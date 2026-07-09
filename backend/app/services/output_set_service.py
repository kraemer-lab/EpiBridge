import json
import os
import uuid
import zipfile
from pathlib import Path

from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.execution_request import ExecutionRequest
from app.models.output import Output
from app.models.output_set import OutputSet, OutputSetStatus
from app.services.output_service import OUTPUT_ROOT

RELEASE_ROOT = Path(settings.release_dir)


def ensure_release_root():
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)


def ensure_output_set(db: Session, execution_request_id: uuid.UUID) -> OutputSet:
    existing = (
        db.query(OutputSet)
        .filter(OutputSet.execution_request_id == execution_request_id)
        .first()
    )
    if existing is not None:
        return existing
    output_set = OutputSet(
        execution_request_id=execution_request_id,
    )
    db.add(output_set)
    db.flush()
    return output_set


def register_output(
    db: Session,
    output_set_id: uuid.UUID,
    filename: str,
    size: int,
) -> Output:
    output = Output(
        output_set_id=output_set_id,
        filename=filename,
        size=size,
    )
    db.add(output)
    db.flush()
    return output


def list_output_sets(db: Session) -> list[OutputSet]:
    return db.query(OutputSet).order_by(OutputSet.created_at.desc()).all()


def get_output_set(db: Session, output_set_id: uuid.UUID) -> OutputSet | None:
    return db.query(OutputSet).filter(OutputSet.id == output_set_id).first()


def get_output_set_by_execution(
    db: Session, execution_request_id: uuid.UUID
) -> OutputSet | None:
    return (
        db.query(OutputSet)
        .filter(OutputSet.execution_request_id == execution_request_id)
        .first()
    )


def get_released_output_set(
    db: Session, execution_request_id: uuid.UUID
) -> OutputSet | None:
    return (
        db.query(OutputSet)
        .filter(
            OutputSet.execution_request_id == execution_request_id,
            OutputSet.status == OutputSetStatus.RELEASED,
        )
        .first()
    )


def list_outputs_by_set(db: Session, output_set_id: uuid.UUID) -> list[Output]:
    return (
        db.query(Output)
        .filter(Output.output_set_id == output_set_id)
        .order_by(Output.filename)
        .all()
    )


def create_release_package(output_set: OutputSet) -> Path:
    execution_request: ExecutionRequest = output_set.execution_request
    output_dir = OUTPUT_ROOT / str(execution_request.id)

    ensure_release_root()
    zip_path = RELEASE_ROOT / f"{output_set.id}.zip"

    total_size = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if output_dir.is_dir():
            for root, dirs, files in os.walk(output_dir):
                for fname in files:
                    fpath = Path(root) / fname
                    relative = fpath.relative_to(output_dir)
                    zf.write(str(fpath), str(relative))
                    total_size += fpath.stat().st_size

        metadata = {
            "execution_request_id": str(execution_request.id),
            "execution_request_name": execution_request.name,
            "output_files": [
                {"filename": o.filename, "size": o.size} for o in output_set.outputs
            ],
        }
        zf.writestr("execution_metadata.json", json.dumps(metadata, indent=2))

    output_set.release_package_path = str(zip_path)
    output_set.release_package_size = zip_path.stat().st_size
    return zip_path


def stream_release_package(output_set: OutputSet) -> FileResponse:
    if not output_set.release_package_path:
        raise ValueError("Release package has not been created yet")
    path = Path(output_set.release_package_path)
    return FileResponse(
        path,
        filename=f"outputs-{output_set.execution_request.name}.zip",
        media_type="application/zip",
    )
