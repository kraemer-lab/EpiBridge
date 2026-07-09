import pytest

from app.models.data_resource import DataResource


@pytest.fixture
def seeded_resources(db_session):
    resources = [
        DataResource(
            identifier="res-1",
            name="Resource One",
            alias="resource_one",
            provider_type="csv",
            endpoint={"path": "data.csv"},
            version="1.0.0",
            status="active",
        ),
        DataResource(
            identifier="res-2",
            name="Resource Two",
            alias="resource_two",
            provider_type="csv",
            endpoint={"path": "data2.csv"},
            version="2.0.0",
            status="active",
        ),
    ]
    for r in resources:
        db_session.add(r)
    db_session.commit()
    for r in resources:
        db_session.refresh(r)
    return resources


class TestAdminResources:
    def test_list_resources_empty(self, client, admin_user):
        response = client.get("/api/admin/resources")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_resources(self, client, admin_user, seeded_resources):
        response = client.get("/api/admin/resources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        names = {r["name"] for r in data}
        assert "Resource One" in names
        assert "Resource Two" in names

    def test_list_resources_returns_fields(self, client, admin_user, seeded_resources):
        response = client.get("/api/admin/resources")
        assert response.status_code == 200
        resource = response.json()[0]
        assert "id" in resource
        assert resource["identifier"] == "res-1"
        assert resource["alias"] == "resource_one"
        assert resource["provider_type"] == "csv"
        assert resource["version"] == "1.0.0"
        assert resource["status"] == "active"

    def test_get_resource_by_id(self, client, admin_user, seeded_resources):
        resource_id = seeded_resources[0].id
        response = client.get(f"/api/admin/resources/{resource_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "res-1"
        assert data["name"] == "Resource One"
        assert data["alias"] == "resource_one"

    def test_get_resource_not_found(self, client, admin_user):
        url = "/api/admin/resources/00000000-0000-0000-0000-000000000000"
        response = client.get(url)
        assert response.status_code == 404

    def test_resources_ordered_by_name(self, client, admin_user, seeded_resources):
        response = client.get("/api/admin/resources")
        data = response.json()
        names = [r["name"] for r in data]
        assert names == sorted(names)


class TestAdminAuthorisation:
    def test_resources_unauthorized(self, researcher_client):
        response = researcher_client.get("/api/admin/resources")
        assert response.status_code == 403

    def test_resource_by_id_unauthorized(self, researcher_client):
        import uuid

        response = researcher_client.get(f"/api/admin/resources/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_execution_environments_unauthorized(self, researcher_client):
        response = researcher_client.get("/api/admin/execution-environments")
        assert response.status_code == 403

    def test_execution_environment_by_id_unauthorized(self, researcher_client):
        import uuid

        response = researcher_client.get(
            f"/api/admin/execution-environments/{uuid.uuid4()}"
        )
        assert response.status_code == 403

    def test_bundles_unauthorized(self, researcher_client):
        response = researcher_client.get("/api/admin/bundles")
        assert response.status_code == 403

    def test_bundle_by_id_unauthorized(self, researcher_client):
        import uuid

        response = researcher_client.get(f"/api/admin/bundles/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_execution_requests_unauthorized(self, researcher_client):
        response = researcher_client.get("/api/admin/execution-requests")
        assert response.status_code == 403

    def test_execution_request_by_id_unauthorized(self, researcher_client):
        import uuid

        response = researcher_client.get(
            f"/api/admin/execution-requests/{uuid.uuid4()}"
        )
        assert response.status_code == 403

    def test_output_sets_unauthorized(self, researcher_client):
        response = researcher_client.get("/api/admin/output-sets")
        assert response.status_code == 403

    def test_output_set_by_id_unauthorized(self, researcher_client):
        import uuid

        response = researcher_client.get(f"/api/admin/output-sets/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_output_by_id_unauthorized(self, researcher_client):
        import uuid

        response = researcher_client.get(f"/api/admin/outputs/{uuid.uuid4()}")
        assert response.status_code == 403


class TestAdminUsers:
    def test_list_users(self, client, admin_user, researcher_user, moderator_user):
        response = client.get("/api/admin/users")
        assert response.status_code == 200
        data = response.json()
        emails = {u["email"] for u in data}
        assert admin_user.email in emails
        assert researcher_user.email in emails
        assert moderator_user.email in emails

    def test_list_users_unauthorized(self, researcher_client):
        response = researcher_client.get("/api/admin/users")
        assert response.status_code == 403

    def test_list_users_anonymous(self, anon_client):
        response = anon_client.get("/api/admin/users")
        assert response.status_code == 401

    def test_create_user(self, client, db_session):
        response = client.post(
            "/api/admin/users",
            json={
                "email": "new@test.local",
                "display_name": "New User",
                "password": "test-secret",
                "role": "researcher",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@test.local"
        assert data["display_name"] == "New User"
        assert data["role"] == "researcher"
        assert "capabilities" in data
        assert "project.manage" in data["capabilities"]
        assert "user.manage" not in data["capabilities"]

    def test_create_user_default_role(self, client):
        response = client.post(
            "/api/admin/users",
            json={
                "email": "default@test.local",
                "display_name": "Default Role",
                "password": "test-secret",
            },
        )
        assert response.status_code == 201
        assert response.json()["role"] == "researcher"

    def test_create_user_short_password_rejected(self, client):
        response = client.post(
            "/api/admin/users",
            json={
                "email": "shortpw@test.local",
                "display_name": "Short Password",
                "password": "short",
                "role": "researcher",
            },
        )
        assert response.status_code == 422

    def test_create_user_duplicate_email(self, client, admin_user):
        response = client.post(
            "/api/admin/users",
            json={
                "email": admin_user.email,
                "display_name": "Duplicate",
                "password": "test-secret",
            },
        )
        assert response.status_code == 409

    def test_create_user_unauthorized(self, researcher_client):
        response = researcher_client.post(
            "/api/admin/users",
            json={
                "email": "should@fail.local",
                "display_name": "Should Fail",
                "password": "test-secret",
            },
        )
        assert response.status_code == 403

    def test_get_user_by_id(self, client, researcher_user):
        response = client.get(f"/api/admin/users/{researcher_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == researcher_user.email
        assert data["display_name"] == "Researcher User"
        assert data["role"] == "researcher"

    def test_get_user_not_found(self, client):
        import uuid

        response = client.get(f"/api/admin/users/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_create_user_moderator(self, client):
        response = client.post(
            "/api/admin/users",
            json={
                "email": "mod@test.local",
                "display_name": "Moderator",
                "password": "test-secret",
                "role": "moderator",
            },
        )
        assert response.status_code == 201
        caps = response.json()["capabilities"]
        assert "bundle.review" in caps
        assert "output.review" in caps
        assert "output.release" not in caps
        assert "data.manage" not in caps

    def test_create_user_maintainer(self, client):
        response = client.post(
            "/api/admin/users",
            json={
                "email": "maint@test.local",
                "display_name": "Maintainer",
                "password": "test-secret",
                "role": "maintainer",
            },
        )
        assert response.status_code == 201
        caps = response.json()["capabilities"]
        assert "output.release" in caps
        assert "data.manage" in caps
        assert "user.manage" not in caps

    def test_create_user_admin(self, client):
        response = client.post(
            "/api/admin/users",
            json={
                "email": "admin2@test.local",
                "display_name": "Admin Two",
                "password": "test-secret",
                "role": "admin",
            },
        )
        assert response.status_code == 201
        caps = response.json()["capabilities"]
        assert "user.manage" in caps
