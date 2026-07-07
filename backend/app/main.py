from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.api.routes.admin import router as admin_router
from app.api.routes.health import router as health_router
from app.api.routes.me import router as me_router
from app.api.routes.projects import router as projects_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.environment_manifest_loader import load_environment_directory
from app.services.execution_environment_service import (
    register_from_manifest as register_environments,
)
from app.services.manifest_loader import load_directory
from app.services.resource_registration import register_from_manifest


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)

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
app.include_router(projects_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
