import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.output_set import OutputSet, OutputSetStatus
from app.services.output_set_service import create_release_package


def _status_str(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)


def approve_output_set(db: Session, output_set: OutputSet) -> OutputSet:
    if output_set.status != OutputSetStatus.PENDING_REVIEW:
        raise ValueError(
            f"Cannot approve output set in state: {_status_str(output_set.status)}"
        )
    output_set.status = OutputSetStatus.APPROVED
    return output_set


def reject_output_set(
    db: Session,
    output_set: OutputSet,
    *,
    reason: str,
    rejected_by_id: uuid.UUID | None = None,
) -> OutputSet:
    if output_set.status != OutputSetStatus.PENDING_REVIEW:
        raise ValueError(
            f"Cannot reject output set in state: {_status_str(output_set.status)}"
        )
    if not reason or not reason.strip():
        raise ValueError("Rejection reason is required")
    output_set.status = OutputSetStatus.REJECTED
    output_set.rejection_reason = reason.strip()
    output_set.rejected_by_id = rejected_by_id
    output_set.rejected_at = datetime.now(timezone.utc)
    return output_set


def release_output_set(db: Session, output_set: OutputSet) -> OutputSet:
    if output_set.status != OutputSetStatus.APPROVED:
        raise ValueError(
            f"Cannot release output set in state: {_status_str(output_set.status)}"
        )
    create_release_package(output_set)
    output_set.status = OutputSetStatus.RELEASED
    return output_set
