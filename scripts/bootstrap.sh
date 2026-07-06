#!/usr/bin/env bash
set -euo pipefail

DEV_MODE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dev) DEV_MODE=true; shift ;;
    *) echo "Usage: $0 [--dev]"; exit 1 ;;
  esac
done

if [ "$DEV_MODE" = true ]; then
  EPIBRIDGE_HOME="${EPIBRIDGE_HOME:-$(pwd)}"
else
  EPIBRIDGE_HOME="${EPIBRIDGE_HOME:-/opt/epibridge}"
fi

REPO_URL="${REPO_URL:-https://github.com/example/epibridge.git}"
BRANCH="${BRANCH:-main}"

echo "=== EpiBridge Bootstrap ==="

# Warn about running as wrong user in dev mode
if [ "$DEV_MODE" = true ]; then
  if ! groups | grep -q docker 2>/dev/null && [ "$(id -u)" != 0 ]; then
    echo "WARNING: not in the docker group. Run as root or the 'epibridge' user."
  fi
  if [ ! -w /var/lib/epibridge/outputs ] 2>/dev/null; then
    echo "WARNING: cannot write to /var/lib/epibridge/outputs. Run as root or the 'epibridge' user."
  fi
fi

# 1. Prerequisites
if [ "$DEV_MODE" = false ]; then
  echo "Checking prerequisites..."
  for cmd in docker git curl; do
    if ! command -v "$cmd" &>/dev/null; then
      echo "ERROR: $cmd is not installed. Run cloud-init first."
      exit 1
    fi
  done

  for dir in /var/lib/epibridge /var/log/epibridge; do
    if [ ! -d "$dir" ]; then
      echo "ERROR: $dir does not exist. Run cloud-init first."
      exit 1
    fi
  done
fi

# 2. Clone repository
if [ "$DEV_MODE" = false ]; then
  if [ -d "$EPIBRIDGE_HOME/.git" ]; then
    echo "Repository already exists at $EPIBRIDGE_HOME"
  else
    echo "Cloning repository..."
    git clone --branch "$BRANCH" "$REPO_URL" "$EPIBRIDGE_HOME"
  fi
fi

cd "$EPIBRIDGE_HOME"

# 3. Run install
if [ "$DEV_MODE" = true ]; then
  ./scripts/install.sh --dev
else
  ./scripts/install.sh
fi

# 4. Verify
echo ""
echo "=== Bootstrap complete ==="
./scripts/healthcheck.sh
