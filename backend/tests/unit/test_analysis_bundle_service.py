import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services.analysis_bundle_service import (
    create_bundle,
    update_bundle,
    validate_entrypoint,
    validate_execution_environment,
    validate_manifest,
    validate_resources,
)

EE_ID = uuid.uuid4()

VALID_MANIFEST = {
    "name": "Survival Analysis",
    "execution_environment_id": EE_ID,
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
        del data["execution_environment_id"]
        with pytest.raises(ValueError, match="execution_environment_id"):
            validate_manifest(data)

    def test_missing_multiple_fields(self):
        data = {"name": "Foo"}
        with pytest.raises(
            ValueError, match="entrypoint, execution_environment_id, version"
        ):
            validate_manifest(data)

    def test_empty_name(self):
        data = VALID_MANIFEST.copy()
        data["name"] = ""
        with pytest.raises(ValueError, match="name"):
            validate_manifest(data)

    def test_empty_version(self):
        data = VALID_MANIFEST.copy()
        data["version"] = "   "
        with pytest.raises(ValueError, match="version"):
            validate_manifest(data)

    def test_empty_entrypoint(self):
        data = VALID_MANIFEST.copy()
        data["entrypoint"] = ""
        with pytest.raises(ValueError, match="entrypoint"):
            validate_manifest(data)

    def test_invalid_execution_environment_id(self):
        data = VALID_MANIFEST.copy()
        data["execution_environment_id"] = "not-a-uuid"
        with pytest.raises(ValueError, match="execution_environment_id.*UUID"):
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
            "execution_environment_id": EE_ID,
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
        project_id = uuid.uuid4()
        db = MagicMock()
        r1 = MagicMock()
        r1.identifier = "ukbb-phenotypes"
        r1.id = uuid.uuid4()
        r2 = MagicMock()
        r2.identifier = "mex-dengue-2026"
        r2.id = uuid.uuid4()
        db.query.return_value.filter.return_value.all.side_effect = [
            [r1, r2],
            [(r1.id,), (r2.id,)],
        ]

        result = validate_resources(
            ["ukbb-phenotypes", "mex-dengue-2026"], project_id, db
        )
        assert len(result) == 2

    def test_missing_resource_raises(self):
        project_id = uuid.uuid4()
        db = MagicMock()
        r1 = MagicMock()
        r1.identifier = "ukbb-phenotypes"
        r1.id = uuid.uuid4()
        db.query.return_value.filter.return_value.all.return_value = [r1]

        with pytest.raises(ValueError, match="mex-dengue-2026"):
            validate_resources(["ukbb-phenotypes", "mex-dengue-2026"], project_id, db)

    def test_empty_list_returns_empty(self):
        project_id = uuid.uuid4()
        db = MagicMock()
        result = validate_resources([], project_id, db)
        assert result == []
        db.query.assert_not_called()

    def test_missing_resource_raises_with_correct_message(self):
        project_id = uuid.uuid4()
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        with pytest.raises(ValueError, match="not found"):
            validate_resources(["nonexistent-resource"], project_id, db)


class TestValidateExecutionEnvironment:
    def test_environment_found(self):
        db = MagicMock()
        env = MagicMock()
        env.id = uuid.uuid4()
        db.query.return_value.filter.return_value.first.return_value = env

        result = validate_execution_environment(EE_ID, db)
        assert result is env

    def test_environment_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Execution environment not found"):
            validate_execution_environment(uuid.uuid4(), db)


class TestCreateBundle:
    @patch("app.services.analysis_bundle_service.validate_resources")
    @patch("app.services.analysis_bundle_service.validate_execution_environment")
    def test_creates_bundle_successfully(
        self, mock_validate_ee, mock_validate_resources
    ):
        db = MagicMock()
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()

        resource = MagicMock()
        resource.id = uuid.uuid4()
        resource.identifier = "ukbb-phenotypes"
        mock_validate_resources.return_value = [resource]
        mock_validate_ee.return_value = MagicMock()

        result = create_bundle(
            db,
            VALID_MANIFEST,
            project_id,
            user_id,
        )

        assert result.project_id == project_id
        assert result.created_by_id == user_id
        assert result.execution_environment_id == EE_ID
        assert result.name == "Survival Analysis"
        assert result.version == "1.0.0"
        assert result.entrypoint == "run.py"
        assert result.outputs == ["summary.csv"]
        assert result.parameters == {"threshold": 0.05}
        db.add.assert_called()
        db.commit.assert_called_once()

    @patch("app.services.analysis_bundle_service.validate_resources")
    @patch("app.services.analysis_bundle_service.validate_execution_environment")
    def test_no_resources_creates_bundle(
        self, mock_validate_ee, mock_validate_resources
    ):
        db = MagicMock()
        mock_validate_resources.return_value = []
        mock_validate_ee.return_value = MagicMock()

        data = VALID_MANIFEST.copy()
        data["resource_identifiers"] = []

        result = create_bundle(db, data, uuid.uuid4(), uuid.uuid4())
        assert result.name == "Survival Analysis"
        assert result.data_resources == []

    @patch("app.services.analysis_bundle_service.validate_resources")
    def test_invalid_manifest_raises(self, mock_validate_resources):
        db = MagicMock()
        data = {"name": "Incomplete"}
        with pytest.raises(ValueError, match="execution_environment_id"):
            create_bundle(db, data, uuid.uuid4(), uuid.uuid4())
        db.commit.assert_not_called()


class TestUpdateBundle:
    def test_update_name_only(self):
        db = MagicMock()
        bundle = MagicMock()
        bundle.id = uuid.uuid4()
        db.query.return_value.filter.return_value.first.return_value = bundle

        update_bundle(db, bundle.id, {"name": "New Name"})

        assert bundle.name == "New Name"
        db.commit.assert_called_once()

    @patch("app.services.analysis_bundle_service.validate_execution_environment")
    def test_update_all_fields(self, mock_validate_ee):
        db = MagicMock()
        bundle = MagicMock()
        bundle.id = uuid.uuid4()
        bundle.data_resources = []
        db.query.return_value.filter.return_value.first.return_value = bundle
        mock_validate_ee.return_value = MagicMock()

        new_ee_id = uuid.uuid4()
        data = {
            "name": "Updated",
            "execution_environment_id": new_ee_id,
            "version": "2.0.0",
            "entrypoint": "analysis.R",
            "description": "Updated description",
            "outputs": ["results.csv"],
            "parameters": {"alpha": 0.01},
            "resource_identifiers": [],
        }
        update_bundle(db, bundle.id, data)

        assert bundle.name == "Updated"
        assert bundle.execution_environment_id == new_ee_id
        assert bundle.version == "2.0.0"
        assert bundle.entrypoint == "analysis.R"
        assert bundle.description == "Updated description"
        assert bundle.outputs == ["results.csv"]
        assert bundle.parameters == {"alpha": 0.01}

    def test_update_nonexistent_raises(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            update_bundle(db, uuid.uuid4(), {"name": "Nope"})

    def test_update_invalid_name_raises(self):
        db = MagicMock()
        bundle = MagicMock()
        bundle.id = uuid.uuid4()
        db.query.return_value.filter.return_value.first.return_value = bundle

        with pytest.raises(ValueError, match="name"):
            update_bundle(db, bundle.id, {"name": ""})

    def test_update_invalid_entrypoint_path_raises(self):
        db = MagicMock()
        bundle = MagicMock()
        bundle.id = uuid.uuid4()
        db.query.return_value.filter.return_value.first.return_value = bundle

        with pytest.raises(ValueError, match="filename"):
            update_bundle(db, bundle.id, {"entrypoint": "src/run.py"})
