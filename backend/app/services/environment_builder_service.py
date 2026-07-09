import hashlib
import logging
import uuid

from sqlalchemy.orm import Session

from app.builders.registry import registry
from app.models.analysis_bundle import (
    AnalysisBundle,
    AnalysisBundleBuildStatus,
    BuildStrategy,
)
from app.models.build_request import BuildRequest, BuildRequestStatus
from app.models.execution_image import ExecutionImage
from app.services.bundle_store import get_bundle_store

logger = logging.getLogger("services.environment_builder_service")

CUSTOM_BUILD_DIR = "build"


def resolve_builder_for_bundle(bundle: AnalysisBundle):
    runtime = (
        bundle.execution_environment.runtime if bundle.execution_environment else ""
    )
    return registry.get_for_runtime(runtime)


def get_cached_image(
    db: Session, execution_environment_id: uuid.UUID, dependency_hash: str
) -> ExecutionImage | None:
    return (
        db.query(ExecutionImage)
        .filter(
            ExecutionImage.execution_environment_id == execution_environment_id,
            ExecutionImage.dependency_hash == dependency_hash,
        )
        .first()
    )


def _compute_custom_hash(bundle_path, builder):
    hasher = hashlib.sha256()
    dep_file = bundle_path / builder.default_dependency_filename()
    if dep_file.exists() and dep_file.is_file():
        hasher.update(dep_file.read_bytes())
    custom_file = bundle_path / CUSTOM_BUILD_DIR / "Dockerfile"
    if custom_file.exists() and custom_file.is_file():
        hasher.update(custom_file.read_bytes())
    return hasher.hexdigest()


def ensure_build_request(db: Session, bundle: AnalysisBundle) -> BuildRequest | None:
    builder = resolve_builder_for_bundle(bundle)
    if builder is None:
        runtime = (
            bundle.execution_environment.runtime if bundle.execution_environment else ""
        )
        logger.info(
            "No builder registered for runtime %s — bundle %s will not be built",
            runtime,
            bundle.id,
        )
        return None

    bundle_path = get_bundle_store().get_path(bundle.id)

    if bundle.build_strategy == BuildStrategy.CUSTOM.value:
        dependency_hash = _compute_custom_hash(bundle_path, builder)
    else:
        dependency_hash = builder.dependency_hash(bundle_path)

    cached = get_cached_image(db, bundle.execution_environment_id, dependency_hash)
    if cached is not None:
        bundle.build_status = AnalysisBundleBuildStatus.ENVIRONMENT_READY
        bundle.execution_image_id = cached.id
        db.commit()
        return None

    build_request = BuildRequest(
        execution_environment_id=bundle.execution_environment_id,
        analysis_bundle_id=bundle.id,
        dependency_hash=dependency_hash,
        builder_type=builder.identifier(),
        status=BuildRequestStatus.PENDING,
    )
    db.add(build_request)
    db.commit()
    db.refresh(build_request)
    return build_request
