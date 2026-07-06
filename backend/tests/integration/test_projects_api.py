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


def test_list_projects_empty(client, admin_user):
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert response.json() == []


def test_create_project(client, admin_user):
    response = client.post(
        "/api/projects",
        json={"name": "My Project", "description": "A test project"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Project"
    assert data["description"] == "A test project"
    assert data["owner_id"] == str(admin_user.id)
    assert "id" in data


def test_create_project_minimal(client, admin_user):
    response = client.post(
        "/api/projects",
        json={"name": "Minimal"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal"
    assert data["description"] == ""


def test_list_projects_after_create(client, admin_user):
    client.post("/api/projects", json={"name": "Project A"})
    client.post("/api/projects", json={"name": "Project B"})

    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = [p["name"] for p in data]
    assert "Project A" in names
    assert "Project B" in names


def test_projects_persist(client, admin_user):
    client.post("/api/projects", json={"name": "Persistent Project"})

    response1 = client.get("/api/projects")
    assert len(response1.json()) == 1

    response2 = client.get("/api/projects")
    assert len(response2.json()) == 1
