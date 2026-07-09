import logging
import os
import shlex
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.builders.registry import registry as builder_registry
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.execution.docker import DockerExecutor
from app.models.analysis_bundle import AnalysisBundle, AnalysisBundleBuildStatus, BuildStrategy
from app.models.audit_event import WORKER_USER_ID, AuditEventType
from app.schemas.analysis_bundle import Interpreter
from app.models.build_request import BuildRequest, BuildRequestStatus
from app.models.execution_environment import ExecutionEnvironment
from app.models.execution_image import ExecutionImage
from app.models.execution_request import (
    ExecutionRequest,
    ExecutionRequestStatus,
)
from app.providers.registry import registry
from app.providers.types import ProviderType
from app.services.audit_service import create_audit_event
from app.services.bundle_store import get_bundle_store
from app.services.output_set_service import (
    ensure_output_set,
    register_output as register_set_output,
)

configure_logging(settings.log_level)
logger = logging.getLogger("worker")

OUTPUT_ROOT = Path(settings.output_dir)
ANALYSIS_ROOT = (
    Path(settings.analysis_bundle_root)
    if settings.analysis_bundle_root
    else Path("/app/examples/analyses")
)
DATA_ROOT = Path(settings.data_root)
POLL_INTERVAL = 5
BACKOFF_MAX = 60

_shutdown_requested = False


def _handle_signal(signum, frame):
    global _shutdown_requested
    logger.info("Received signal %d, shutting down after current iteration", signum)
    _shutdown_requested = True


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


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
            logger.warning("Unknown provider type: %s", dr.provider_type)
            continue
        provider = registry.get(provider_type)
        runtime = provider.prepare_runtime(dr.endpoint)
        for mount in runtime.mounts:
            mount_path = Path(mount.source).resolve()
            data_root_resolved = DATA_ROOT.resolve()
            if not str(mount_path).startswith(str(data_root_resolved)):
                raise ValueError(
                    f"Mount source {mount.source} escapes data root {DATA_ROOT}"
                )
            host_source = str(mount_path)
            target = f"/data/{dr.alias}"
            if not mount_path.is_dir():
                target = os.path.join(target, mount_path.name)
            mounts.append((host_source, target, mount.read_only))
    return mounts


def process_build(db: Session, build: BuildRequest) -> None:
    # NOTE: bundle.build_status mirrors the BuildRequest lifecycle.
    # Environment preparation is owned by BuildRequest, not AnalysisBundle.
    # The build_status field is retained for backwards compatibility and
    # is expected to be removed in a future governance refactor.
    ts = _timestamp()
    bundle = db.query(AnalysisBundle).get(build.analysis_bundle_id)
    if bundle is None:
        build.log = f"[{ts}] BUILD FAILED: bundle not found (id={build.analysis_bundle_id})"
        build_transition_to(db, build, BuildRequestStatus.FAILED, "bundle not found")
        return

    env = db.query(ExecutionEnvironment).get(build.execution_environment_id)
    if env is None:
        build.log = (
            f"[{ts}] BUILD FAILED: execution environment not found "
            f"(id={build.execution_environment_id})"
        )
        build_transition_to(
            db, build, BuildRequestStatus.FAILED, "environment not found"
        )
        return

    builder = builder_registry.get_for_runtime(env.runtime)
    if builder is None:
        build.log = (
            f"[{ts}] BUILD FAILED: no builder registered for runtime "
            f"'{env.runtime}'"
        )
        build_transition_to(
            db, build, BuildRequestStatus.FAILED, "no builder for runtime"
        )
        return

    bundle_path = get_bundle_store().get_path(bundle.id)
    if not bundle_path.is_dir():
        build.log = (
            f"[{ts}] BUILD FAILED: bundle directory not found "
            f"(bundle_id={bundle.id})"
        )
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
        log = (
            f"[{ts}] BUILD CACHE HIT\n"
            f"[build] builder={build.builder_type} runtime={env.runtime}\n"
            f"[build] hash={build.dependency_hash}\n"
            f"[build] existing image: {existing.image_reference}\n"
            f"[build] Using cached execution image (id={existing.id})"
        )
        build.log = log
        bundle.execution_image_id = existing.id
        bundle.build_status = AnalysisBundleBuildStatus.ENVIRONMENT_READY
        build.execution_image_id = existing.id
        build_transition_to(db, build, BuildRequestStatus.COMPLETED, "cache hit (race)")
        return

    build_start = _timestamp()
    preamble = (
        f"[{build_start}] BUILD STARTED\n"
        f"[build] builder={build.builder_type} runtime={env.runtime}\n"
        f"[build] hash={build.dependency_hash}\n"
        f"[build] base_image={env.image_reference}\n"
        f"[build] image_tag={tag}\n"
        f"[build] bundle_path={bundle_path}"
    )

    bundle.build_status = AnalysisBundleBuildStatus.ENVIRONMENT_BUILDING
    build_transition_to(db, build, BuildRequestStatus.BUILDING)

    if bundle.build_strategy == BuildStrategy.CUSTOM.value:
        dockerfile = bundle_path / "build" / "Dockerfile"
    else:
        dockerfile = builder.get_template_dockerfile()

    try:
        result = builder.build(
            bundle_path=bundle_path,
            dockerfile=dockerfile,
            base_image=env.image_reference,
            image_tag=tag,
        )
    except Exception as e:
        build_end = _timestamp()
        build.log = (
            f"{preamble}\n"
            f"[{build_end}] BUILD FAILED (exception): {e}"
        )
        bundle.build_status = AnalysisBundleBuildStatus.ENVIRONMENT_BUILD_FAILED
        bundle.build_error = str(e)
        db.commit()
        build_transition_to(db, build, BuildRequestStatus.FAILED, str(e))
        return

    build_end = _timestamp()
    if not result.success:
        build.log = (
            f"{preamble}\n"
            f"[{build_end}] BUILD FAILED (duration={result.duration_seconds:.1f}s)\n"
            f"{result.build_log}"
        )
        bundle.build_status = AnalysisBundleBuildStatus.ENVIRONMENT_BUILD_FAILED
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

    ref = result.image_reference
    build.log = (
        f"{preamble}\n"
        f"[{build_end}] BUILD COMPLETED (duration={result.duration_seconds:.1f}s)\n"
        f"{result.build_log}\n"
        f"[build] Result image: {ref}"
    )
    bundle.execution_image_id = cached.id
    bundle.build_status = AnalysisBundleBuildStatus.ENVIRONMENT_READY
    build.execution_image_id = cached.id
    build_transition_to(db, build, BuildRequestStatus.COMPLETED)


def _emit_execution_event(
    db: Session,
    event_type: AuditEventType,
    request: ExecutionRequest,
    metadata: dict | None = None,
) -> None:
    create_audit_event(
        db,
        event_type=event_type,
        actor_id=WORKER_USER_ID,
        project_id=request.project_id,
        resource_type="execution_request",
        resource_id=request.id,
        metadata=metadata or {},
    )


def execute_request(db: Session, request: ExecutionRequest) -> None:
    ts = _timestamp()
    bundle = db.query(AnalysisBundle).get(request.analysis_bundle_id)
    if bundle is None:
        request.log = f"[{ts}] EXECUTION FAILED: bundle not found (id={request.analysis_bundle_id})"
        db.commit()
        _emit_execution_event(db, AuditEventType.EXECUTION_FAILED, request, {"failure_reason": "bundle not found"})
        transition_to(db, request, ExecutionRequestStatus.FAILED, "bundle not found")
        return

    env = db.query(ExecutionEnvironment).get(bundle.execution_environment_id)
    if env is None:
        request.log = f"[{ts}] EXECUTION FAILED: environment not found"
        db.commit()
        _emit_execution_event(db, AuditEventType.EXECUTION_FAILED, request, {"failure_reason": "environment not found"})
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
        request.log = f"[{ts}] EXECUTION FAILED: no image reference"
        db.commit()
        _emit_execution_event(db, AuditEventType.EXECUTION_FAILED, request, {"failure_reason": "no image reference"})
        transition_to(db, request, ExecutionRequestStatus.FAILED, "no image reference")
        return

    analysis_dir = (
        ANALYSIS_ROOT / bundle.source_path if bundle.source_path else ANALYSIS_ROOT
    )
    if not analysis_dir.is_dir():
        request.log = (
            f"[{ts}] EXECUTION FAILED: analysis directory not found: {analysis_dir}"
        )
        db.commit()
        _emit_execution_event(db, AuditEventType.EXECUTION_FAILED, request, {"failure_reason": "analysis directory not found"})
        transition_to(
            db,
            request,
            ExecutionRequestStatus.FAILED,
            f"analysis directory not found: {analysis_dir}",
        )
        return

    entrypoint = bundle.entrypoint
    interpreter_str = bundle.interpreter or "python"
    try:
        interpreter = Interpreter(interpreter_str)
    except ValueError:
        request.log = (
            f"[{_timestamp()}] EXECUTION FAILED: unknown interpreter '{interpreter_str}'"
        )
        db.commit()
        _emit_execution_event(db, AuditEventType.EXECUTION_FAILED, request, {"failure_reason": f"unknown interpreter '{interpreter_str}'"})
        transition_to(db, request, ExecutionRequestStatus.FAILED, f"unknown interpreter '{interpreter_str}'")
        return
    extra = shlex.split(bundle.arguments) if bundle.arguments else []
    command = [interpreter.executable, f"/analysis/{entrypoint}"] + extra
    output_dir = OUTPUT_ROOT / str(request.id)
    data_mounts = resolve_data_mounts(bundle, db)
    timeout = request.timeout_seconds

    mount_remap = {}
    if settings.host_data_root:
        mount_remap[settings.data_root] = settings.host_data_root
    executor = DockerExecutor(mount_remap=mount_remap)

    exec_start = _timestamp()
    preamble = (
        f"[{exec_start}] EXECUTION STARTED\n"
        f"[exec] bundle={bundle.name} interpreter={interpreter_str} entrypoint={entrypoint}\n"
        f"[exec] command={' '.join(command)}\n"
        f"[exec] image={image}\n"
        f"[exec] timeout={timeout}s"
    )
    request.log = preamble
    db.commit()

    _emit_execution_event(db, AuditEventType.EXECUTION_STARTED, request)
    transition_to(db, request, ExecutionRequestStatus.RUNNING)

    try:
        result = executor.run(
            image=image,
            analysis_dir=analysis_dir,
            command=command,
            mounts=data_mounts,
            output_dir=output_dir,
            timeout=timeout,
            env={},
        )
    except TimeoutError:
        exec_end = _timestamp()
        request.log = (
            f"{preamble}\n"
            f"[{exec_end}] EXECUTION TIMED OUT after {timeout}s\n"
            f"[exec] No output captured — container was terminated"
        )
        db.commit()
        _emit_execution_event(db, AuditEventType.EXECUTION_FAILED, request, {"failure_reason": "timeout"})
        transition_to(db, request, ExecutionRequestStatus.FAILED, "timeout")
        return
    except Exception as e:
        exec_end = _timestamp()
        request.log = (
            f"{preamble}\n"
            f"[{exec_end}] EXECUTION FAILED: {e}"
        )
        db.commit()
        _emit_execution_event(db, AuditEventType.EXECUTION_FAILED, request, {"failure_reason": str(e)})
        transition_to(db, request, ExecutionRequestStatus.FAILED, str(e))
        return

    exec_end = _timestamp()
    log_body = ""
    if result.stdout:
        log_body += f"[exec] stdout:\n{result.stdout.rstrip()}\n"
    if result.stderr:
        log_body += f"[exec] stderr:\n{result.stderr.rstrip()}\n"

    if result.exit_code != 0:
        logger.error("Execution failed (exit %s): %s", result.exit_code, result.stderr or "")
        request.log = (
            f"{preamble}\n"
            f"[{exec_end}] EXECUTION FAILED (exit code {result.exit_code})\n"
            f"{log_body}"
        )
        db.commit()
        _emit_execution_event(db, AuditEventType.EXECUTION_FAILED, request, {"failure_reason": f"exit code {result.exit_code}"})
        transition_to(
            db,
            request,
            ExecutionRequestStatus.FAILED,
            f"exit code {result.exit_code}",
        )
        return

    output_set = ensure_output_set(db, request.id)
    output_count = 0
    if output_dir.is_dir():
        for root, dirs, files in os.walk(output_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                relative = os.path.relpath(fpath, output_dir)
                register_set_output(db, output_set.id, relative, os.path.getsize(fpath))
                output_count += 1
                logger.info(
                    "Registered output: %s (%s bytes)", relative, os.path.getsize(fpath)
                )

    request.log = (
        f"{preamble}\n"
        f"[{exec_end}] EXECUTION COMPLETED (exit code 0)\n"
        f"{log_body}"
        f"[exec] Output files: {output_count}"
    )
    create_audit_event(
        db,
        event_type=AuditEventType.OUTPUT_SET_CREATED,
        actor_id=WORKER_USER_ID,
        project_id=request.project_id,
        resource_type="output_set",
        resource_id=output_set.id,
        metadata={"file_count": output_count},
    )
    db.commit()
    _emit_execution_event(db, AuditEventType.EXECUTION_COMPLETED, request, {"output_count": output_count})
    transition_to(db, request, ExecutionRequestStatus.COMPLETED)


def main():
    logger.info("Worker starting")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    backoff = 1

    while not _shutdown_requested:
        try:
            db = SessionLocal()
            backoff = 1
        except Exception as e:
            logger.warning(
                "Database connection failed (retry in %ds): %s", backoff, e
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)
            continue

        try:
            pending_builds = get_pending_builds(db)
            for build in pending_builds:
                if _shutdown_requested:
                    break
                logger.info("Processing build %s", build.id)
                process_build(db, build)

            if _shutdown_requested:
                continue

            pending = get_pending_requests(db)
            for request in pending:
                if _shutdown_requested:
                    break
                logger.info("Processing request %s: %s", request.id, request.name)
                execute_request(db, request)
        except Exception:
            logger.exception("Worker error")
        finally:
            db.close()

        if not _shutdown_requested:
            time.sleep(POLL_INTERVAL)

    logger.info("Worker shutdown complete")


if __name__ == "__main__":
    main()
