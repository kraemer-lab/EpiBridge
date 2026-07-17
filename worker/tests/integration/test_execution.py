"""Integration tests for worker execution orchestration.

Tests execute_request and resolve_mounts against a real database
with Docker SDK mocked only.  Exercises state transitions, audit
events, mount resolution, and cancellation.
"""

from unittest.mock import MagicMock, patch

import pytest

from worker.main import execute_request, resolve_mounts

from app.execution.base import CancelledError
from app.models.analysis_bundle import (
    AnalysisBundle,
    AnalysisBundleBuildStatus,
    AnalysisBundleStatus,
)
from app.models.audit_event import AuditEvent, AuditEventType, WORKER_USER_ID
from app.models.execution_request import ExecutionRequest, ExecutionRequestStatus
from app.models.output_set import OutputSet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bundle(
    db_session,
    project,
    execution_environment,
    execution_image,
    resource,
    *,
    entrypoint="run.py",
    interpreter="python",
    source_path="",
    arguments="",
    status=AnalysisBundleStatus.APPROVED_FOR_EXECUTION,
    build_status=AnalysisBundleBuildStatus.ENVIRONMENT_READY,
):
    b = AnalysisBundle(
        project_id=project.id,
        created_by_id=project.owner_id,
        execution_environment_id=execution_environment.id,
        execution_image_id=execution_image.id,
        name="Test Analysis",
        version="1.0.0",
        entrypoint=entrypoint,
        interpreter=interpreter,
        source_path=source_path,
        arguments=arguments,
        status=status,
        build_status=build_status,
    )
    b.data_resources = [resource]
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)
    return b


def _make_execution_request(db_session, project, bundle, user):
    er = ExecutionRequest(
        project_id=project.id,
        analysis_bundle_id=bundle.id,
        name="Test Execution",
        timeout_seconds=3600,
        requested_by_id=user.id,
        status=ExecutionRequestStatus.PENDING,
    )
    db_session.add(er)
    db_session.commit()
    db_session.refresh(er)
    return er


# ---------------------------------------------------------------------------
# Successful execution
# ---------------------------------------------------------------------------


@patch("worker.main.DockerExecutor")
def test_execute_request_successful(
    mock_docker_cls,
    db_session,
    project,
    execution_environment,
    execution_image,
    resource,
    worker_test_user,
    analysis_dir,
    monkeypatch,
):
    """A valid PENDING request transitions to COMPLETED with audit events."""
    monkeypatch.setattr("worker.main.ANALYSIS_ROOT", analysis_dir.parent)

    bundle = _make_bundle(
        db_session, project, execution_environment, execution_image, resource,
        source_path=analysis_dir.name,
    )
    request = _make_execution_request(db_session, project, bundle, worker_test_user)

    mock_instance = MagicMock()
    mock_instance.run.return_value = MagicMock(exit_code=0, stdout="", stderr="")
    mock_docker_cls.return_value = mock_instance

    execute_request(db_session, request)
    db_session.refresh(request)

    assert request.status == ExecutionRequestStatus.COMPLETED

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.resource_id == request.id)
        .order_by(AuditEvent.occurred_at)
        .all()
    )
    event_types = [e.event_type for e in events]
    assert AuditEventType.EXECUTION_STARTED in event_types
    assert AuditEventType.EXECUTION_COMPLETED in event_types

    output_set = (
        db_session.query(OutputSet)
        .filter(OutputSet.execution_request_id == request.id)
        .first()
    )
    assert output_set is not None

    _call_kwargs = mock_instance.run.call_args.kwargs
    assert _call_kwargs.get("network_enabled") is False


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


@patch("worker.main.DockerExecutor")
def test_execute_request_cancelled(
    mock_docker_cls,
    db_session,
    project,
    execution_environment,
    execution_image,
    resource,
    worker_test_user,
    analysis_dir,
    monkeypatch,
):
    """A running execution that receives cancellation transitions to CANCELLED."""
    monkeypatch.setattr("worker.main.ANALYSIS_ROOT", analysis_dir.parent)

    bundle = _make_bundle(
        db_session, project, execution_environment, execution_image, resource,
        source_path=analysis_dir.name,
    )
    request = _make_execution_request(db_session, project, bundle, worker_test_user)

    request.cancelled_by_id = worker_test_user.id
    request.cancellation_reason = "Operator requested stop"
    db_session.commit()

    mock_instance = MagicMock()
    mock_instance.run.side_effect = CancelledError()
    mock_docker_cls.return_value = mock_instance

    execute_request(db_session, request)
    db_session.refresh(request)

    assert request.status == ExecutionRequestStatus.CANCELLED
    assert request.cancelled_at is not None
    assert request.cancellation_reason == "Operator requested stop"

    cancelled_event = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.resource_id == request.id,
            AuditEvent.event_type == AuditEventType.EXECUTION_CANCELLED,
        )
        .first()
    )
    assert cancelled_event is not None
    assert cancelled_event.actor_id == worker_test_user.id


# ---------------------------------------------------------------------------
# Pre-flight validation failures
# ---------------------------------------------------------------------------


def _scenario_no_env(bundle):
    bundle.execution_environment_id = None
    return bundle


def _scenario_no_entrypoint(bundle):
    bundle.entrypoint = ""
    return bundle


def _scenario_bad_interpreter(bundle):
    bundle.interpreter = "nonexistent"
    return bundle


@pytest.mark.parametrize(
    "scenario,setup_fn,expected_fragment",
    [
        ("no-environment", _scenario_no_env, "no execution environment configured"),
        ("no-entrypoint", _scenario_no_entrypoint, "no entrypoint configured"),
        ("bad-interpreter", _scenario_bad_interpreter, "unknown interpreter"),
    ],
    ids=[
        "no-environment-configured",
        "no-entrypoint",
        "unknown-interpreter",
    ],
)
@patch("worker.main.DockerExecutor")
def test_execute_request_validation_failure(
    mock_docker_cls,
    scenario,
    setup_fn,
    expected_fragment,
    db_session,
    project,
    execution_environment,
    execution_image,
    resource,
    worker_test_user,
    analysis_dir,
    monkeypatch,
):
    """Validation checks on bundle fields correctly transition to FAILED."""
    monkeypatch.setattr("worker.main.ANALYSIS_ROOT", analysis_dir.parent)
    bundle = _make_bundle(
        db_session, project, execution_environment, execution_image, resource,
        source_path=analysis_dir.name,
    )
    setup_fn(bundle)
    db_session.commit()
    db_session.refresh(bundle)

    request = _make_execution_request(db_session, project, bundle, worker_test_user)

    execute_request(db_session, request)
    db_session.refresh(request)

    assert request.status == ExecutionRequestStatus.FAILED
    failed_event = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.resource_id == request.id,
            AuditEvent.event_type == AuditEventType.EXECUTION_FAILED,
        )
        .first()
    )
    assert failed_event is not None
    assert failed_event.actor_id == WORKER_USER_ID
    assert expected_fragment in (request.log or "")
    mock_docker_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Mount resolution
# ---------------------------------------------------------------------------


def test_resolve_mounts_valid(
    db_session, project, execution_environment, execution_image, resource,
):
    """Valid resources produce correctly structured mounts."""
    bundle = _make_bundle(
        db_session, project, execution_environment, execution_image, resource,
    )
    mounts = resolve_mounts(bundle, db_session)
    assert len(mounts) > 0
    for _source, target, read_only in mounts:
        assert target.startswith("/data/")
        assert read_only is True


def test_resolve_mounts_representative(
    db_session, project, execution_environment, execution_image,
    tmp_path, monkeypatch,
):
    """Representative data mounts resolve to the representative subdirectory."""
    manifest_root = tmp_path / "resources"
    manifest_root.mkdir()

    res_dir = manifest_root / "test-rep" / "representative"
    res_dir.mkdir(parents=True)
    (res_dir / "sample.csv").write_text("a,b,c\n1,2,3\n")

    from app.models.data_resource import DataResource

    rep_resource = DataResource(
        identifier="test-rep",
        name="Test Rep",
        alias="test_rep",
        provider_type="csv",
        endpoint={"path": "data.csv"},
        version="1.0.0",
        status="active",
    )
    db_session.add(rep_resource)
    db_session.commit()
    db_session.refresh(rep_resource)

    bundle = _make_bundle(
        db_session, project, execution_environment, execution_image, rep_resource,
    )
    bundle.data_resources = [rep_resource]
    db_session.commit()

    monkeypatch.setattr("worker.main.settings.resource_manifest_dir", str(manifest_root))

    mounts = resolve_mounts(bundle, db_session, representative=True)
    assert len(mounts) > 0
    source, _target, _read_only = mounts[0]
    assert "representative" in source
