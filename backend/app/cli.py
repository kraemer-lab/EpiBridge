import sys


def seed_admin():
    try:
        from app.core.config import settings
    except Exception as e:
        print(f"seed-admin: ERROR — could not load config: {e}")
        print("seed-admin: Ensure .env exists in the project root.")
        sys.exit(1)

    print(f"seed-admin: ADMIN_EMAIL={settings.admin_email}")
    print("seed-admin: SKIP — User model not yet implemented")
    sys.exit(0)


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
