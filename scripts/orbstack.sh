#!/usr/bin/env bash
set -euo pipefail

MACHINE="epibridge"
CLOUD_INIT="vm/cloud-init.yaml"

case "${1:-help}" in
  create)
    shift
    orbctl create --user-data "$CLOUD_INIT" ubuntu:24.04 "$MACHINE" "$@"
    ;;
  mount)
    # OrbStack auto-shares the host filesystem.
    # Replace /opt/epibridge (empty dir from cloud-init) with a symlink to the repo.
    ssh root@"$MACHINE"@orb "rm -rf /opt/epibridge && ln -sfn $(pwd) /opt/epibridge"
    echo "Mounted $(pwd) at /opt/epibridge"
    ;;
  ssh)
    shift
    ssh root@"$MACHINE"@orb "$@"
    ;;
  ip)
    orbctl info "$MACHINE" | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' | head -1
    ;;
  delete)
    echo "Deleting VM $MACHINE..."
    orbctl delete --force "$MACHINE"
    ;;
  help|*)
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  create           Create the installation VM"
    echo "  delete           Delete the installation VM"
    echo "  mount            Symlink repo into /opt/epibridge"
    echo "  ssh [cmd]        Run command in the VM (or start a shell)"
    echo "  ip               Show VM IP address"
    ;;
esac
