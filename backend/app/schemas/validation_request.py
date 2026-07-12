import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.validation_request import ValidationRequestStatus


class ValidationRequestCreate(BaseModel):
    analysis_bundle_id: uuid.UUID
    name: str | None = None
    timeout_seconds: int = 3600
    parameter_overrides: dict = {}


class ValidationRequestRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    analysis_bundle_id: uuid.UUID
    name: str
    timeout_seconds: int
    parameter_overrides: dict
    status: ValidationRequestStatus
    log: str = ""
    output_files: list = []
    bundle_content_hash: str = ""
    requested_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BundleValidationStatus(BaseModel):
    last_validation_id: str | None = None
    last_validation_hash: str = ""
    current_bundle_hash: str = ""
    is_validated: bool = False
    has_changed: bool = False
