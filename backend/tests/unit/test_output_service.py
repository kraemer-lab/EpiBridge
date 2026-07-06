import uuid
from unittest.mock import MagicMock

import pytest

from app.models.execution_request import ExecutionRequestStatus
from app.services.output_service import (
    get_output,
    list_outputs,
    register_output,
    transition_request_status,
)


class TestRegisterOutput:
    def test_registers_successfully(self):
        db = MagicMock()
        er_id = uuid.uuid4()

        result = register_output(db, er_id, "summary.csv", 1024)

        assert result.execution_request_id == er_id
        assert result.filename == "summary.csv"
        assert result.size == 1024
        db.add.assert_called_once()
        db.commit.assert_called_once()


class TestListOutputs:
    def test_list_empty(self):
        db = MagicMock()
        (
            db.query.return_value.filter.return_value.order_by.return_value.all.return_value
        ) = []
        result = list_outputs(db, uuid.uuid4())
        assert result == []

    def test_list_with_data(self):
        db = MagicMock()
        expected = [MagicMock(), MagicMock()]
        (
            db.query.return_value.filter.return_value.order_by.return_value.all.return_value
        ) = expected
        result = list_outputs(db, uuid.uuid4())
        assert result == expected


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
