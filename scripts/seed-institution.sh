#!/usr/bin/env bash
set -euo pipefail

# seed-institution.sh — seed administrator account, platform terms, and dataset terms
#
# Prerequisite: the platform must be running (bootstrap.sh has completed).
# Idempotent: safe to run multiple times.

echo "Seeding administrator account..."
docker compose exec -T backend python -m app.cli seed-admin

echo "Seeding platform terms..."
docker compose exec -T backend python -m app.cli seed-terms
