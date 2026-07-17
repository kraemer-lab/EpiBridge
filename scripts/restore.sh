#!/usr/bin/env bash
set -euo pipefail

EPIBRIDGE_HOME="${EPIBRIDGE_HOME:-/opt/epibridge}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/epibridge}"
COMPOSE_FILE="${EPIBRIDGE_HOME}/docker-compose.yml"

# Parse --yes / -y flag
CONFIRMED=false
while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y)
      CONFIRMED=true
      shift
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Usage: $0 [--yes|-y] <backup-file>"
      echo "Example: $0 /var/backups/epibridge/epibridge_20250101_120000.tar.gz"
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [ $# -ne 1 ]; then
  echo "Usage: $0 [--yes|-y] <backup-file>"
  echo "Example: $0 /var/backups/epibridge/epibridge_20250101_120000.tar.gz"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "=== EpiBridge Restore ==="
echo "Backup: $BACKUP_FILE"

# Require explicit confirmation before destructive operations
if [ "$CONFIRMED" = false ]; then
  echo ""
  echo "WARNING: This will DESTROY all current data and replace it"
  echo "with the state from the backup archive."
  echo ""
  echo "  - All services will be stopped"
  echo "  - The database will be overwritten"
  echo "  - All current platform state will be lost"
  echo ""
  read -p "Continue? [y/N] " confirm
  if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Restore cancelled."
    exit 1
  fi
fi

# Extract backup
RESTORE_DIR="/tmp/epibridge_restore_$(date +%s)"
mkdir -p "$RESTORE_DIR"
tar xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

# Find the extracted directory
EXTRACTED_DIR=$(find "$RESTORE_DIR" -maxdepth 1 -type d | tail -1)

if [ ! -f "${EXTRACTED_DIR}/postgres.sql" ]; then
  echo "Error: no postgres.sql found in backup"
  rm -rf "$RESTORE_DIR"
  exit 1
fi

# Stop services
echo "Stopping services..."
docker compose -f "$COMPOSE_FILE" down

# Restore environment config
if [ -f "${EXTRACTED_DIR}/.env" ]; then
  echo "Restoring .env..."
  cp "${EXTRACTED_DIR}/.env" "${EPIBRIDGE_HOME}/.env"
fi

# Start database only for restore
echo "Starting database..."
docker compose -f "$COMPOSE_FILE" up -d postgres

# Wait for database
echo "Waiting for PostgreSQL..."
until docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U epibridge 2>/dev/null; do
  sleep 2
done

# Restore database
echo "Restoring PostgreSQL..."
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U epibridge < "${EXTRACTED_DIR}/postgres.sql"

# Restore data volumes
if [ -f "${EXTRACTED_DIR}/data.tar.gz" ]; then
  echo "Restoring data volumes..."
  sudo tar xzf "${EXTRACTED_DIR}/data.tar.gz" -C /var/lib/epibridge
fi

# Start all services
echo "Starting all services..."
docker compose -f "$COMPOSE_FILE" up -d

# Run migrations
echo "Running database migrations..."
docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head

# Cleanup
rm -rf "$RESTORE_DIR"

# Health check
echo "Running health checks..."
./scripts/healthcheck.sh

echo ""
echo "=== Restore complete ==="
