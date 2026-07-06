#!/usr/bin/env bash
set -euo pipefail

EPIBRIDGE_HOME="${EPIBRIDGE_HOME:-/opt/epibridge}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/epibridge}"
COMPOSE_FILE="${EPIBRIDGE_HOME}/docker-compose.yml"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/epibridge_${TIMESTAMP}"

echo "=== EpiBridge Backup ==="

mkdir -p "$BACKUP_PATH"

# Dump PostgreSQL database
echo "Backing up PostgreSQL..."
docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dumpall -U epibridge > "${BACKUP_PATH}/postgres.sql"

# Backup environment config
echo "Backing up configuration..."
if [ -f "${EPIBRIDGE_HOME}/.env" ]; then
  cp "${EPIBRIDGE_HOME}/.env" "${BACKUP_PATH}/.env"
fi

# Backup persistent volumes (outputs, datasets)
echo "Backing up data volumes..."
if [ -d "/var/lib/epibridge" ]; then
  tar czf "${BACKUP_PATH}/data.tar.gz" -C /var/lib/epibridge .
fi

# Compress backup
echo "Compressing backup..."
tar czf "${BACKUP_DIR}/epibridge_${TIMESTAMP}.tar.gz" -C "$BACKUP_DIR" "epibridge_${TIMESTAMP}"
rm -rf "$BACKUP_PATH"

# Keep only last 30 backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "epibridge_*.tar.gz" -mtime +30 -delete

echo ""
echo "=== Backup complete: ${BACKUP_DIR}/epibridge_${TIMESTAMP}.tar.gz ==="
