import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator

from app.models.output_set import OutputSetStatus
from app.schemas.ai_output_set_review import AIOutputSetReviewRead
from app.schemas.output import OutputRead


class RejectOutputSetRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class OutputSetRead(BaseModel):
    id: uuid.UUID
    execution_request_id: uuid.UUID
    execution_request_name: str
    status: OutputSetStatus
    release_package_size: int | None
    rejection_reason: str | None = None
    outputs: List[OutputRead]
    file_count: int
    requested_by_id: uuid.UUID | None = None
    project_name: str = ""
    ai_review: AIOutputSetReviewRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OutputSetListItem(BaseModel):
    id: uuid.UUID
    execution_request_id: uuid.UUID
    execution_request_name: str
    status: OutputSetStatus
    file_count: int
    rejection_reason: str | None = None
    release_package_size: int | None
    requested_by_id: uuid.UUID | None = None
    project_name: str = ""
    ai_review: AIOutputSetReviewRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
