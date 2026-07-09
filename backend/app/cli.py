import sys

from app.db.session import SessionLocal
from app.models.user import UserRole
from app.services.demo_seeder import seed_demo_workspace
from app.services.user_service import (
    create_user,
    get_or_create_admin,
    get_or_create_user,
)


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


def create_researcher():
    if len(sys.argv) < 4:
        print(
            "Usage: epibridge create-user <email> <name> "
            "[--password PASSWORD] [--role researcher|admin]"
        )
        sys.exit(1)

    email = sys.argv[2]
    name = sys.argv[3]
    password = "password"
    role = UserRole.RESEARCHER

    i = 4
    while i < len(sys.argv):
        if sys.argv[i] == "--password" and i + 1 < len(sys.argv):
            password = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--role" and i + 1 < len(sys.argv):
            role_str = sys.argv[i + 1]
            if role_str == "admin":
                role = UserRole.ADMIN
            elif role_str == "researcher":
                role = UserRole.RESEARCHER
            else:
                print(f"Unknown role: {role_str}")
                sys.exit(1)
            i += 2
        else:
            i += 1

    db = SessionLocal()
    try:
        user = create_user(
            db, email=email, display_name=name, password=password, role=role
        )
        print(f"create-user: Created {role.value} user: {user.email} (id={user.id})")
    except Exception as e:
        print(f"create-user: ERROR — {e}")
        sys.exit(1)
    finally:
        db.close()


def seed_maintainer():
    email = "maintainer@epibridge.local"
    password = "maintainer"
    display_name = "Maintainer"

    if len(sys.argv) >= 4:
        email = sys.argv[2]
        password = sys.argv[3]
    if len(sys.argv) >= 5:
        display_name = sys.argv[4]

    db = SessionLocal()
    try:
        user = get_or_create_user(
            db,
            email=email,
            display_name=display_name,
            password=password,
            role=UserRole.MAINTAINER,
        )
        print(
            f"seed-maintainer: Created/verified maintainer user: "
            f"{user.email} (id={user.id})"
        )
    except Exception as e:
        print(f"seed-maintainer: ERROR — {e}")
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
        print("Commands: seed-admin, seed-demo, create-user")
        sys.exit(1)

    command = sys.argv[1]
    if command == "seed-admin":
        seed_admin()
    elif command == "seed-maintainer":
        seed_maintainer()
    elif command == "seed-demo":
        seed_demo()
    elif command == "create-user":
        create_researcher()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
