from sqlalchemy.orm import Session

from app.models.output import Output, OutputStatus


def approve_output(db: Session, output: Output) -> Output:
    if output.status != OutputStatus.PENDING_REVIEW:
        raise ValueError(f"Cannot approve output in state: {output.status.value}")
    output.status = OutputStatus.APPROVED
    return output


def reject_output(db: Session, output: Output) -> Output:
    if output.status != OutputStatus.PENDING_REVIEW:
        raise ValueError(f"Cannot reject output in state: {output.status.value}")
    output.status = OutputStatus.REJECTED
    return output


def release_output(db: Session, output: Output) -> Output:
    if output.status != OutputStatus.APPROVED:
        raise ValueError(f"Cannot release output in state: {output.status.value}")
    output.status = OutputStatus.RELEASED
    return output
