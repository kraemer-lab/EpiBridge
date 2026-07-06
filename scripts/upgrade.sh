#!/usr/bin/env bash
set -euo pipefail

EPIBRIDGE_HOME="${EPIBRIDGE_HOME:-/opt/epibridge}"
COMPOSE_FILE="${EPIBRIDGE_HOME}/docker-compose.yml"

echo "=== EpiBridge Upgrade ==="

if [ ! -d "$EPIBRIDGE_HOME/.git" ]; then
  echo "Error: $EPIBRIDGE_HOME is not a git repository."
  echo "Run install.sh first."
  exit 1
fi

# Pull latest code
cd "$EPIBRIDGE_HOME"
echo "Pulling latest code..."
git fetch origin
git checkout main
git pull origin main

# Rebuild images
echo "Rebuilding Docker images..."
docker compose -f "$COMPOSE_FILE" build

# Restart services
echo "Restarting services..."
docker compose -f "$COMPOSE_FILE" up -d

# Wait for database
echo "Waiting for PostgreSQL..."
until docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U epibridge 2>/dev/null; do
  sleep 2
done

# Run migrations
echo "Running database migrations..."
docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head

# Health check
echo "Running health checks..."
./scripts/healthcheck.sh

echo ""
echo "=== EpiBridge upgrade complete ==="
