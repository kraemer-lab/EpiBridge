import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.execution_request import ExecutionRequestStatus


class ExecutionRequestCreate(BaseModel):
    analysis_bundle_id: uuid.UUID
    name: str | None = None
    parameter_overrides: dict = {}


class CancelExecutionRequest(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Cancellation reason must not be empty")
        if len(stripped) > 2000:
            raise ValueError("Cancellation reason must not exceed 2000 characters")
        return stripped


class ExecutionRequestRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    analysis_bundle_id: uuid.UUID
    name: str
    timeout_seconds: int
    parameter_overrides: dict
    status: ExecutionRequestStatus
    requested_by_id: uuid.UUID
    cancelled_by_id: uuid.UUID | None = None
    cancelled_by_display_name: str | None = None
    cancelled_by_email: str | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    analysis_name: str
    runtime: str
    resource_identifiers: list[str] = []
    parameters: dict = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExecutionRequestAdminDetail(ExecutionRequestRead):
    log: str = ""
