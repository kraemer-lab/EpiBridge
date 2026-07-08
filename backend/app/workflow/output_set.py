from sqlalchemy.orm import Session

from app.models.output_set import OutputSet, OutputSetStatus
from app.services.output_set_service import create_release_package


def approve_output_set(db: Session, output_set: OutputSet) -> OutputSet:
    if output_set.status != OutputSetStatus.PENDING_REVIEW:
        raise ValueError(
            f"Cannot approve output set in state: {output_set.status.value}"
        )
    output_set.status = OutputSetStatus.APPROVED
    return output_set


def reject_output_set(db: Session, output_set: OutputSet) -> OutputSet:
    if output_set.status != OutputSetStatus.PENDING_REVIEW:
        raise ValueError(
            f"Cannot reject output set in state: {output_set.status.value}"
        )
    output_set.status = OutputSetStatus.REJECTED
    return output_set


def release_output_set(db: Session, output_set: OutputSet) -> OutputSet:
    if output_set.status != OutputSetStatus.APPROVED:
        raise ValueError(
            f"Cannot release output set in state: {output_set.status.value}"
        )
    create_release_package(output_set)
    output_set.status = OutputSetStatus.RELEASED
    return output_set
