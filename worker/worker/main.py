import logging
import os
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.builders.registry import registry as builder_registry
from app.core.config import settings
from app.db.session import SessionLocal
from app.execution.docker import DockerExecutor
from app.models.analysis_bundle import AnalysisBundle
from app.models.build_request import BuildRequest, BuildRequestStatus
from app.models.execution_environment import ExecutionEnvironment
from app.models.execution_image import ExecutionImage
from app.models.execution_request import (
    ExecutionRequest,
    ExecutionRequestStatus,
)
from app.providers.registry import registry
from app.providers.types import ProviderType
from app.services.bundle_store import get_bundle_store

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


def get_pending_builds(db: Session) -> list[BuildRequest]:
    return (
        db.query(BuildRequest)
        .filter(BuildRequest.status == BuildRequestStatus.PENDING)
        .order_by(BuildRequest.created_at)
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


def build_transition_to(
    db: Session,
    build: BuildRequest,
    status: BuildRequestStatus,
    reason: str | None = None,
) -> None:
    build.status = status
    if reason:
        build.error_message = reason
    db.commit()
    db.refresh(build)
    msg = f"Build {build.id} → {status.value}"
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


def process_build(db: Session, build: BuildRequest) -> None:
    bundle = db.query(AnalysisBundle).get(build.analysis_bundle_id)
    if bundle is None:
        build_transition_to(db, build, BuildRequestStatus.FAILED, "bundle not found")
        return

    env = db.query(ExecutionEnvironment).get(build.execution_environment_id)
    if env is None:
        build_transition_to(
            db, build, BuildRequestStatus.FAILED, "environment not found"
        )
        return

    builder = builder_registry.get_for_runtime(env.runtime)
    if builder is None:
        build_transition_to(
            db, build, BuildRequestStatus.FAILED, "no builder for runtime"
        )
        return

    bundle_path = get_bundle_store().get_path(bundle.id)
    if not bundle_path.is_dir():
        build_transition_to(
            db, build, BuildRequestStatus.FAILED, "bundle directory not found"
        )
        return

    tag = f"{settings.image_registry_prefix}/{env.runtime}:{build.dependency_hash[:16]}"

    existing = (
        db.query(ExecutionImage)
        .filter(
            ExecutionImage.execution_environment_id == build.execution_environment_id,
            ExecutionImage.dependency_hash == build.dependency_hash,
        )
        .first()
    )
    if existing is not None:
        bundle.execution_image_id = existing.id
        bundle.build_status = "environment_ready"
        build.execution_image_id = existing.id
        build_transition_to(db, build, BuildRequestStatus.COMPLETED, "cache hit (race)")
        return

    bundle.build_status = "environment_building"
    build_transition_to(db, build, BuildRequestStatus.BUILDING)

    result = builder.build(
        bundle_path=bundle_path,
        base_image=env.image_reference,
        image_tag=tag,
    )

    if not result.success:
        bundle.build_status = "environment_build_failed"
        bundle.build_error = result.build_log
        db.commit()
        build_transition_to(db, build, BuildRequestStatus.FAILED, result.build_log)
        return

    cached = (
        db.query(ExecutionImage)
        .filter(
            ExecutionImage.execution_environment_id == build.execution_environment_id,
            ExecutionImage.dependency_hash == build.dependency_hash,
        )
        .first()
    )
    if cached is None:
        cached = ExecutionImage(
            execution_environment_id=build.execution_environment_id,
            dependency_hash=build.dependency_hash,
            image_reference=result.image_reference,
            builder_type=build.builder_type,
            build_log=result.build_log,
        )
        db.add(cached)
        db.flush()
    else:
        cached.image_reference = result.image_reference
        cached.builder_type = build.builder_type
        cached.build_log = result.build_log

    bundle.execution_image_id = cached.id
    bundle.build_status = "environment_ready"
    build.execution_image_id = cached.id
    build_transition_to(db, build, BuildRequestStatus.COMPLETED)


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

    image = (
        bundle.execution_image.image_reference
        if bundle.execution_image
        else env.image_reference
    )
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

    mount_remap = {}
    if settings.host_data_root:
        mount_remap[settings.data_root] = settings.host_data_root
    executor = DockerExecutor(mount_remap=mount_remap)

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

    # The filename field represents the relative path within the execution
    # output directory (e.g. "summary.csv", "figures/plot.png").
    # This preserves structured output hierarchies without flattening.
    if output_dir.is_dir():
        from app.services.output_service import register_output

        for root, dirs, files in os.walk(output_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                relative = os.path.relpath(fpath, output_dir)
                register_output(db, request.id, relative, os.path.getsize(fpath))
                logger.info(
                    f"Registered output: {relative} ({os.path.getsize(fpath)} bytes)"
                )

    transition_to(db, request, ExecutionRequestStatus.COMPLETED)


def main():
    logger.info("Worker starting")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            db = SessionLocal()
            try:
                pending_builds = get_pending_builds(db)
                for build in pending_builds:
                    logger.info(f"Processing build {build.id}")
                    process_build(db, build)

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
