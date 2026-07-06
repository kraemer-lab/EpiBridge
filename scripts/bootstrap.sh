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
# 2. Build Docker images
###############################################################################
echo "Building application images..."
docker compose build

echo "Building analysis container image..."
docker build -t epibridge/python-3.13-scientific:latest containers/python-3.13-scientific/

###############################################################################
# 3. Start services
###############################################################################
echo "Starting services..."
docker compose up -d

###############################################################################
# 4. Wait for PostgreSQL
###############################################################################
echo "Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U epibridge 2>/dev/null; do
  sleep 2
done
echo "PostgreSQL is ready."

###############################################################################
# 5. Seed admin account
###############################################################################
echo "Seeding administrator account..."
docker compose exec -T backend python -m app.cli seed-admin

###############################################################################
# 6. Seed demo workspace
###############################################################################
echo "Seeding demo workspace..."
docker compose exec -T backend python -m app.cli seed-demo

###############################################################################
# 7. Health check
###############################################################################
echo "Running health checks..."
./scripts/healthcheck.sh

echo "=== EpiBridge bootstrap complete ==="
