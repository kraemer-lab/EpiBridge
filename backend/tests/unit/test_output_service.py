import uuid
from unittest.mock import MagicMock

import pytest

from app.models.execution_request import ExecutionRequestStatus
from app.services.output_service import get_output, transition_request_status


class TestGetOutput:
    def test_found(self):
        db = MagicMock()
        expected = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = expected
        result = get_output(db, uuid.uuid4())
        assert result == expected

    def test_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = get_output(db, uuid.uuid4())
        assert result is None


class TestTransitionRequestStatus:
    def test_transition(self):
        db = MagicMock()
        request = MagicMock()
        request.id = uuid.uuid4()
        db.query.return_value.filter.return_value.first.return_value = request

        result = transition_request_status(
            db, request.id, ExecutionRequestStatus.RUNNING
        )

        assert request.status == ExecutionRequestStatus.RUNNING
        assert result == request
        db.commit.assert_called_once()

    def test_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Execution request not found"):
            transition_request_status(db, uuid.uuid4(), ExecutionRequestStatus.RUNNING)
