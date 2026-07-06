#!/usr/bin/env bash
set -euo pipefail

# bootstrap.sh — shared EpiBridge bootstrap
#
# Idempotent application initialisation. Safe to run multiple times.
#
# Environment contract:
#   - Current directory is the repository root.
#   - Docker and Docker Compose are available.
#   - Any required environment variables are already configured
#     (otherwise .env will be generated from .env.example).
#
# Assumes nothing about: OrbStack, GitHub Actions, SSH, VM paths,
# or local machine layout.

###############################################################################
# 1. Generate .env if not present
###############################################################################
if [ ! -f .env ]; then
  echo "Generating .env from .env.example..."
  cp .env.example .env

  POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
  REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
  SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')

  python3 -c "
import os
path = '.env'
with open(path) as f:
    c = f.read()
c = c.replace('POSTGRES_PASSWORD=__GENERATED__', 'POSTGRES_PASSWORD=$POSTGRES_PASSWORD')
c = c.replace('REDIS_PASSWORD=__GENERATED__', 'REDIS_PASSWORD=$REDIS_PASSWORD')
c = c.replace('SECRET_KEY=__GENERATED__', 'SECRET_KEY=$SECRET_KEY')
with open(path, 'w') as f:
    f.write(c)
"
  chmod 600 .env
  echo ".env created"
fi

###############################################################################
# 2. Set HOST_DATA_ROOT for Docker-outside-of-Docker bind mounts
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
# 3. Build Docker images
###############################################################################
echo "Building application images..."
docker compose build

echo "Building analysis container image..."
docker build -t epibridge/python-3.13-scientific:latest containers/python-3.13-scientific/

###############################################################################
# 4. Start services
###############################################################################
echo "Starting services..."
docker compose up -d

###############################################################################
# 5. Wait for PostgreSQL
###############################################################################
echo "Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U epibridge 2>/dev/null; do
  sleep 2
done
echo "PostgreSQL is ready."

###############################################################################
# 6. Seed admin account
###############################################################################
echo "Seeding administrator account..."
docker compose exec -T backend python -m app.cli seed-admin

###############################################################################
# 7. Seed demo workspace
###############################################################################
echo "Seeding demo workspace..."
docker compose exec -T backend python -m app.cli seed-demo

###############################################################################
# 8. Health check
###############################################################################
echo "Running health checks..."
./scripts/healthcheck.sh

echo "=== EpiBridge bootstrap complete ==="
