#!/usr/bin/env bash
set -euo pipefail

DEV_MODE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dev) DEV_MODE=true; shift ;;
    *) echo "Usage: $0 [--dev]"; exit 1 ;;
  esac
done

EPIBRIDGE_HOME="${EPIBRIDGE_HOME:-/opt/epibridge}"
REPO_URL="${REPO_URL:-https://github.com/example/epibridge.git}"
BRANCH="${BRANCH:-main}"
ENV_FILE="${EPIBRIDGE_HOME}/.env"
COMPOSE_FILE="${EPIBRIDGE_HOME}/docker-compose.yml"

echo "=== EpiBridge Install ==="

if [ "$DEV_MODE" = true ]; then
  if [ ! -d "$EPIBRIDGE_HOME" ]; then
    echo "ERROR: $EPIBRIDGE_HOME does not exist."
    echo "In --dev mode the source tree must be mounted or symlinked before running install.sh."
    exit 1
  fi
else
  if [ ! -d "$EPIBRIDGE_HOME" ]; then
    echo "Creating $EPIBRIDGE_HOME"
    mkdir -p "$EPIBRIDGE_HOME"
  fi

  # Clone or update repository
  if [ -d "$EPIBRIDGE_HOME/.git" ]; then
    echo "Updating repository..."
    cd "$EPIBRIDGE_HOME"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
  else
    echo "Cloning repository..."
    git clone --branch "$BRANCH" "$REPO_URL" "$EPIBRIDGE_HOME"
  fi
fi

cd "$EPIBRIDGE_HOME"

# Generate .env if not present
if [ ! -f "$ENV_FILE" ]; then
  echo "Generating .env..."
  cp "${EPIBRIDGE_HOME}/.env.example" "$ENV_FILE"

  export POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
  export REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
  export SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')

  python3 -c "
import os
path = '$ENV_FILE'
with open(path) as f:
    c = f.read()
c = c.replace('POSTGRES_PASSWORD=__GENERATED__', f'POSTGRES_PASSWORD={os.environ[\"POSTGRES_PASSWORD\"]}')
c = c.replace('REDIS_PASSWORD=__GENERATED__', f'REDIS_PASSWORD={os.environ[\"REDIS_PASSWORD\"]}')
c = c.replace('SECRET_KEY=__GENERATED__', f'SECRET_KEY={os.environ[\"SECRET_KEY\"]}')
with open(path, 'w') as f:
    f.write(c)
"

  chmod 600 "$ENV_FILE"
  echo ".env created at $ENV_FILE"
  if [ "$DEV_MODE" = true ]; then
    echo "Using generated defaults for development."
  else
    echo "Edit $ENV_FILE to configure Firebase and domain before continuing."
    echo "Then re-run install.sh to proceed."
    exit 0
  fi
fi

# Build and start services
echo "Building and starting Docker services..."
docker compose -f "$COMPOSE_FILE" build
docker compose -f "$COMPOSE_FILE" up -d

# Wait for database
echo "Waiting for PostgreSQL..."
until docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U epibridge 2>/dev/null; do
  sleep 2
done
echo "PostgreSQL is ready."

# Seed admin account
echo "Seeding administrator account..."
docker compose -f "$COMPOSE_FILE" exec -T backend python -m app.cli seed-admin

# Health check
echo "Running health checks..."
./scripts/healthcheck.sh

echo ""
echo "=== EpiBridge installation complete ==="
echo "Frontend: https://$(grep ^DOMAIN "$ENV_FILE" | cut -d= -f2)/"
echo "API:      https://$(grep ^DOMAIN "$ENV_FILE" | cut -d= -f2)/api/health"
