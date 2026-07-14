#!/usr/bin/env bash
set -euo pipefail

# setup-ai.sh — Enable AI deployment configuration in .env
#
# This script ensures OLLAMA_BASE_URL and OLLAMA_MODEL are present
# and uncommented in .env. It does not affect the institutional
# AI_REVIEW_ENABLED setting — that is managed through the admin UI.
#
# Idempotent: safe to run at any time.

if [ ! -f .env ]; then
  echo "Error: .env not found. Run make install first."
  exit 1
fi

_changed=false

_set_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env 2>/dev/null; then
    return
  fi
  if grep -q "^# ${key}=" .env 2>/dev/null; then
    sed -i.bak "s/^# ${key}=.*/${key}=${value}/" .env
  else
    echo "${key}=${value}" >> .env
  fi
  _changed=true
}

_set_env "OLLAMA_BASE_URL" "http://ollama:11434"
_set_env "OLLAMA_MODEL" "llama3.2"
_set_env "OLLAMA_TIMEOUT_SECONDS" "120"

rm -f .env.bak

if [ "$_changed" = true ]; then
  echo "AI deployment configuration enabled in .env"
else
  echo "AI deployment configuration already present in .env"
fi
