#!/usr/bin/env bash
set -euo pipefail

# platform.sh — execution-environment abstraction for EpiBridge
#
# Reads .epibridge-context to determine the execution target, then
# dispatches platform operations to the appropriate backend.
#
# Usage: ./scripts/platform.sh <command> [args...]
#
# Commands:
#   compose <args>    Run docker compose on the platform host
#   exec <svc> <cmd>  Run a command in a container (non-TTY)
#   logs [args]       Tail compose logs
#   shell             Interactive session on the platform host
#   restart <svc>     Restart a compose service
#   run <script>      Execute a script from the repo on the platform host
#   cp <src> <dst>    Copy files to/from the platform host

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load execution context.  An explicit EPIBRIDGE_TARGET environment
# variable takes precedence — this supports make uninstall TARGET=...
# when the execution context is missing or stale.
if [ -z "${EPIBRIDGE_TARGET:-}" ] && [ -f "$REPO_ROOT/.epibridge-context" ]; then
    . "$REPO_ROOT/.epibridge-context"
fi
EPIBRIDGE_TARGET="${EPIBRIDGE_TARGET:-native}"

# — helpers -----------------------------------------------------------------------

_q() {
    printf '%q ' "$@"
}

# _run <shell-command-string>
#   Execute an arbitrary shell command on the platform host.
_run() {
    case "$EPIBRIDGE_TARGET" in
        native)
            cd "$REPO_ROOT" && eval "$*"
            ;;
        orbstack)
            VM_DIR="${EPIBRIDGE_VM_DIR:-/opt/epibridge}"
            ssh -q root@epibridge@orb "cd $VM_DIR && $*"
            ;;
        multipass)
            VM_DIR="${EPIBRIDGE_VM_DIR:-/opt/epibridge}"
            EPIBRIDGE_VM="${EPIBRIDGE_VM:-epibridge}"
            multipass exec "$EPIBRIDGE_VM" -- sudo -u epibridge bash -c "cd $VM_DIR && $*"
            ;;
        remote)
            local host="${EPIBRIDGE_HOST:?EPIBRIDGE_HOST not set}"
            local user="${EPIBRIDGE_USER:-epibridge}"
            local dir="${EPIBRIDGE_DIR:-/opt/epibridge}"
            ssh -q "$user@$host" "cd $dir && $*"
            ;;
        *)
            echo "Unknown EPIBRIDGE_TARGET: $EPIBRIDGE_TARGET" >&2
            exit 1
            ;;
    esac
}

# _compose <args...>
#   Run docker compose on the platform host.
#   Materialises the runtime environment from execution context
#   before every invocation so that variables like PUBLIC_URL_HOST
#   are available regardless of how services were started.
_compose() {
    "$SCRIPT_DIR/prepare-env.sh" 2>/dev/null || true
    _run "docker compose --env-file ./.env --env-file ./.epibridge-compose.env $(_q "$@")"
}

# — subcommands -------------------------------------------------------------------

case "${1:-help}" in
    compose)
        shift
        _compose "$@"
        ;;

    start)
        case "$EPIBRIDGE_TARGET" in
            native|remote)
                echo "No VM to start for $EPIBRIDGE_TARGET target."
                ;;
            orbstack)
                "$SCRIPT_DIR/orbstack.sh" start
                ;;
            multipass)
                "$SCRIPT_DIR/multipass.sh" start
                ;;
            *)
                echo "Don't know how to start $EPIBRIDGE_TARGET environment." >&2
                exit 1
                ;;
        esac
        ;;

    exec)
        shift
        _compose exec -T "$@"
        ;;

    logs)
        shift
        _compose logs "$@"
        ;;

    shell)
        case "$EPIBRIDGE_TARGET" in
            native)
                echo "Already on the platform host." >&2
                exec "${SHELL:-/bin/sh}"
                ;;
            orbstack)
                exec ssh -q root@epibridge@orb
                ;;
            multipass)
                EPIBRIDGE_VM="${EPIBRIDGE_VM:-epibridge}"
                exec multipass exec "$EPIBRIDGE_VM" -- sudo -u epibridge -s
                ;;
            remote)
                local host="${EPIBRIDGE_HOST:?EPIBRIDGE_HOST not set}"
                local user="${EPIBRIDGE_USER:-epibridge}"
                exec ssh -q "$user@$host"
                ;;
        esac
        ;;

    destroy)
        case "$EPIBRIDGE_TARGET" in
            native|remote)
                echo "No environment teardown required for $EPIBRIDGE_TARGET target."
                ;;
            orbstack)
                echo "Deleting OrbStack VM (epibridge)..."
                "$SCRIPT_DIR/orbstack.sh" delete
                ;;
            multipass)
                echo "Deleting Multipass VM (epibridge)..."
                "$SCRIPT_DIR/multipass.sh" delete
                ;;
            *)
                echo "Don't know how to destroy $(EPIBRIDGE_TARGET) environment." >&2
                exit 1
                ;;
        esac
        ;;

    restart)
        shift
        _compose restart "$@"
        ;;

    run)
        shift
        _run "bash $*"
        ;;

    cp)
        shift
        case "$EPIBRIDGE_TARGET" in
            native)
                cp "$@"
                ;;
            orbstack)
                # The repo is symlinked at /opt/epibridge inside the VM,
                # so files are already shared. This subcommand is a no-op
                # for OrbStack; use scp if cross-VM copies are needed.
                echo "Files are shared via the mounted repo. Use scp for explicit copies." >&2
                ;;
            multipass)
                # The repo is mounted at /opt/epibridge inside the VM,
                # so files are already shared. This subcommand is a no-op
                # for Multipass; use multipass transfer for explicit copies.
                echo "Files are shared via the mounted repo. Use multipass transfer for explicit copies." >&2
                ;;
            remote)
                local host="${EPIBRIDGE_HOST:?EPIBRIDGE_HOST not set}"
                local user="${EPIBRIDGE_USER:-epibridge}"
                scp "$user@$host:$1" "${2:-.}" 2>/dev/null || \
                scp "$1" "$user@$host:${2:-.}"
                ;;
        esac
        ;;

    help|*)
        echo "Usage: $0 <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  compose <args>    Run docker compose on the platform host"
        echo "  destroy           Teardown the execution environment (VM, etc.)"
        echo "  start             Start the execution environment (VM, etc.)"
        echo "  exec <svc> <cmd>  Run a command in a container (non-TTY)"
        echo "  logs [args]       Tail container logs"
        echo "  shell             Interactive session on the platform host"
        echo "  restart <svc>     Restart a compose service"
        echo "  run <script>      Execute a script on the platform host"
        echo "  cp <src> <dst>    Copy files to/from the platform host"
        ;;
esac
