"""Integration tests for the Data Resource artefact API.

Verifies that the publication-boundary policy is enforced at the API
layer — runtime data in ``data/`` is neither listed nor downloadable.
"""

import tempfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.models.data_resource import DataResource


@pytest.fixture
def artefact_resource(db_session):
    """Create a DataResource with a real artefact directory containing
    both published artefacts and runtime data, then restore settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        resource_dir = Path(tmpdir) / "test-resource-artefacts"
        resource_dir.mkdir()

        # Published artefacts
        (resource_dir / "DOCUMENTATION.md").write_text("# Docs\n")
        (resource_dir / "SCHEMA.md").write_text("# Schema\n")

        # Representative dataset — published for local development
        rep_dir = resource_dir / "representative"
        rep_dir.mkdir()
        (rep_dir / "demo.csv").write_text("id,value\n1,a\n")

        # Runtime data — must NOT be exposed through publication API
        data_dir = resource_dir / "data"
        data_dir.mkdir()
        (data_dir / "demo.csv").write_text(
            "id,age,region,outcome,exposed,vaccinated\n1,45,North,recovered,no,yes\n"
        )

        original_dir = settings.resource_manifest_dir
        settings.resource_manifest_dir = tmpdir
        try:
            resource = DataResource(
                identifier="test-resource-artefacts",
                name="Test Resource",
                alias="test-resource",
                provider_type="csv",
                endpoint={"path": "test-resource-artefacts/data"},
                description="Publication boundary test resource",
                version="1.0.0",
                status="active",
            )
            db_session.add(resource)
            db_session.commit()
            db_session.refresh(resource)
            yield resource
        finally:
            settings.resource_manifest_dir = original_dir


class TestResourceArtefactAPI:
    """API-level enforcement of the publication boundary."""

    def test_list_artefacts_excludes_runtime_data(
        self, client, admin_user, artefact_resource
    ):
        identifier = artefact_resource.identifier
        response = client.get(f"/api/resources/{identifier}/artefacts")
        assert response.status_code == 200
        data = response.json()
        assert "data/demo.csv" not in data["artefacts"]
        assert "DOCUMENTATION.md" in data["artefacts"]
        assert "SCHEMA.md" in data["artefacts"]
        assert "representative/demo.csv" in data["artefacts"]

    def test_download_runtime_data_returns_404(
        self, client, admin_user, artefact_resource
    ):
        identifier = artefact_resource.identifier
        response = client.get(f"/api/resources/{identifier}/artefacts/data/demo.csv")
        assert response.status_code == 404

    def test_download_runtime_data_subdirectory_returns_404(
        self, client, admin_user, artefact_resource
    ):
        identifier = artefact_resource.identifier
        response = client.get(
            f"/api/resources/{identifier}/artefacts/data/subdir/secret.csv"
        )
        assert response.status_code == 404

    def test_download_documentation_succeeds(
        self, client, admin_user, artefact_resource
    ):
        identifier = artefact_resource.identifier
        response = client.get(f"/api/resources/{identifier}/artefacts/DOCUMENTATION.md")
        assert response.status_code == 200
        assert response.text == "# Docs\n"

    def test_download_schema_succeeds(self, client, admin_user, artefact_resource):
        identifier = artefact_resource.identifier
        response = client.get(f"/api/resources/{identifier}/artefacts/SCHEMA.md")
        assert response.status_code == 200
        assert response.text == "# Schema\n"

    def test_download_representative_dataset_succeeds(
        self, client, admin_user, artefact_resource
    ):
        identifier = artefact_resource.identifier
        response = client.get(
            f"/api/resources/{identifier}/artefacts/representative/demo.csv"
        )
        assert response.status_code == 200
        assert response.text == "id,value\n1,a\n"

    def test_resource_not_found_returns_404(self, client, admin_user):
        response = client.get("/api/resources/nonexistent/artefacts")
        assert response.status_code == 404

    def test_artefact_not_found_returns_404(
        self, client, admin_user, artefact_resource
    ):
        identifier = artefact_resource.identifier
        response = client.get(f"/api/resources/{identifier}/artefacts/nonexistent.txt")
        assert response.status_code == 404

    def test_path_traversal_still_blocked(self, client, admin_user, artefact_resource):
        identifier = artefact_resource.identifier
        response = client.get(
            f"/api/resources/{identifier}/artefacts/%2e%2e%2fsecret.txt"
        )
        assert response.status_code == 403
