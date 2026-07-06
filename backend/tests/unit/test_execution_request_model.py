import uuid

from app.models.execution_request import ExecutionRequest, ExecutionRequestStatus


class TestExecutionRequestModel:
    def test_create_request(self):
        project_id = uuid.uuid4()
        bundle_id = uuid.uuid4()
        user_id = uuid.uuid4()
        request = ExecutionRequest(
            project_id=project_id,
            analysis_bundle_id=bundle_id,
            name="Baseline run",
            timeout_seconds=7200,
            parameter_overrides={"threshold": 0.01},
            requested_by_id=user_id,
        )
        assert request.project_id == project_id
        assert request.analysis_bundle_id == bundle_id
        assert request.name == "Baseline run"
        assert request.timeout_seconds == 7200
        assert request.parameter_overrides == {"threshold": 0.01}
        assert request.requested_by_id == user_id

    def test_default_timeout(self):
        request = ExecutionRequest(
            project_id=uuid.uuid4(),
            analysis_bundle_id=uuid.uuid4(),
            name="Default timeout",
            requested_by_id=uuid.uuid4(),
        )
        assert request.timeout_seconds is None  # server_default, not in-memory

    def test_default_status(self):
        request = ExecutionRequest(
            project_id=uuid.uuid4(),
            analysis_bundle_id=uuid.uuid4(),
            name="Default status",
            requested_by_id=uuid.uuid4(),
        )
        assert request.status is None  # server_default, not in-memory

    def test_status_enum_values(self):
        assert ExecutionRequestStatus.PENDING.value == "pending"
        assert ExecutionRequestStatus.RUNNING.value == "running"
        assert ExecutionRequestStatus.COMPLETED.value == "completed"
        assert ExecutionRequestStatus.FAILED.value == "failed"
        assert ExecutionRequestStatus.CANCELLED.value == "cancelled"

    def test_default_parameter_overrides(self):
        request = ExecutionRequest(
            project_id=uuid.uuid4(),
            analysis_bundle_id=uuid.uuid4(),
            name="No overrides",
            requested_by_id=uuid.uuid4(),
        )
        assert request.parameter_overrides is None  # server_default, not in-memory
