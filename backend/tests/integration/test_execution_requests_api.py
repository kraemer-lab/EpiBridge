import uuid

import pytest

from app.models.analysis_bundle import AnalysisBundle
from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.project import Project


@pytest.fixture
def project(db_session, admin_user):
    p = Project(name="Test Project", description="A test", owner_id=admin_user.id)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


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


@pytest.fixture
def bundle(db_session, project, execution_environment):
    b = AnalysisBundle(
        project_id=project.id,
        created_by_id=project.owner_id,
        execution_environment_id=execution_environment.id,
        name="Survival Analysis",
        version="1.0.0",
        entrypoint="run.py",
        description="A test analysis",
        outputs=["summary.csv"],
        parameters={"threshold": 0.05},
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)
    return b


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


class TestCreateExecutionRequest:
    def test_create_with_name(self, client, project, bundle):
        response = client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "name": "Baseline run",
                "timeout_seconds": 7200,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Baseline run"
        assert data["analysis_name"] == "Survival Analysis"
        assert data["timeout_seconds"] == 7200
        assert data["status"] == "pending"
        assert data["analysis_bundle_id"] == str(bundle.id)
        assert data["runtime"] == "python-3.13"
        assert "id" in data
        assert "created_at" in data

    def test_auto_generates_name(self, client, project, bundle):
        response = client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"].startswith("Survival Analysis @ ")

    def test_bundle_not_in_project_returns_422(
        self, client, project, bundle, db_session
    ):
        other_project = Project(name="Other", owner_id=project.owner_id)
        db_session.add(other_project)
        db_session.commit()

        response = client.post(
            f"/api/projects/{other_project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
            },
        )
        assert response.status_code == 422
        assert "does not belong" in response.json()["detail"]

    def test_nonexistent_bundle_returns_422(self, client, project):
        response = client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422

    def test_invalid_timeout_returns_422(self, client, project, bundle):
        response = client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "timeout_seconds": 30,
            },
        )
        assert response.status_code == 422

    def test_default_parameter_overrides(self, client, project, bundle):
        response = client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "name": "Defaults test",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["parameter_overrides"] == {}
        assert data["parameters"] == {"threshold": 0.05}


class TestListExecutionRequests:
    def test_list_empty(self, client, project):
        response = client.get(f"/api/projects/{project.id}/execution-requests")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_after_create(self, client, project, bundle):
        client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "name": "Run 1",
            },
        )
        client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "name": "Run 2",
            },
        )

        response = client.get(f"/api/projects/{project.id}/execution-requests")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = [r["name"] for r in data]
        assert "Run 1" in names
        assert "Run 2" in names

    def test_ordered_by_created_at_desc(self, client, project, bundle):
        client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "name": "First",
            },
        )
        client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "name": "Second",
            },
        )

        response = client.get(f"/api/projects/{project.id}/execution-requests")
        data = response.json()
        assert data[0]["name"] == "Second"
        assert data[1]["name"] == "First"

    def test_project_isolation(self, client, project, bundle, db_session):
        other_project = Project(name="Other", owner_id=project.owner_id)
        db_session.add(other_project)
        db_session.commit()

        client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "name": "My Request",
            },
        )

        response = client.get(f"/api/projects/{other_project.id}/execution-requests")
        assert response.status_code == 200
        assert response.json() == []


class TestGetExecutionRequest:
    def test_get_by_id(self, client, project, bundle):
        create_resp = client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "name": "Detail Test",
            },
        )
        er_id = create_resp.json()["id"]

        response = client.get(f"/api/projects/{project.id}/execution-requests/{er_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Detail Test"
        assert data["analysis_name"] == "Survival Analysis"
        assert data["status"] == "pending"
        assert data["runtime"] == "python-3.13"
        assert data["resource_identifiers"] == []

    def test_get_not_found(self, client, project):
        response = client.get(
            f"/api/projects/{project.id}/execution-requests/{uuid.uuid4()}"
        )
        assert response.status_code == 404

    def test_get_wrong_project(self, client, project, bundle, db_session):
        other_project = Project(name="Other", owner_id=project.owner_id)
        db_session.add(other_project)
        db_session.commit()

        create_resp = client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={
                "analysis_bundle_id": str(bundle.id),
                "name": "Hidden",
            },
        )
        er_id = create_resp.json()["id"]

        response = client.get(
            f"/api/projects/{other_project.id}/execution-requests/{er_id}"
        )
        assert response.status_code == 404


class TestAdminExecutionRequests:
    def test_admin_list_all(self, client, admin_user, project, bundle, db_session):
        p2 = Project(name="Project 2", owner_id=admin_user.id)
        db_session.add(p2)
        db_session.commit()

        b2 = AnalysisBundle(
            project_id=p2.id,
            created_by_id=admin_user.id,
            execution_environment_id=bundle.execution_environment_id,
            name="Analysis 2",
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(b2)
        db_session.commit()

        client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={"analysis_bundle_id": str(bundle.id), "name": "Req 1"},
        )
        client.post(
            f"/api/projects/{p2.id}/execution-requests",
            json={"analysis_bundle_id": str(b2.id), "name": "Req 2"},
        )

        response = client.get("/api/admin/execution-requests")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_admin_get_by_id(self, client, admin_user, project, bundle):
        create_resp = client.post(
            f"/api/projects/{project.id}/execution-requests",
            json={"analysis_bundle_id": str(bundle.id), "name": "Admin Get"},
        )
        er_id = create_resp.json()["id"]

        response = client.get(f"/api/admin/execution-requests/{er_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Admin Get"
        assert data["status"] == "pending"
        assert data["analysis_name"] == "Survival Analysis"
        assert data["runtime"] == "python-3.13"
