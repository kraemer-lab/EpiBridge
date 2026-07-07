from app.auth.local import hash_password
from app.core.config import settings
from app.models.user import User, UserRole


def test_login_success(client, db_session):
    hashed = hash_password(settings.admin_password)
    user = User(
        email=settings.admin_email,
        display_name="Administrator",
        password_hash=hashed,
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "email": settings.admin_email,
            "password": settings.admin_password,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == settings.admin_email
    assert "session_id" in response.cookies


def test_login_invalid_password(client, db_session):
    hashed = hash_password(settings.admin_password)
    user = User(
        email=settings.admin_email,
        display_name="Administrator",
        password_hash=hashed,
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "email": settings.admin_email,
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401
    assert "session_id" not in response.cookies


def test_login_nonexistent_user(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "anything",
        },
    )
    assert response.status_code == 401


def test_get_me_authenticated(client):
    response = client.get("/api/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == settings.admin_email
    assert data["display_name"] == "Administrator"
    assert data["role"] == "admin"


def test_get_me_anonymous_rejected(anon_client):
    response = anon_client.get("/api/me")
    assert response.status_code == 401


def test_logout(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 204

    # Session should be invalidated
    me_response = client.get("/api/me")
    assert me_response.status_code == 401
