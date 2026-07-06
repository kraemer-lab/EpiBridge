import pytest

from app.core.config import settings
from app.models.user import User, UserRole


@pytest.fixture
def admin_user(db_session):
    user = User(
        email=settings.admin_email,
        display_name="Administrator",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_get_me_returns_authenticated_user(client, admin_user):
    response = client.get("/api/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == settings.admin_email
    assert data["display_name"] == "Administrator"
    assert data["role"] == "admin"
    assert "id" in data


def test_get_me_fails_without_admin_user(client):
    response = client.get("/api/me")
    assert response.status_code == 401
