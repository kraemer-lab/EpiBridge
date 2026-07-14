#!/usr/bin/env bash
set -euo pipefail

# seed-personas.sh — seed institutional persona accounts
#
# Prerequisite: seed-institution.sh must have completed (admin must exist).
# Idempotent: safe to run multiple times.

echo "Seeding maintainer account..."
docker compose exec -T backend python -m app.cli seed-maintainer

echo "Seeding researcher account..."
docker compose exec -T backend python -m app.cli seed-researcher

echo "Seeding moderator account..."
docker compose exec -T backend python -m app.cli seed-moderator
