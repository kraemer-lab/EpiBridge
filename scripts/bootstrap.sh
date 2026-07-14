#!/usr/bin/env bash
set -euo pipefail

# bootstrap.sh — platform boot only
#
# bootstrap.sh brings the platform into an operational state.
# It does NOT seed users, terms, or any other application state.
#
# Idempotent platform initialisation. Safe to run multiple times.
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

  sed -i.bak "s|POSTGRES_PASSWORD=__GENERATED__|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" .env && rm -f .env.bak
  sed -i.bak "s|REDIS_PASSWORD=__GENERATED__|REDIS_PASSWORD=$REDIS_PASSWORD|" .env && rm -f .env.bak
  sed -i.bak "s|SECRET_KEY=__GENERATED__|SECRET_KEY=$SECRET_KEY|" .env && rm -f .env.bak
  sed -i.bak "s|ADMIN_PASSWORD=__GENERATED__|ADMIN_PASSWORD=$ADMIN_PASSWORD|" .env && rm -f .env.bak

  chmod 600 .env
  echo ".env created"
fi

###############################################################################
# 2. Discover deployment environment
###############################################################################
if command -v getent &>/dev/null; then
  DOCKER_GID="$(getent group docker | cut -d: -f3)"
  if [ -z "$DOCKER_GID" ]; then
    echo "ERROR: Docker group not found. Is Docker installed?"
    exit 1
  fi
elif [[ "$(uname)" == "Darwin" ]]; then
  # Docker Desktop on macOS: socket permissions vary; use the socket's group.
  DOCKER_GID=$(stat -f '%g' /var/run/docker.sock 2>/dev/null || echo "0")
else
  echo "ERROR: Cannot determine Docker group ID."
  exit 1
fi
export DOCKER_GID
echo "Docker group GID: $DOCKER_GID"

# Persist DOCKER_GID to .env so that all subsequent docker compose
# invocations (clean-db, CI, etc.) automatically consume it.
if grep -q "^DOCKER_GID=" .env 2>/dev/null; then
  sed -i.bak "s|^DOCKER_GID=.*|DOCKER_GID=$DOCKER_GID|" .env && rm -f .env.bak
else
  echo "DOCKER_GID=$DOCKER_GID" >> .env
fi

###############################################################################
# 3. Set HOST_DATA_ROOT for Docker-outside-of-Docker bind mounts
###############################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export HOST_DATA_ROOT="${HOST_DATA_ROOT:-${REPO_ROOT}/examples/resources}"
export HOST_RESOURCE_MANIFEST_DIR="${HOST_RESOURCE_MANIFEST_DIR:-${REPO_ROOT}/resources}"

###############################################################################
# 4. Derive PUBLIC_URL_HOST from PUBLIC_URL for Caddy
#     PUBLIC_URL_HOST is exported as a runtime environment variable only —
#     never stored in .env. The direction of dependency is:
#       PUBLIC_URL (config) → PUBLIC_URL_HOST (derived) → Caddy
###############################################################################
PUBLIC_URL="$(sed -n 's/^PUBLIC_URL=//p' .env 2>/dev/null || true)"
PUBLIC_URL="${PUBLIC_URL:-https://localhost}"
# Strip scheme and port to extract bare hostname
PUBLIC_URL_HOST="${PUBLIC_URL#https://}"
PUBLIC_URL_HOST="${PUBLIC_URL_HOST#http://}"
PUBLIC_URL_HOST="${PUBLIC_URL_HOST%%:*}"
export PUBLIC_URL_HOST
echo "Public URL: $PUBLIC_URL (hostname: $PUBLIC_URL_HOST)"

###############################################################################
# 5. Build Docker images
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
# 6. Provision application storage
###############################################################################
mkdir -p /var/lib/epibridge/bundles /var/lib/epibridge/outputs /var/lib/epibridge/releases

###############################################################################
# 7. Generate TLS certificates if not present
#     If mkcert has already generated trusted certificates (via make certs or
#     setup-certs.sh), they are reused.  Otherwise, self-signed certificates
#     are generated for CI and environments without mkcert.
###############################################################################
if [ ! -f "certs/${PUBLIC_URL_HOST}.pem" ]; then
  echo "Generating self-signed certificate for: $PUBLIC_URL_HOST"
  mkdir -p certs
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "certs/${PUBLIC_URL_HOST}-key.pem" \
    -out "certs/${PUBLIC_URL_HOST}.pem" \
    -subj "/CN=${PUBLIC_URL_HOST}" 2>/dev/null
  echo "Certificate generated: certs/${PUBLIC_URL_HOST}.pem"
fi

###############################################################################
# 8. Start services
###############################################################################
echo "Starting services..."
docker compose up -d

###############################################################################
# 9. Wait for PostgreSQL
###############################################################################
echo "Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U epibridge 2>/dev/null; do
  sleep 2
done
echo "PostgreSQL is ready."

###############################################################################
# 10. Wait for backend API to be ready
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
# 11. Health check
###############################################################################
echo "Running health checks..."
./scripts/healthcheck.sh

echo ""
echo "=== EpiBridge platform boot complete ==="
