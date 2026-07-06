import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services.analysis_bundle_service import (
    create_bundle,
    validate_entrypoint,
    validate_manifest,
    validate_resources,
)

VALID_MANIFEST = {
    "name": "Survival Analysis",
    "runtime": "python-3.13",
    "version": "1.0.0",
    "entrypoint": "run.py",
    "description": "A test analysis",
    "resource_identifiers": ["ukbb-phenotypes"],
    "outputs": ["summary.csv"],
    "parameters": {"threshold": 0.05},
}


class TestValidateManifest:
    def test_valid_manifest(self):
        result = validate_manifest(VALID_MANIFEST)
        assert result["name"] == "Survival Analysis"

    def test_missing_required_field(self):
        data = VALID_MANIFEST.copy()
        del data["runtime"]
        with pytest.raises(ValueError, match="runtime"):
            validate_manifest(data)

    def test_missing_multiple_fields(self):
        data = {"name": "Foo"}
        with pytest.raises(ValueError, match="entrypoint, runtime, version"):
            validate_manifest(data)

    def test_empty_name(self):
        data = VALID_MANIFEST.copy()
        data["name"] = ""
        with pytest.raises(ValueError, match="name"):
            validate_manifest(data)

    def test_empty_runtime(self):
        data = VALID_MANIFEST.copy()
        data["runtime"] = "   "
        with pytest.raises(ValueError, match="runtime"):
            validate_manifest(data)

    def test_empty_entrypoint(self):
        data = VALID_MANIFEST.copy()
        data["entrypoint"] = ""
        with pytest.raises(ValueError, match="entrypoint"):
            validate_manifest(data)

    def test_resources_not_a_list(self):
        data = VALID_MANIFEST.copy()
        data["resource_identifiers"] = "not a list"
        with pytest.raises(ValueError, match="resource_identifiers.*list"):
            validate_manifest(data)

    def test_outputs_not_a_list(self):
        data = VALID_MANIFEST.copy()
        data["outputs"] = "not a list"
        with pytest.raises(ValueError, match="outputs.*list"):
            validate_manifest(data)

    def test_parameters_not_a_dict(self):
        data = VALID_MANIFEST.copy()
        data["parameters"] = "not a dict"
        with pytest.raises(ValueError, match="parameters.*dict"):
            validate_manifest(data)

    def test_optional_fields_default(self):
        data = {
            "name": "Minimal",
            "runtime": "python-3.13",
            "version": "1.0.0",
            "entrypoint": "run.py",
        }
        result = validate_manifest(data)
        assert result["name"] == "Minimal"


class TestValidateEntrypoint:
    def test_valid_entrypoint(self):
        validate_entrypoint("run.py")

    def test_empty_entrypoint(self):
        with pytest.raises(ValueError, match="Entrypoint must not be empty"):
            validate_entrypoint("")

    def test_entrypoint_with_path(self):
        with pytest.raises(ValueError, match="filename"):
            validate_entrypoint("src/run.py")

    def test_entrypoint_with_absolute_path(self):
        with pytest.raises(ValueError, match="filename"):
            validate_entrypoint("/home/user/run.py")


class TestValidateResources:
    def test_all_resources_found(self):
        db = MagicMock()
        r1 = MagicMock()
        r1.identifier = "ukbb-phenotypes"
        r2 = MagicMock()
        r2.identifier = "mex-dengue-2026"
        db.query.return_value.filter.return_value.all.return_value = [r1, r2]

        result = validate_resources(["ukbb-phenotypes", "mex-dengue-2026"], db)
        assert len(result) == 2

    def test_missing_resource_raises(self):
        db = MagicMock()
        r1 = MagicMock()
        r1.identifier = "ukbb-phenotypes"
        db.query.return_value.filter.return_value.all.return_value = [r1]

        with pytest.raises(ValueError, match="mex-dengue-2026"):
            validate_resources(["ukbb-phenotypes", "mex-dengue-2026"], db)

    def test_empty_list_returns_empty(self):
        db = MagicMock()
        result = validate_resources([], db)
        assert result == []
        db.query.assert_not_called()

    def test_missing_resource_raises_with_correct_message(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        with pytest.raises(ValueError, match="not found"):
            validate_resources(["nonexistent-resource"], db)


class TestCreateBundle:
    @patch("app.services.analysis_bundle_service.validate_resources")
    def test_creates_bundle_successfully(self, mock_validate_resources):
        db = MagicMock()
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()

        resource = MagicMock()
        resource.id = uuid.uuid4()
        resource.identifier = "ukbb-phenotypes"
        mock_validate_resources.return_value = [resource]

        result = create_bundle(
            db,
            VALID_MANIFEST,
            project_id,
            user_id,
        )

        assert result.project_id == project_id
        assert result.created_by_id == user_id
        assert result.name == "Survival Analysis"
        assert result.runtime == "python-3.13"
        assert result.version == "1.0.0"
        assert result.entrypoint == "run.py"
        assert result.outputs == ["summary.csv"]
        assert result.parameters == {"threshold": 0.05}
        db.add.assert_called()
        db.commit.assert_called_once()

    @patch("app.services.analysis_bundle_service.validate_resources")
    def test_no_resources_creates_bundle(self, mock_validate_resources):
        db = MagicMock()
        mock_validate_resources.return_value = []

        data = VALID_MANIFEST.copy()
        data["resource_identifiers"] = []

        result = create_bundle(db, data, uuid.uuid4(), uuid.uuid4())
        assert result.name == "Survival Analysis"
        assert result.data_resources == []

    @patch("app.services.analysis_bundle_service.validate_resources")
    def test_invalid_manifest_raises(self, mock_validate_resources):
        db = MagicMock()
        data = {"name": "Incomplete"}
        with pytest.raises(ValueError, match="runtime"):
            create_bundle(db, data, uuid.uuid4(), uuid.uuid4())
        db.commit.assert_not_called()
