import uuid
from pathlib import Path

from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.execution_request import ExecutionRequest, ExecutionRequestStatus
from app.models.output import Output

OUTPUT_ROOT = Path(settings.output_dir)


def ensure_output_root():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def get_output(db: Session, output_id: uuid.UUID) -> Output | None:
    return db.query(Output).filter(Output.id == output_id).first()


def get_output_path(execution_request_id: uuid.UUID, filename: str) -> Path:
    return OUTPUT_ROOT / str(execution_request_id) / filename


def stream_output(execution_request_id: uuid.UUID, filename: str) -> FileResponse:
    path = get_output_path(execution_request_id, filename)
    return FileResponse(path, filename=filename)


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
