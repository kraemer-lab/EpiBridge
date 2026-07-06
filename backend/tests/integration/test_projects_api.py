import uuid

import pytest

from app.core.config import settings
from app.models.analysis_bundle import AnalysisBundle
from app.models.data_resource import DataResource
from app.models.project import Project
from app.models.project_data_resource import ProjectDataResource
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


@pytest.fixture
def project(db_session, admin_user):
    p = Project(name="Test Project", description="A test", owner_id=admin_user.id)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def resource(db_session):
    r = DataResource(
        identifier="test-resource",
        name="Test Resource",
        alias="test_resource",
        provider_type="csv",
        endpoint={"path": "data.csv"},
        version="1.0.0",
        status="active",
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


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


class TestGetProject:
    def test_get_project_by_id(self, client, project):
        response = client.get(f"/api/projects/{project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test"
        assert data["id"] == str(project.id)

    def test_get_project_not_found(self, client, admin_user):
        response = client.get(f"/api/projects/{uuid.uuid4()}")
        assert response.status_code == 404


class TestGetProjectResources:
    def test_resources_empty(self, client, project):
        response = client.get(f"/api/projects/{project.id}/resources")
        assert response.status_code == 200
        assert response.json() == []

    def test_resources_with_data(self, client, project, resource, db_session):
        link = ProjectDataResource(project_id=project.id, data_resource_id=resource.id)
        db_session.add(link)
        db_session.commit()

        response = client.get(f"/api/projects/{project.id}/resources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["identifier"] == "test-resource"
        assert data[0]["name"] == "Test Resource"
        assert data[0]["provider_type"] == "csv"

    def test_resources_not_found(self, client, admin_user):
        response = client.get(f"/api/projects/{uuid.uuid4()}/resources")
        assert response.status_code == 404


class TestGetProjectBundles:
    def test_bundles_empty(self, client, project):
        response = client.get(f"/api/projects/{project.id}/bundles")
        assert response.status_code == 200
        assert response.json() == []

    def test_bundles_with_data(self, client, project, resource, db_session):
        link = ProjectDataResource(project_id=project.id, data_resource_id=resource.id)
        db_session.add(link)

        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            name="My Bundle",
            runtime="python-3.13",
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(bundle)
        db_session.commit()

        response = client.get(f"/api/projects/{project.id}/bundles")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "My Bundle"
        assert data[0]["runtime"] == "python-3.13"

    def test_bundles_ordered_by_name(self, client, project, db_session):
        for name in ["Zeta", "Beta", "Alpha"]:
            db_session.add(
                AnalysisBundle(
                    project_id=project.id,
                    created_by_id=project.owner_id,
                    name=name,
                    runtime="python-3.13",
                    version="1.0.0",
                    entrypoint="run.py",
                )
            )
        db_session.commit()

        response = client.get(f"/api/projects/{project.id}/bundles")
        data = response.json()
        names = [b["name"] for b in data]
        assert names == ["Alpha", "Beta", "Zeta"]

    def test_bundles_not_found(self, client, admin_user):
        response = client.get(f"/api/projects/{uuid.uuid4()}/bundles")
        assert response.status_code == 404


class TestGetProjectBundle:
    def test_get_bundle_by_id(self, client, project, db_session):
        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            name="Detail Bundle",
            runtime="python-3.13",
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(bundle)
        db_session.commit()
        db_session.refresh(bundle)

        response = client.get(f"/api/projects/{project.id}/bundles/{bundle.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Detail Bundle"
        assert data["status"] == "draft"
        assert data["runtime"] == "python-3.13"
        assert data["version"] == "1.0.0"

    def test_get_bundle_not_found(self, client, project):
        response = client.get(f"/api/projects/{project.id}/bundles/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_bundle_wrong_project(self, client, admin_user, db_session):
        bundle = AnalysisBundle(
            project_id=uuid.uuid4(),
            created_by_id=admin_user.id,
            name="Orphan",
            runtime="python-3.13",
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(bundle)
        db_session.commit()

        response = client.get(f"/api/projects/{uuid.uuid4()}/bundles/{bundle.id}")
        assert response.status_code == 404


class TestUpdateProjectBundle:
    def test_update_metadata(self, client, project, db_session):
        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            name="Original",
            runtime="python-3.13",
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(bundle)
        db_session.commit()
        db_session.refresh(bundle)

        response = client.put(
            f"/api/projects/{project.id}/bundles/{bundle.id}",
            json={"name": "Updated", "description": "New desc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["description"] == "New desc"
        assert data["runtime"] == "python-3.13"

    def test_update_partial(self, client, project, db_session):
        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            name="Partial Test",
            runtime="python-3.13",
            version="1.0.0",
            entrypoint="run.py",
            description="Original description",
        )
        db_session.add(bundle)
        db_session.commit()
        db_session.refresh(bundle)

        response = client.put(
            f"/api/projects/{project.id}/bundles/{bundle.id}",
            json={"description": "Only this changes"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Partial Test"
        assert data["runtime"] == "python-3.13"
        assert data["description"] == "Only this changes"
        assert data["version"] == "1.0.0"

    def test_update_resources(self, client, project, resource, db_session):
        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            name="Resource Bundle",
            runtime="python-3.13",
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(bundle)
        db_session.commit()
        db_session.refresh(bundle)

        response = client.put(
            f"/api/projects/{project.id}/bundles/{bundle.id}",
            json={"resource_identifiers": ["test-resource"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource_identifiers"] == ["test-resource"]

    def test_update_not_found(self, client, project):
        response = client.put(
            f"/api/projects/{project.id}/bundles/{uuid.uuid4()}",
            json={"name": "Nope"},
        )
        assert response.status_code == 404

    def test_update_invalid_data(self, client, project, db_session):
        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            name="Invalid Test",
            runtime="python-3.13",
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(bundle)
        db_session.commit()
        db_session.refresh(bundle)

        response = client.put(
            f"/api/projects/{project.id}/bundles/{bundle.id}",
            json={"entrypoint": "path/to/file.py"},
        )
        assert response.status_code == 422
