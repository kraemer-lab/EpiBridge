#!/usr/bin/env bash
set -euo pipefail

# multipass.sh — Multipass VM helper for EpiBridge
#
# Provides VM lifecycle operations through the same interface as
# orbstack.sh, enabling the platform.sh abstraction layer to manage
# a Multipass-backed execution environment.

MACHINE="epibridge"
CLOUD_INIT="vm/cloud-init.yaml"

case "${1:-help}" in
  create)
    shift
    if multipass info "$MACHINE" >/dev/null 2>&1; then
      echo "VM $MACHINE already exists, skipping creation."
    else
      echo "Launching VM $MACHINE (Ubuntu 24.04, 20GB disk)..."
      multipass launch --disk 20G --cloud-init "$CLOUD_INIT" 24.04 --name "$MACHINE" "$@"
    fi
    echo "Waiting for cloud-init provisioning to complete..."
    echo "  (Installing Docker Engine, configuring firewall, creating directories)"
    multipass exec "$MACHINE" -- cloud-init status --wait || true
    echo "Cloud-init finished."
    echo "VM $MACHINE ready."
    ;;
  mount)
    # Native mount (9p/virtio) provides a live shared filesystem suitable
    # for development. Unlike the default SSHFS mount on macOS, native
    # mounts support full file read/write access.
    # Requires the VM to be stopped, then started after mounting.
    multipass umount "$MACHINE:/opt/epibridge" 2>/dev/null || true
    multipass stop "$MACHINE" 2>/dev/null || true
    multipass mount -t native "$(pwd)" "$MACHINE:/opt/epibridge"
    multipass start "$MACHINE"
    echo "Mounted $(pwd) at /opt/epibridge (native 9p)"
    ;;
  exec)
    shift
    multipass exec "$MACHINE" -- sudo -u epibridge "$@"
    ;;
  shell)
    exec multipass exec "$MACHINE" -- sudo -u epibridge -s
    ;;
  ip)
    multipass info "$MACHINE" --format json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['$MACHINE']['ipv4'][0])"
    ;;
  delete)
    echo "Deleting VM $MACHINE..."
    multipass delete --purge "$MACHINE"
    ;;
  help|*)
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  create           Create the installation VM"
    echo "  delete           Delete the installation VM"
    echo "  mount            Mount repo into /opt/epibridge (native 9p)"
    echo "  exec <cmd>       Run command inside the VM (as epibridge user)"
    echo "  shell            Interactive shell inside the VM (as epibridge user)"
    echo "  ip               Show VM IP address"
    ;;
esac
