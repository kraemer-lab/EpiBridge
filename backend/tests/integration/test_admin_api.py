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
