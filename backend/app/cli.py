import sys

from app.db.session import SessionLocal
from app.services.user_service import get_or_create_admin


def seed_admin():
    db = SessionLocal()
    try:
        user = get_or_create_admin(db)
        print(f"seed-admin: Created/verified admin user: {user.email} (id={user.id})")
    except Exception as e:
        print(f"seed-admin: ERROR — {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: epibridge <command>")
        print("Commands: seed-admin")
        sys.exit(1)

    command = sys.argv[1]
    if command == "seed-admin":
        seed_admin()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
