from app.models.user import User, UserRole


def test_user_creation():
    user = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="argon2-hash-value",
        role=UserRole.ADMIN,
    )
    assert user.email == "admin@example.com"
    assert user.display_name == "Admin"
    assert user.role == UserRole.ADMIN
    assert user.password_hash == "argon2-hash-value"


def test_user_email_unique_constraint():
    user1 = User(
        email="same@example.com",
        display_name="A",
        password_hash="hash1",
        role=UserRole.ADMIN,
    )
    user2 = User(
        email="same@example.com",
        display_name="B",
        password_hash="hash2",
        role=UserRole.ADMIN,
    )
    assert user1.email == user2.email


def test_user_researcher_role():
    user = User(
        email="researcher@example.com",
        display_name="Researcher",
        password_hash="hash",
        role=UserRole.RESEARCHER,
    )
    assert user.role == UserRole.RESEARCHER
