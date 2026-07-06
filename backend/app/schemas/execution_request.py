import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.execution_request import ExecutionRequestStatus


class ExecutionRequestCreate(BaseModel):
    analysis_bundle_id: uuid.UUID
    name: str | None = None
    timeout_seconds: int = 3600
    parameter_overrides: dict = {}


class ExecutionRequestRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    analysis_bundle_id: uuid.UUID
    name: str
    timeout_seconds: int
    parameter_overrides: dict
    status: ExecutionRequestStatus
    requested_by_id: uuid.UUID
    analysis_name: str
    runtime: str
    resource_identifiers: list[str] = []
    parameters: dict = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
