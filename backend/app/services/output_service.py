import os
import uuid
from pathlib import Path

from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.execution_request import (
    ExecutionRequest,
    ExecutionRequestStatus,
)
from app.models.output import Output

OUTPUT_ROOT = Path(os.environ.get("OUTPUT_DIR", "/tmp/epibridge-outputs"))


def ensure_output_root():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def register_output(
    db: Session,
    execution_request_id: uuid.UUID,
    filename: str,
    size: int,
) -> Output:
    output = Output(
        execution_request_id=execution_request_id,
        filename=filename,
        size=size,
    )
    db.add(output)
    db.commit()
    db.refresh(output)
    return output


def list_outputs(db: Session, execution_request_id: uuid.UUID) -> list[Output]:
    return (
        db.query(Output)
        .filter(Output.execution_request_id == execution_request_id)
        .order_by(Output.created_at)
        .all()
    )


def get_output(db: Session, output_id: uuid.UUID) -> Output | None:
    return db.query(Output).filter(Output.id == output_id).first()


def transition_request_status(
    db: Session,
    request_id: uuid.UUID,
    status: ExecutionRequestStatus,
    reason: str | None = None,
) -> ExecutionRequest:
    request = (
        db.query(ExecutionRequest).filter(ExecutionRequest.id == request_id).first()
    )
    if request is None:
        raise ValueError(f"Execution request not found: {request_id}")
    request.status = status
    db.commit()
    db.refresh(request)
    return request


def get_output_path(execution_request_id: uuid.UUID, filename: str) -> Path:
    return OUTPUT_ROOT / str(execution_request_id) / filename


def stream_output(execution_request_id: uuid.UUID, filename: str) -> FileResponse:
    path = get_output_path(execution_request_id, filename)
    return FileResponse(path, filename=filename)
