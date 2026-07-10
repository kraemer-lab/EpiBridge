import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes.admin import router as admin_router
from app.api.routes.environments import router as environments_router
from app.api.routes.health import router as health_router
from app.api.routes.me import router as me_router
from app.api.routes.projects import router as projects_router
from app.api.routes.terms import router as terms_router
from app.auth.dependencies import require_platform_terms_accepted
from app.auth.policy import PolicyError
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.migration import ensure_migrated
from app.db.session import SessionLocal
from app.services.environment_manifest_loader import load_environment_directory
from app.services.execution_environment_service import (
    register_from_manifest as register_environments,
)
from app.services.manifest_loader import load_directory
from app.services.resource_registration import register_from_manifest
from app.services.session_service import cleanup_expired_sessions

logger = logging.getLogger("epibridge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    ensure_migrated()

    db: Session = SessionLocal()
    try:
        cleaned = cleanup_expired_sessions(db)
        if cleaned:
            logger.info("Cleaned %d expired session(s)", cleaned)
    finally:
        db.close()

    # Ensure application storage directories exist.
    for store_dir in (
        Path(settings.output_dir),
        Path(settings.bundle_store_dir),
        Path(settings.release_dir),
    ):
        store_dir.mkdir(parents=True, exist_ok=True)

    if settings.auto_register_resources:
        manifest_path = Path(settings.resource_manifest_dir)
        if not manifest_path.is_dir():
            raise RuntimeError(
                f"Resource manifest directory not found: {manifest_path}. "
                "Set RESOURCE_MANIFEST_DIR env var to a valid directory."
            )
        entries = load_directory(manifest_path)
        db: Session = SessionLocal()
        try:
            register_from_manifest(db, entries)
        finally:
            db.close()

    if settings.auto_register_environments:
        env_manifest_path = Path(settings.environment_manifest_dir)
        if not env_manifest_path.is_dir():
            raise RuntimeError(
                f"Environment manifest directory not found: {env_manifest_path}. "
                "Set ENVIRONMENT_MANIFEST_DIR env var to a valid directory."
            )
        env_entries = load_environment_directory(env_manifest_path)
        db: Session = SessionLocal()
        try:
            register_environments(db, env_entries)
        finally:
            db.close()

    yield


app = FastAPI(title="EpiBridge", lifespan=lifespan)

app.include_router(health_router, prefix="/api")
app.include_router(me_router, prefix="/api")
app.include_router(
    projects_router,
    prefix="/api",
    dependencies=[Depends(require_platform_terms_accepted)],
)
app.include_router(auth_router, prefix="/api")
app.include_router(
    environments_router,
    prefix="/api",
    dependencies=[Depends(require_platform_terms_accepted)],
)
app.include_router(
    admin_router,
    prefix="/api",
    dependencies=[Depends(require_platform_terms_accepted)],
)
app.include_router(terms_router, prefix="/api")


@app.exception_handler(PolicyError)
def policy_error_handler(request: Request, exc: PolicyError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": "Forbidden"})


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger.warning(
        "Unhandled ValueError on %s %s: %s", request.method, request.url.path, exc
    )
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request."},
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        "%s %s %s (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration * 1000,
    )
    return response
