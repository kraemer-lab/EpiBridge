from app.auth.local import hash_password
from app.core.config import settings
from app.models.user import User, UserRole


LOGIN_TEST_EMAIL = "logintest@epibridge.local"
LOGIN_TEST_PASSWORD = "login-test-pw"


def test_login_success(anon_client, db_session):
    hashed = hash_password(LOGIN_TEST_PASSWORD)
    user = User(
        email=LOGIN_TEST_EMAIL,
        display_name="Login Test",
        password_hash=hashed,
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()

    response = anon_client.post(
        "/api/auth/login",
        json={
            "email": LOGIN_TEST_EMAIL,
            "password": LOGIN_TEST_PASSWORD,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == LOGIN_TEST_EMAIL
    assert "session_id" in response.cookies


def test_login_invalid_password(anon_client, db_session):
    hashed = hash_password(LOGIN_TEST_PASSWORD)
    user = User(
        email=LOGIN_TEST_EMAIL,
        display_name="Login Test",
        password_hash=hashed,
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()

    response = anon_client.post(
        "/api/auth/login",
        json={
            "email": LOGIN_TEST_EMAIL,
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
