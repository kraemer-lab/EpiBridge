import uuid

import pytest

from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.project import Project


@pytest.fixture
def project(db_session, admin_user):
    project = Project(name="Test Project", owner_id=admin_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


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


class TestAdminBundlesAPI:
    def test_list_bundles_empty(self, client, admin_user):
        response = client.get("/api/admin/bundles")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_bundles(
        self, client, admin_user, project, resource, execution_environment
    ):
        payload = {
            "name": "Survival Analysis",
            "execution_environment_id": str(execution_environment.id),
            "version": "1.0.0",
            "entrypoint": "run.py",
            "description": "A test",
            "resource_identifiers": ["test-resource"],
            "outputs": ["summary.csv"],
        }
        create_resp = client.post(
            f"/api/projects/{project.id}/bundles",
            json=payload,
        )
        assert create_resp.status_code == 201

        response = client.get("/api/admin/bundles")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Survival Analysis"
        assert data[0]["runtime"] == "python-3.13"
        assert data[0]["execution_environment_id"] == str(execution_environment.id)
        assert data[0]["version"] == "1.0.0"
        assert data[0]["entrypoint"] == "run.py"
        assert data[0]["resource_identifiers"] == ["test-resource"]
        assert data[0]["outputs"] == ["summary.csv"]

    def test_get_bundle_by_id(
        self, client, admin_user, project, resource, execution_environment
    ):
        create_payload = {
            "name": "My Bundle",
            "execution_environment_id": str(execution_environment.id),
            "version": "2.0.0",
            "entrypoint": "analysis.R",
            "resource_identifiers": [],
        }
        create_resp = client.post(
            f"/api/projects/{project.id}/bundles",
            json=create_payload,
        )
        assert create_resp.status_code == 201
        bundle_id = create_resp.json()["id"]

        response = client.get(f"/api/admin/bundles/{bundle_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Bundle"
        assert data["runtime"] == "python-3.13"
        assert data["version"] == "2.0.0"
        assert data["entrypoint"] == "analysis.R"

    def test_get_bundle_not_found(self, client, admin_user):
        url = f"/api/admin/bundles/{uuid.uuid4()}"
        response = client.get(url)
        assert response.status_code == 404

    def test_list_bundles_ordered_by_name(
        self, client, admin_user, project, resource, execution_environment
    ):
        for name in ["Zeta", "Alpha", "Beta"]:
            client.post(
                f"/api/projects/{project.id}/bundles",
                json={
                    "name": name,
                    "execution_environment_id": str(execution_environment.id),
                    "version": "1.0.0",
                    "entrypoint": "run.py",
                },
            )

        response = client.get("/api/admin/bundles")
        data = response.json()
        names = [b["name"] for b in data]
        assert names == sorted(names)

    def test_get_bundle_includes_resource_identifiers(
        self, client, admin_user, project, execution_environment, db_session
    ):
        r2 = DataResource(
            identifier="second-resource",
            name="Second",
            alias="second",
            provider_type="csv",
            endpoint={"path": "data.csv"},
            version="1.0.0",
            status="active",
        )
        db_session.add(r2)
        db_session.commit()

        payload = {
            "name": "Multi Resource Bundle",
            "execution_environment_id": str(execution_environment.id),
            "version": "1.0.0",
            "entrypoint": "run.py",
            "resource_identifiers": ["test-resource", "second-resource"],
        }
        create_resp = client.post(
            f"/api/projects/{project.id}/bundles",
            json=payload,
        )
        assert create_resp.status_code == 201
        bundle_id = create_resp.json()["id"]

        response = client.get(f"/api/admin/bundles/{bundle_id}")
        data = response.json()
        assert sorted(data["resource_identifiers"]) == [
            "second-resource",
            "test-resource",
        ]
