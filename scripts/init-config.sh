#!/usr/bin/env bash
set -euo pipefail

# init-config.sh — initialise application configuration
#
# Creates .env from .env.example with generated secrets.
# Accepts initial configuration values through environment variables.
# Overrides are applied only when creating a fresh .env.
# Idempotent: safe to run repeatedly.
#
# Usage: PUBLIC_URL=https://example.com ./scripts/init-config.sh

_apply_override() {
    local key="$1"
    if [ -n "${!key:-}" ]; then
        sed -i.bak "s|^${key}=.*|${key}=${!key}|" .env && rm -f .env.bak
        echo "  ${key}=${!key}"
    fi
}

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

    _apply_override PUBLIC_URL

    chmod 600 .env
    echo ".env created"
fi
