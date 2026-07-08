import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.analysis_bundle import AnalysisBundleStatus
from app.services.execution_request_service import (
    create_execution_request,
    generate_request_name,
    list_execution_requests,
    validate_timeout,
)

VALID_DATA = {
    "analysis_bundle_id": uuid.uuid4(),
    "name": "Test Run",
    "timeout_seconds": 3600,
    "parameter_overrides": {},
}


class TestGenerateRequestName:
    def test_includes_bundle_name(self):
        bundle = MagicMock()
        bundle.name = "Survival Analysis"
        name = generate_request_name(bundle)
        assert name.startswith("Survival Analysis @ ")


class TestValidateTimeout:
    def test_valid_timeout(self):
        validate_timeout(3600)

    def test_minimum_timeout(self):
        validate_timeout(60)

    def test_below_minimum_raises(self):
        with pytest.raises(ValueError, match="at least 60"):
            validate_timeout(59)

    def test_non_integer_raises(self):
        with pytest.raises(ValueError, match="at least 60"):
            validate_timeout(30.5)

    def test_exceeds_maximum_raises(self):
        with pytest.raises(ValueError, match="not exceed 86400"):
            validate_timeout(86401)


class TestCreateExecutionRequest:
    @patch("app.services.execution_request_service.generate_request_name")
    @patch("app.services.execution_request_service.validate_timeout")
    def test_successful_creation(self, mock_validate, mock_generate):
        db = MagicMock()
        bundle = MagicMock()
        bundle.id = VALID_DATA["analysis_bundle_id"]
        bundle.project_id = uuid.uuid4()
        bundle.name = "Test Bundle"
        bundle.status = AnalysisBundleStatus.APPROVED_FOR_EXECUTION
        db.query.return_value.filter.return_value.first.return_value = bundle
        mock_generate.return_value = "Test Bundle @ 2026-01-01 12:00"

        project_id = bundle.project_id
        user_id = uuid.uuid4()

        result = create_execution_request(db, VALID_DATA, project_id, user_id)

        assert result.project_id == project_id
        assert result.analysis_bundle_id == bundle.id
        assert result.name == "Test Run"
        assert result.timeout_seconds == 3600
        assert result.parameter_overrides == {}
        assert result.requested_by_id == user_id
        assert db.add.call_count >= 1
        db.commit.assert_called_once()

    @patch("app.services.execution_request_service.validate_timeout")
    def test_auto_generates_name(self, mock_validate):
        db = MagicMock()
        bundle = MagicMock()
        bundle.id = uuid.uuid4()
        bundle.project_id = uuid.uuid4()
        bundle.name = "Auto Bundle"
        bundle.status = AnalysisBundleStatus.APPROVED_FOR_EXECUTION
        db.query.return_value.filter.return_value.first.return_value = bundle

        data = VALID_DATA.copy()
        data["name"] = None

        result = create_execution_request(db, data, bundle.project_id, uuid.uuid4())
        assert result.name.startswith("Auto Bundle @ ")

    def test_bundle_not_found_raises(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Analysis bundle not found"):
            create_execution_request(db, VALID_DATA, uuid.uuid4(), uuid.uuid4())

    def test_bundle_wrong_project_raises(self):
        db = MagicMock()
        bundle = MagicMock()
        bundle.id = VALID_DATA["analysis_bundle_id"]
        bundle.project_id = uuid.uuid4()  # different from the one passed
        bundle.status = AnalysisBundleStatus.APPROVED_FOR_EXECUTION
        db.query.return_value.filter.return_value.first.return_value = bundle

        with pytest.raises(ValueError, match="does not belong to this project"):
            create_execution_request(db, VALID_DATA, uuid.uuid4(), uuid.uuid4())

    def test_unapproved_bundle_raises(self):
        db = MagicMock()
        bundle = MagicMock()
        bundle.id = VALID_DATA["analysis_bundle_id"]
        bundle.project_id = uuid.uuid4()
        bundle.status = AnalysisBundleStatus.DRAFT
        db.query.return_value.filter.return_value.first.return_value = bundle

        with pytest.raises(ValueError, match="approved"):
            create_execution_request(db, VALID_DATA, bundle.project_id, uuid.uuid4())


class TestListExecutionRequests:
    def test_list_all(self):
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = ["r1", "r2"]
        result = list_execution_requests(db)
        assert result == ["r1", "r2"]

    def test_list_by_project(self):
        db = MagicMock()
        project_id = uuid.uuid4()
        filtered_query = MagicMock()
        filtered_query.all.return_value = ["r1"]
        ordered_query = MagicMock()
        ordered_query.filter.return_value = filtered_query
        db.query.return_value.order_by.return_value = ordered_query
        result = list_execution_requests(db, project_id=project_id)
        assert result == ["r1"]
