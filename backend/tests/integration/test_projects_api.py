import uuid

import pytest

from app.models.analysis_bundle import AnalysisBundle
from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.project import Project
from app.models.project_data_resource import ProjectResourceAllocation
from app.models.project_membership import ProjectMembership


@pytest.fixture
def project(db_session, admin_user):
    p = Project(name="Test Project", description="A test", owner_id=admin_user.id)
    db_session.add(p)
    db_session.flush()
    db_session.add(
        ProjectMembership(
            project_id=p.id, user_id=admin_user.id, created_by_id=admin_user.id
        )
    )
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


@pytest.fixture
def execution_environment(db_session):
    env = ExecutionEnvironment(
        identifier="python-3.13-scientific",
        name="Python 3.13 Scientific",
        runtime="python-3.13",
        description="Test environment",
        status="active",
    )
    db_session.add(env)
    db_session.commit()
    db_session.refresh(env)
    return env


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
        link = ProjectResourceAllocation(
            project_id=project.id,
            data_resource_id=resource.id,
            created_by_id=project.owner_id,
        )
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

    def test_revoke_resource(
        self,
        client,
        project,
        resource,
        db_session,
    ):
        link = ProjectResourceAllocation(
            project_id=project.id,
            data_resource_id=resource.id,
            created_by_id=project.owner_id,
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(f"/api/projects/{project.id}/resources")
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.delete(f"/api/projects/{project.id}/resources/{resource.id}")
        assert response.status_code == 204

        response = client.get(f"/api/projects/{project.id}/resources")
        assert response.status_code == 200
        assert response.json() == []


class TestGetProjectBundles:
    def test_bundles_empty(self, client, project):
        response = client.get(f"/api/projects/{project.id}/bundles")
        assert response.status_code == 200
        assert response.json() == []

    def test_bundles_with_data(
        self, client, project, resource, execution_environment, db_session
    ):
        link = ProjectResourceAllocation(
            project_id=project.id,
            data_resource_id=resource.id,
            created_by_id=project.owner_id,
        )
        db_session.add(link)

        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            execution_environment_id=execution_environment.id,
            name="My Bundle",
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
        assert data[0]["execution_environment_id"] == str(execution_environment.id)

    def test_bundles_ordered_by_name(
        self, client, project, execution_environment, db_session
    ):
        for name in ["Zeta", "Beta", "Alpha"]:
            db_session.add(
                AnalysisBundle(
                    project_id=project.id,
                    created_by_id=project.owner_id,
                    execution_environment_id=execution_environment.id,
                    name=name,
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
    def test_get_bundle_by_id(self, client, project, execution_environment, db_session):
        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            execution_environment_id=execution_environment.id,
            name="Detail Bundle",
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
        assert data["execution_environment_id"] == str(execution_environment.id)

    def test_get_bundle_not_found(self, client, project):
        response = client.get(f"/api/projects/{project.id}/bundles/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_bundle_wrong_project(
        self, client, admin_user, project, execution_environment, db_session
    ):
        other_project = Project(name="Other Project", owner_id=admin_user.id)
        db_session.add(other_project)
        db_session.commit()

        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=admin_user.id,
            execution_environment_id=execution_environment.id,
            name="Orphan",
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(bundle)
        db_session.commit()

        response = client.get(f"/api/projects/{other_project.id}/bundles/{bundle.id}")
        assert response.status_code == 404


class TestUpdateProjectBundle:
    def test_update_metadata(self, client, project, execution_environment, db_session):
        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            execution_environment_id=execution_environment.id,
            name="Original",
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

    def test_update_partial(self, client, project, execution_environment, db_session):
        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            execution_environment_id=execution_environment.id,
            name="Partial Test",
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

    def test_update_resources(
        self, client, project, resource, execution_environment, db_session
    ):
        allocation = ProjectResourceAllocation(
            project_id=project.id,
            data_resource_id=resource.id,
            created_by_id=project.owner_id,
        )
        db_session.add(allocation)

        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            execution_environment_id=execution_environment.id,
            name="Resource Bundle",
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

    def test_update_invalid_data(
        self, client, project, execution_environment, db_session
    ):
        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=project.owner_id,
            execution_environment_id=execution_environment.id,
            name="Invalid Test",
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


class TestProjectMembership:
    def test_list_members(self, client, project, admin_user):
        response = client.get(f"/api/projects/{project.id}/members")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == admin_user.email
        assert data[0]["display_name"] == admin_user.display_name
        assert data[0]["user_id"] == str(admin_user.id)

    def test_list_members_not_authenticated(self, anon_client, project):
        response = anon_client.get(f"/api/projects/{project.id}/members")
        assert response.status_code == 401

    def test_add_member(self, client, project, researcher_user):
        response = client.post(
            f"/api/projects/{project.id}/members",
            json={"email": researcher_user.email},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(researcher_user.id)
        assert data["display_name"] == researcher_user.display_name
        assert "added_at" in data

    def test_add_member_idempotent(self, client, project, admin_user):
        response = client.post(
            f"/api/projects/{project.id}/members",
            json={"email": admin_user.email},
        )
        assert response.status_code == 201

    def test_add_member_not_found(self, client, project):
        response = client.post(
            f"/api/projects/{project.id}/members",
            json={"email": "nonexistent@nowhere.local"},
        )
        assert response.status_code == 404

    def test_add_member_unauthorized(
        self, researcher_client, project, researcher_user, db_session
    ):
        # First add researcher to project via database
        from app.models.project_membership import ProjectMembership

        db_session.add(
            ProjectMembership(
                project_id=project.id,
                user_id=researcher_user.id,
                created_by_id=project.owner_id,
            )
        )
        db_session.commit()

        # Researcher lacks project.members.manage
        response = researcher_client.post(
            f"/api/projects/{project.id}/members",
            json={"email": "test@test.local"},
        )
        assert response.status_code == 403

    def test_remove_member(self, client, project, researcher_user, db_session):
        from app.models.project_membership import ProjectMembership

        db_session.add(
            ProjectMembership(
                project_id=project.id,
                user_id=researcher_user.id,
                created_by_id=project.owner_id,
            )
        )
        db_session.commit()

        response = client.delete(
            f"/api/projects/{project.id}/members/{researcher_user.id}"
        )
        assert response.status_code == 204

    def test_remove_member_not_found(self, client, project):
        import uuid

        response = client.delete(f"/api/projects/{project.id}/members/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_remove_member_unauthorized(self, researcher_client, project):
        response = researcher_client.delete(
            f"/api/projects/{project.id}/members/{uuid.uuid4()}"
        )
        assert response.status_code == 404
