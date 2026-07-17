"""Worker health check.

Verifies the worker's critical dependencies are functional:
- Database connectivity
- Docker daemon accessibility

Returns exit code 0 if healthy, 1 otherwise.

This module is the stable health check interface for Docker Compose.
The implementation can evolve (e.g. heartbeat freshness, progress
indicators) without changes to the Compose configuration.
"""


def _check_database() -> bool:
    try:
        from sqlalchemy import text
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return True
        finally:
            db.close()
    except Exception:
        return False


def _check_docker() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


def main() -> int:
    ok = all((_check_database(), _check_docker()))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
