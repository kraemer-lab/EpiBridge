from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.analysis_bundle import AnalysisBundle
from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.execution_request import (
    ExecutionRequest,
    ExecutionRequestStatus,
)
from app.models.output import Output
from app.models.project import Project
from app.services.output_service import (
    register_output,
    transition_request_status,
)


@pytest.fixture
def project(db_session, admin_user):
    p = Project(name="Test Project", owner_id=admin_user.id)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def execution_environment(db_session):
    env = ExecutionEnvironment(
        identifier="python-3.13-scientific",
        name="Python 3.13 Scientific",
        runtime="python-3.13",
        description="Test env",
        status="active",
        image_reference="python:3.13-slim",
    )
    db_session.add(env)
    db_session.commit()
    db_session.refresh(env)
    return env


@pytest.fixture
def resource(db_session):
    r = DataResource(
        identifier="test-data",
        name="Test Data",
        alias="test_data",
        provider_type="csv",
        endpoint={"path": "data.csv"},
        version="1.0.0",
        status="active",
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


@pytest.fixture
def bundle(db_session, project, execution_environment, resource):
    b = AnalysisBundle(
        project_id=project.id,
        created_by_id=project.owner_id,
        execution_environment_id=execution_environment.id,
        name="Test Analysis",
        version="1.0.0",
        entrypoint="run.py",
        source_path="examples/analyses/demo",
        outputs=["summary.csv"],
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)
    return b


@pytest.fixture
def pending_request(db_session, project, bundle, admin_user):
    er = ExecutionRequest(
        project_id=project.id,
        analysis_bundle_id=bundle.id,
        name="Test Run",
        timeout_seconds=3600,
        requested_by_id=admin_user.id,
        status=ExecutionRequestStatus.PENDING,
    )
    db_session.add(er)
    db_session.commit()
    db_session.refresh(er)
    return er


class TestStatusTransitions:
    def test_transition_pending_to_running(self, db_session, pending_request):
        result = transition_request_status(
            db_session, pending_request.id, ExecutionRequestStatus.RUNNING
        )
        assert result.status == ExecutionRequestStatus.RUNNING

    def test_transition_to_completed(self, db_session, pending_request):
        result = transition_request_status(
            db_session, pending_request.id, ExecutionRequestStatus.COMPLETED
        )
        assert result.status == ExecutionRequestStatus.COMPLETED

    def test_transition_to_failed(self, db_session, pending_request):
        result = transition_request_status(
            db_session, pending_request.id, ExecutionRequestStatus.FAILED
        )
        assert result.status == ExecutionRequestStatus.FAILED


class TestOutputRegistration:
    def test_register_output(self, db_session, pending_request):
        output = register_output(db_session, pending_request.id, "summary.csv", 1024)
        assert output.execution_request_id == pending_request.id
        assert output.filename == "summary.csv"
        assert output.size == 1024

    def test_list_outputs(self, db_session, pending_request):
        register_output(db_session, pending_request.id, "a.csv", 100)
        register_output(db_session, pending_request.id, "b.csv", 200)

        outputs = (
            db_session.query(Output)
            .filter(Output.execution_request_id == pending_request.id)
            .all()
        )
        assert len(outputs) == 2


@patch("app.execution.docker.docker")
class TestDockerExecutor:
    def test_successful_execution(
        self, mock_docker, db_session, pending_request, bundle
    ):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_container = MagicMock()

        mock_client.images.get.return_value = MagicMock()
        mock_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = 0
        mock_container.logs.side_effect = [
            b"stdout output",
            b"",
        ]

        from app.execution.docker import DockerExecutor

        executor = DockerExecutor(client=mock_client)
        output_dir = Path("/tmp/test-outputs") / str(pending_request.id)
        result = executor.run(
            image="python:3.13-slim",
            analysis_dir=Path("/tmp/fake-analysis"),
            entrypoint="run.py",
            mounts=[("/src/data.csv", "/data/test_data/data.csv", True)],
            output_dir=output_dir,
            timeout=3600,
            env={},
        )

        assert result.exit_code == 0
        assert "stdout output" in result.stdout
        mock_client.containers.create.assert_called_once()
        mock_container.start.assert_called_once()
        mock_container.remove.assert_called_once()

    def test_timeout_execution(self, mock_docker, db_session, pending_request):
        from docker.errors import TimeoutError as DockerTimeoutError

        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_container = MagicMock()

        mock_client.images.get.return_value = MagicMock()
        mock_client.containers.create.return_value = mock_container
        mock_container.wait.side_effect = DockerTimeoutError("timed out")

        from app.execution.docker import DockerExecutor

        executor = DockerExecutor(client=mock_client)
        output_dir = Path("/tmp/test-outputs") / str(pending_request.id)

        with pytest.raises(TimeoutError, match="timed out"):
            executor.run(
                image="python:3.13-slim",
                analysis_dir=Path("/tmp/fake-analysis"),
                entrypoint="run.py",
                mounts=[],
                output_dir=output_dir,
                timeout=1,
                env={},
            )
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()

    def test_failed_execution(self, mock_docker, db_session, pending_request):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_container = MagicMock()

        mock_client.images.get.return_value = MagicMock()
        mock_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = 1
        mock_container.logs.side_effect = [
            b"",
            b"error: division by zero",
        ]

        from app.execution.docker import DockerExecutor

        executor = DockerExecutor(client=mock_client)
        output_dir = Path("/tmp/test-outputs") / str(pending_request.id)
        result = executor.run(
            image="python:3.13-slim",
            analysis_dir=Path("/tmp/fake-analysis"),
            entrypoint="run.py",
            mounts=[],
            output_dir=output_dir,
            timeout=3600,
            env={},
        )

        assert result.exit_code == 1
        assert "division by zero" in result.stderr
