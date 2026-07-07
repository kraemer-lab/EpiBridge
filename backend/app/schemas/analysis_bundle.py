import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field

from app.schemas.ai_bundle_review import AIBundleReviewRead
from app.schemas.execution_environment import _display_name


class AnalysisBundleCreate(BaseModel):
    name: str
    execution_environment_id: uuid.UUID
    version: str
    entrypoint: str
    source_path: str = ""
    description: str = ""
    resource_identifiers: list[str] = []
    outputs: list[str] = []
    parameters: dict = {}
    status: str = "draft"


class AnalysisBundleRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by_id: uuid.UUID
    execution_environment_id: uuid.UUID
    name: str
    source_path: str
    status: str
    runtime: str
    version: str
    entrypoint: str
    description: str
    build_status: str = "environment_not_built"
    build_error: str = ""
    resource_identifiers: list[str] = []
    outputs: list[str] = []
    parameters: dict = {}
    created_at: datetime
    updated_at: datetime
    ai_review: AIBundleReviewRead | None = None

    @computed_field
    @property
    def display_runtime(self) -> str:
        return _display_name(self.runtime)

    model_config = {"from_attributes": True}


class AnalysisBundleUpdate(BaseModel):
    name: str | None = None
    execution_environment_id: uuid.UUID | None = None
    version: str | None = None
    entrypoint: str | None = None
    source_path: str | None = None
    description: str | None = None
    resource_identifiers: list[str] | None = None
    outputs: list[str] | None = None
    parameters: dict | None = None
