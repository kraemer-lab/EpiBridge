import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.analysis_bundle import AnalysisBundle
from app.models.validation_request import ValidationRequest
from app.services.bundle_store import get_bundle_store

MIN_TIMEOUT = 60
MAX_TIMEOUT = 86400


def generate_validation_name(bundle: AnalysisBundle) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"Validate: {bundle.name} @ {now}"


def validate_timeout(timeout_seconds: int) -> None:
    if not isinstance(timeout_seconds, int) or timeout_seconds < MIN_TIMEOUT:
        raise ValueError(f"timeout_seconds must be at least {MIN_TIMEOUT}")
    if timeout_seconds > MAX_TIMEOUT:
        raise ValueError(f"timeout_seconds must not exceed {MAX_TIMEOUT}")


def compute_execution_fingerprint(bundle: AnalysisBundle) -> str:
    """Deterministic hash covering everything that affects execution.

    Two bundles with the same fingerprint will execute identically.
    """
    store = get_bundle_store()
    file_hash = store.get_content_hash(bundle.id)

    config = json.dumps(
        {
            "execution_environment_id": str(bundle.execution_environment_id or ""),
            "entrypoint": bundle.entrypoint or "",
            "interpreter": bundle.interpreter or "python",
            "arguments": bundle.arguments or "",
            "resource_identifiers": sorted(
                dr.identifier for dr in bundle.data_resources
            ),
            "build_strategy": bundle.build_strategy or "institutional",
        },
        sort_keys=True,
    )

    hasher = hashlib.sha256()
    hasher.update(file_hash.encode())
    hasher.update(config.encode())
    return hasher.hexdigest()


def create_validation_request(
    db: Session,
    data: dict,
    project_id: uuid.UUID,
    requested_by_id: uuid.UUID,
) -> ValidationRequest:
    bundle_id = data["analysis_bundle_id"]
    if isinstance(bundle_id, str):
        bundle_id = uuid.UUID(bundle_id)

    bundle = db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
    if bundle is None:
        raise ValueError(f"Analysis bundle not found: {bundle_id}")
    if bundle.project_id != project_id:
        raise ValueError("Analysis bundle does not belong to this project")

    timeout = data.get("timeout_seconds", 3600)
    validate_timeout(timeout)

    name = data.get("name")
    if not name or not name.strip():
        name = generate_validation_name(bundle)

    fingerprint = compute_execution_fingerprint(bundle)

    request = ValidationRequest(
        project_id=project_id,
        analysis_bundle_id=bundle.id,
        name=name,
        timeout_seconds=timeout,
        parameter_overrides=data.get("parameter_overrides", {}),
        bundle_content_hash=fingerprint,
        requested_by_id=requested_by_id,
    )
    db.add(request)
    db.flush()
    db.commit()
    db.refresh(request)
    return request


def list_validation_requests(
    db: Session,
    project_id: uuid.UUID | None = None,
    bundle_id: uuid.UUID | None = None,
) -> list[ValidationRequest]:
    query = db.query(ValidationRequest).order_by(ValidationRequest.created_at.desc())
    if project_id is not None:
        query = query.filter(ValidationRequest.project_id == project_id)
    if bundle_id is not None:
        query = query.filter(ValidationRequest.analysis_bundle_id == bundle_id)
    return query.all()


def get_validation_request(
    db: Session, request_id: uuid.UUID
) -> ValidationRequest | None:
    return (
        db.query(ValidationRequest).filter(ValidationRequest.id == request_id).first()
    )


def request_to_read(request: ValidationRequest) -> dict:
    return {
        "id": request.id,
        "project_id": request.project_id,
        "analysis_bundle_id": request.analysis_bundle_id,
        "name": request.name,
        "timeout_seconds": request.timeout_seconds,
        "parameter_overrides": request.parameter_overrides,
        "status": request.status,
        "log": request.log,
        "output_files": request.output_files,
        "bundle_content_hash": request.bundle_content_hash,
        "requested_by_id": request.requested_by_id,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
    }


def get_bundle_validation_status(db: Session, bundle_id: uuid.UUID) -> dict:
    bundle = db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
    if bundle is None:
        return {
            "last_validation_id": None,
            "last_validation_hash": "",
            "current_bundle_hash": "",
            "is_validated": False,
            "has_changed": False,
        }
    current_fingerprint = compute_execution_fingerprint(bundle)
    last = (
        db.query(ValidationRequest)
        .filter(ValidationRequest.analysis_bundle_id == bundle_id)
        .order_by(ValidationRequest.created_at.desc())
        .first()
    )
    if last is None:
        return {
            "last_validation_id": None,
            "last_validation_hash": "",
            "current_bundle_hash": current_fingerprint,
            "is_validated": False,
            "has_changed": False,
        }
    return {
        "last_validation_id": str(last.id),
        "last_validation_hash": last.bundle_content_hash,
        "current_bundle_hash": current_fingerprint,
        "is_validated": (
            last.status.value == "completed"
            and last.bundle_content_hash == current_fingerprint
        ),
        "has_changed": (last.bundle_content_hash != current_fingerprint),
    }
