import logging
import os
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.execution.docker import DockerExecutor
from app.models.analysis_bundle import AnalysisBundle
from app.models.execution_environment import ExecutionEnvironment
from app.models.execution_request import (
    ExecutionRequest,
    ExecutionRequestStatus,
)
from app.providers.registry import registry
from app.providers.types import ProviderType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

OUTPUT_ROOT = Path(settings.output_dir)
ANALYSIS_ROOT = (
    Path(settings.analysis_bundle_root)
    if settings.analysis_bundle_root
    else Path("/app/examples/analyses")
)
DATA_ROOT = Path(settings.data_root)
POLL_INTERVAL = 5


def get_pending_requests(db: Session) -> list[ExecutionRequest]:
    return (
        db.query(ExecutionRequest)
        .filter(ExecutionRequest.status == ExecutionRequestStatus.PENDING)
        .order_by(ExecutionRequest.created_at)
        .all()
    )


def transition_to(
    db: Session,
    request: ExecutionRequest,
    status: ExecutionRequestStatus,
    reason: str | None = None,
) -> None:
    request.status = status
    db.commit()
    db.refresh(request)
    msg = f"Request {request.id} → {status.value}"
    if reason:
        msg += f" ({reason})"
    logger.info(msg)


def resolve_data_mounts(
    bundle: AnalysisBundle, db: Session
) -> list[tuple[str, str, bool]]:
    mounts = []
    for dr in bundle.data_resources:
        try:
            provider_type = ProviderType(dr.provider_type)
        except ValueError:
            logger.warning(f"Unknown provider type: {dr.provider_type}")
            continue
        provider = registry.get(provider_type)
        runtime = provider.prepare_runtime(dr.endpoint)
        for mount in runtime.mounts:
            host_source = str(DATA_ROOT / mount.source)
            target = f"/data/{dr.alias}"
            if not os.path.isdir(host_source):
                target = os.path.join(target, os.path.basename(host_source))
            mounts.append((host_source, target, mount.read_only))
    return mounts


def execute_request(db: Session, request: ExecutionRequest) -> None:
    bundle = db.query(AnalysisBundle).get(request.analysis_bundle_id)
    if bundle is None:
        transition_to(db, request, ExecutionRequestStatus.FAILED, "bundle not found")
        return

    env = db.query(ExecutionEnvironment).get(bundle.execution_environment_id)
    if env is None:
        transition_to(
            db, request, ExecutionRequestStatus.FAILED, "environment not found"
        )
        return

    image = env.image_reference
    if not image:
        transition_to(db, request, ExecutionRequestStatus.FAILED, "no image reference")
        return

    analysis_dir = (
        ANALYSIS_ROOT / bundle.source_path if bundle.source_path else ANALYSIS_ROOT
    )
    if not analysis_dir.is_dir():
        transition_to(
            db,
            request,
            ExecutionRequestStatus.FAILED,
            f"analysis directory not found: {analysis_dir}",
        )
        return

    entrypoint = bundle.entrypoint
    output_dir = OUTPUT_ROOT / str(request.id)
    data_mounts = resolve_data_mounts(bundle, db)
    timeout = request.timeout_seconds

    executor = DockerExecutor()

    transition_to(db, request, ExecutionRequestStatus.RUNNING)

    try:
        result = executor.run(
            image=image,
            analysis_dir=analysis_dir,
            entrypoint=entrypoint,
            mounts=data_mounts,
            output_dir=output_dir,
            timeout=timeout,
            env={},
        )
    except TimeoutError:
        transition_to(db, request, ExecutionRequestStatus.FAILED, "timeout")
        return
    except Exception as e:
        transition_to(db, request, ExecutionRequestStatus.FAILED, str(e))
        return

    if result.exit_code != 0:
        logger.error(f"Execution failed (exit {result.exit_code}): {result.stderr}")
        transition_to(
            db,
            request,
            ExecutionRequestStatus.FAILED,
            f"exit code {result.exit_code}",
        )
        return

    if output_dir.is_dir():
        for fname in os.listdir(output_dir):
            fpath = os.path.join(output_dir, fname)
            if os.path.isfile(fpath):
                from app.services.output_service import register_output

                register_output(db, request.id, fname, os.path.getsize(fpath))
                logger.info(
                    f"Registered output: {fname} ({os.path.getsize(fpath)} bytes)"
                )

    transition_to(db, request, ExecutionRequestStatus.COMPLETED)


def main():
    logger.info("Worker starting")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            db = SessionLocal()
            try:
                pending = get_pending_requests(db)
                for request in pending:
                    logger.info(f"Processing request {request.id}: {request.name}")
                    execute_request(db, request)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Worker error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
