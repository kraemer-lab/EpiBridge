import sys

from app.db.session import SessionLocal
from app.services.demo_seeder import seed_demo_workspace
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


def seed_demo():
    db = SessionLocal()
    try:
        result = seed_demo_workspace(db)
        status = result["status"]
        if status == "skipped":
            print(f"seed-demo: {result['message']}")
        elif status == "error":
            print(f"seed-demo: ERROR — {result['message']}")
            sys.exit(1)
        else:
            print(
                f"seed-demo: Created demo workspace "
                f"(project_id={result['project_id']}, bundle_id={result['bundle_id']})"
            )
    except Exception as e:
        print(f"seed-demo: ERROR — {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: epibridge <command>")
        print("Commands: seed-admin, seed-demo")
        sys.exit(1)

    command = sys.argv[1]
    if command == "seed-admin":
        seed_admin()
    elif command == "seed-demo":
        seed_demo()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
