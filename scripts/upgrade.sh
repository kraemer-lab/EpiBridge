#!/usr/bin/env bash
set -euo pipefail

EPIBRIDGE_HOME="${EPIBRIDGE_HOME:-/opt/epibridge}"
COMPOSE_FILE="${EPIBRIDGE_HOME}/docker-compose.yml"

# Parse --no-backup flag
SKIP_BACKUP=false
while [ $# -gt 0 ]; do
  case "$1" in
    --no-backup)
      SKIP_BACKUP=true
      shift
      ;;
    -*)
      echo "Usage: $0 [--no-backup]"
      echo ""
      echo "  --no-backup    Skip pre-upgrade backup (not recommended)"
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

echo "=== EpiBridge Upgrade ==="

if [ ! -d "$EPIBRIDGE_HOME/.git" ]; then
  echo "Error: $EPIBRIDGE_HOME is not a git repository."
  echo "Run install.sh first."
  exit 1
fi

cd "$EPIBRIDGE_HOME"

# Create a pre-upgrade backup unless explicitly skipped
if [ "$SKIP_BACKUP" = false ]; then
  echo "Creating pre-upgrade backup..."
  if ./scripts/backup.sh; then
    echo "Pre-upgrade backup completed."
  else
    echo ""
    echo "ERROR: Pre-upgrade backup failed."
    echo ""
    echo "The upgrade cannot proceed without a recent backup."
    echo "If the database migration fails, there will be no recovery path."
    echo ""
    echo "To create a backup manually and retry:"
    echo "  make backup && make upgrade"
    echo ""
    echo "To bypass this check (not recommended):"
    echo "  make upgrade ARGS=--no-backup"
    exit 1
  fi
else
  echo "Skipping pre-upgrade backup (--no-backup specified)."
fi

# Pull latest code
echo "Pulling latest code..."
git fetch origin
git checkout main
git pull origin main

# Rebuild application images
echo "Rebuilding application images..."
docker compose -f "$COMPOSE_FILE" build

# Rebuild analysis container images
echo "Rebuilding analysis container images..."
for dir in execution-environments/*/; do
    tag="epibridge/$(basename "$dir"):latest"
    echo "  Building $tag..."
    docker build -t "$tag" "$dir"
done

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
