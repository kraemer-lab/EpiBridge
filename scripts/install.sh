#!/usr/bin/env bash
set -euo pipefail

# install.sh — full system installation
#
# Handles environment setup (clone, directory provisioning) then
# delegates all application-level initialisation to bootstrap.sh.

DEV_MODE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dev) DEV_MODE=true; shift ;;
    *) echo "Usage: $0 [--dev]"; exit 1 ;;
  esac
done

EPIBRIDGE_HOME="${EPIBRIDGE_HOME:-/opt/epibridge}"
REPO_URL="${REPO_URL:-https://github.com/example/epibridge.git}"
BRANCH="${BRANCH:-main}"

echo "=== EpiBridge Install ==="

if [ "$DEV_MODE" = true ]; then
  if [ ! -d "$EPIBRIDGE_HOME" ]; then
    echo "ERROR: $EPIBRIDGE_HOME does not exist."
    echo "In --dev mode the source tree must be mounted or symlinked before running install.sh."
    exit 1
  fi
else
  if [ ! -d "$EPIBRIDGE_HOME" ]; then
    echo "Creating $EPIBRIDGE_HOME"
    mkdir -p "$EPIBRIDGE_HOME"
  fi

  # Clone or update repository
  if [ -d "$EPIBRIDGE_HOME/.git" ]; then
    echo "Updating repository..."
    cd "$EPIBRIDGE_HOME"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
  else
    echo "Cloning repository..."
    git clone --branch "$BRANCH" "$REPO_URL" "$EPIBRIDGE_HOME"
  fi
fi

cd "$EPIBRIDGE_HOME"

# Delegate all application-level bootstrapping
./scripts/bootstrap.sh

echo ""
echo "=== EpiBridge installation complete ==="
echo "Frontend: https://$(grep ^DOMAIN "$EPIBRIDGE_HOME/.env" 2>/dev/null || echo "localhost")/"
