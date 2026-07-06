from app.models.user import User, UserRole


def test_user_creation():
    user = User(
        email="admin@example.com",
        display_name="Admin",
        role=UserRole.ADMIN,
    )
    assert user.email == "admin@example.com"
    assert user.display_name == "Admin"
    assert user.role == UserRole.ADMIN


def test_user_email_unique_constraint():
    user1 = User(email="same@example.com", display_name="A", role=UserRole.ADMIN)
    user2 = User(email="same@example.com", display_name="B", role=UserRole.ADMIN)
    assert user1.email == user2.email
