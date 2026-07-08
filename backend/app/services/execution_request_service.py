import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.analysis_bundle import AnalysisBundle, AnalysisBundleStatus
from app.models.audit_event import AuditEventType
from app.models.execution_request import ExecutionRequest
from app.services.analysis_bundle_service import (
    get_environment_runtime,
    get_resource_identifiers,
)
from app.services.audit_service import create_audit_event

MIN_TIMEOUT = 60
MAX_TIMEOUT = 86400


def generate_request_name(bundle: AnalysisBundle) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"{bundle.name} @ {now}"


def validate_timeout(timeout_seconds: int) -> None:
    if not isinstance(timeout_seconds, int) or timeout_seconds < MIN_TIMEOUT:
        raise ValueError(f"timeout_seconds must be at least {MIN_TIMEOUT}")
    if timeout_seconds > MAX_TIMEOUT:
        raise ValueError(f"timeout_seconds must not exceed {MAX_TIMEOUT}")


def create_execution_request(
    db: Session,
    data: dict,
    project_id: uuid.UUID,
    requested_by_id: uuid.UUID,
) -> ExecutionRequest:
    bundle_id = data["analysis_bundle_id"]
    if isinstance(bundle_id, str):
        bundle_id = uuid.UUID(bundle_id)

    bundle = db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
    if bundle is None:
        raise ValueError(f"Analysis bundle not found: {bundle_id}")
    if bundle.project_id != project_id:
        raise ValueError("Analysis bundle does not belong to this project")
    if bundle.status != AnalysisBundleStatus.APPROVED_FOR_EXECUTION:
        raise ValueError(
            "Execution requests require an approved analysis bundle; "
            f"current status: {bundle.status.value}"
        )

    timeout = data.get("timeout_seconds", 3600)
    validate_timeout(timeout)

    name = data.get("name")
    if not name or not name.strip():
        name = generate_request_name(bundle)

    request = ExecutionRequest(
        project_id=project_id,
        analysis_bundle_id=bundle.id,
        name=name,
        timeout_seconds=timeout,
        parameter_overrides=data.get("parameter_overrides", {}),
        requested_by_id=requested_by_id,
    )
    db.add(request)
    db.flush()  # Flush so request.id is available for the audit event before commit
    create_audit_event(
        db,
        event_type=AuditEventType.EXECUTION_REQUESTED,
        actor_id=requested_by_id,
        project_id=project_id,
        resource_type="execution_request",
        resource_id=request.id,
        metadata={"bundle_name": bundle.name, "timeout_seconds": timeout},
    )
    db.commit()
    db.refresh(request)
    return request


def list_execution_requests(
    db: Session, project_id: uuid.UUID | None = None
) -> list[ExecutionRequest]:
    query = db.query(ExecutionRequest).order_by(ExecutionRequest.created_at.desc())
    if project_id is not None:
        query = query.filter(ExecutionRequest.project_id == project_id)
    return query.all()


def get_execution_request(
    db: Session, request_id: uuid.UUID
) -> ExecutionRequest | None:
    return db.query(ExecutionRequest).filter(ExecutionRequest.id == request_id).first()


def request_to_read(request: ExecutionRequest) -> dict:
    bundle = request.analysis_bundle
    return {
        "id": request.id,
        "project_id": request.project_id,
        "analysis_bundle_id": request.analysis_bundle_id,
        "name": request.name,
        "timeout_seconds": request.timeout_seconds,
        "parameter_overrides": request.parameter_overrides,
        "status": request.status,
        "log": request.log,
        "requested_by_id": request.requested_by_id,
        "analysis_name": bundle.name if bundle else "",
        "runtime": get_environment_runtime(bundle) if bundle else "",
        "resource_identifiers": (get_resource_identifiers(bundle) if bundle else []),
        "parameters": bundle.parameters if bundle else {},
        "created_at": request.created_at,
        "updated_at": request.updated_at,
    }
