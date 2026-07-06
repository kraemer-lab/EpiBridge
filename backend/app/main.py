from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.me import router as me_router
from app.api.routes.projects import router as projects_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="EpiBridge", lifespan=lifespan)

app.include_router(health_router, prefix="/api")
app.include_router(me_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
