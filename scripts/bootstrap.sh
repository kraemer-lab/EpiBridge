#!/usr/bin/env bash
set -euo pipefail

# bootstrap.sh — shared EpiBridge bootstrap
#
# bootstrap.sh initialises the application.
# It is NOT an infrastructure provisioning script.
#
# Idempotent application initialisation. Safe to run multiple times.
#
# Environment contract:
#   - Current directory is the repository root.
#   - Docker and Docker Compose are available.
#   - Infrastructure provisioning has completed — storage directories
#     (/var/lib/epibridge/...) exist with correct ownership.
#   - Any required environment variables are already configured
#     (otherwise .env will be generated from .env.example).

###############################################################################
# 1. Generate .env if not present
###############################################################################
if [ ! -f .env ]; then
  echo "Generating .env from .env.example..."
  cp .env.example .env

  POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
  REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
  SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')
  ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')

  python3 -c "
import os
path = '.env'
with open(path) as f:
    c = f.read()
c = c.replace('POSTGRES_PASSWORD=__GENERATED__', 'POSTGRES_PASSWORD=$POSTGRES_PASSWORD')
c = c.replace('REDIS_PASSWORD=__GENERATED__', 'REDIS_PASSWORD=$REDIS_PASSWORD')
c = c.replace('SECRET_KEY=__GENERATED__', 'SECRET_KEY=$SECRET_KEY')
c = c.replace('ADMIN_PASSWORD=__GENERATED__', 'ADMIN_PASSWORD=$ADMIN_PASSWORD')
with open(path, 'w') as f:
    f.write(c)
"
  chmod 600 .env
  echo ".env created"
fi

###############################################################################
# 2. Discover deployment environment
###############################################################################
DOCKER_GID="$(getent group docker | cut -d: -f3)"
if [ -z "$DOCKER_GID" ]; then
  echo "ERROR: Docker group not found. Is Docker installed?"
  exit 1
fi
export DOCKER_GID
echo "Docker group GID: $DOCKER_GID"

# Persist DOCKER_GID to .env so that all subsequent docker compose
# invocations (make clean-db, make reset, CI, etc.) automatically
# consume it without shell exports or hardcoded fallbacks.
#
# DOCKER_GID is deployment metadata discovered from the local
# environment.  It is generated automatically by bootstrap.sh and
# is not intended to be manually edited.
if grep -q "^DOCKER_GID=" .env 2>/dev/null; then
  sed -i.bak "s/^DOCKER_GID=.*/DOCKER_GID=$DOCKER_GID/" .env && rm -f .env.bak
else
  echo "DOCKER_GID=$DOCKER_GID" >> .env
fi

###############################################################################
# 3. Set HOST_DATA_ROOT for Docker-outside-of-Docker bind mounts
#
# The worker runs in a container, so provider mount sources like
# /read-only-data/* are not visible to Docker Engine on the host.
# This variable remaps them to the host-visible path.
#
# Derive from the bootstrap script location so it works in development
# (OrbStack VM at /opt/epibridge), CI (GitHub workspace), and any
# future deployment context. Can be overridden via environment.
###############################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export HOST_DATA_ROOT="${HOST_DATA_ROOT:-${REPO_ROOT}/examples/resources}"

###############################################################################
# 4. Build Docker images
###############################################################################
echo "Building application images..."
docker compose build

echo "Building analysis container images..."
for dir in execution-environments/*/; do
    tag="epibridge/$(basename "$dir"):latest"
    echo "  Building $tag..."
    docker build -t "$tag" "$dir"
done

###############################################################################
# 4. Provision application storage
#
# The mkdir below is a defensive measure — it ensures the directories
# exist even if infrastructure provisioning (cloud-init.yaml or CI)
# hasn't run yet.  Ownership is an infrastructure responsibility and
# is never modified here.  If the application user cannot write to
# these directories, the containers will fail with a clear permission
# error, correctly directing the operator to check provisioning.
###############################################################################
echo "Provisioning storage directories..."
mkdir -p /var/lib/epibridge/bundles /var/lib/epibridge/outputs /var/lib/epibridge/releases

###############################################################################
# 5. Start services
###############################################################################
echo "Starting services..."
docker compose up -d

###############################################################################
# 6. Wait for PostgreSQL
###############################################################################
echo "Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U epibridge 2>/dev/null; do
  sleep 2
done
echo "PostgreSQL is ready."

###############################################################################
# 7. Wait for backend API to be ready
###############################################################################
echo "Waiting for backend API..."
until docker compose exec -T backend python3 -c "
import http.client, json
c = http.client.HTTPConnection('localhost', 8000, timeout=5)
c.request('GET', '/api/health')
r = c.getresponse()
assert r.status == 200
assert json.loads(r.read())['status'] == 'ok'
" 2>/dev/null; do
  sleep 2
done
echo "Backend API is ready."

###############################################################################
# 8. Create test database
###############################################################################
echo "Creating test database..."
docker compose exec -T postgres psql -U epibridge -c "CREATE DATABASE epibridge_test;" 2>/dev/null || true

###############################################################################
# 9. Seed admin account
###############################################################################
echo "Seeding administrator account..."
docker compose exec -T backend python -m app.cli seed-admin

###############################################################################
# 10. Seed maintainer account
###############################################################################
echo "Seeding maintainer account..."
docker compose exec -T backend python -m app.cli seed-maintainer

###############################################################################
# 11. Health check
###############################################################################
echo "Running health checks..."
./scripts/healthcheck.sh

echo "=== EpiBridge bootstrap complete ==="
