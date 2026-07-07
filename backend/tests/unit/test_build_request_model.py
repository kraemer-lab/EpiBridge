import uuid

from app.models.build_request import BuildRequest, BuildRequestStatus


class TestBuildRequestModel:
    def test_create_build_request(self):
        br = BuildRequest(
            execution_environment_id=uuid.uuid4(),
            analysis_bundle_id=uuid.uuid4(),
            dependency_hash="a" * 64,
            builder_type="python",
        )
        assert br.execution_environment_id is not None
        assert br.analysis_bundle_id is not None
        assert br.dependency_hash == "a" * 64
        assert br.builder_type == "python"

    def test_default_status(self):
        br = BuildRequest(
            execution_environment_id=uuid.uuid4(),
            analysis_bundle_id=uuid.uuid4(),
            dependency_hash="a" * 64,
            builder_type="python",
        )
        assert br.status is None  # server_default, not in-memory

    def test_default_error_message(self):
        br = BuildRequest(
            execution_environment_id=uuid.uuid4(),
            analysis_bundle_id=uuid.uuid4(),
            dependency_hash="a" * 64,
            builder_type="python",
        )
        assert br.error_message is None  # server_default, not in-memory

    def test_can_set_execution_image_id(self):
        img_id = uuid.uuid4()
        br = BuildRequest(
            execution_environment_id=uuid.uuid4(),
            analysis_bundle_id=uuid.uuid4(),
            dependency_hash="a" * 64,
            builder_type="python",
            execution_image_id=img_id,
        )
        assert br.execution_image_id == img_id

    def test_status_enum_values(self):
        assert BuildRequestStatus.PENDING.value == "pending"
        assert BuildRequestStatus.BUILDING.value == "building"
        assert BuildRequestStatus.COMPLETED.value == "completed"
        assert BuildRequestStatus.FAILED.value == "failed"
