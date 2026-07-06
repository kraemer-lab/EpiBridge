import uuid
from datetime import datetime

from pydantic import BaseModel


class AnalysisBundleCreate(BaseModel):
    name: str
    execution_environment_id: uuid.UUID
    version: str
    entrypoint: str
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
    status: str
    runtime: str
    version: str
    entrypoint: str
    description: str
    resource_identifiers: list[str] = []
    outputs: list[str] = []
    parameters: dict = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalysisBundleUpdate(BaseModel):
    name: str | None = None
    execution_environment_id: uuid.UUID | None = None
    version: str | None = None
    entrypoint: str | None = None
    description: str | None = None
    resource_identifiers: list[str] | None = None
    outputs: list[str] | None = None
    parameters: dict | None = None
