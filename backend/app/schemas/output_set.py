import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel

from app.models.output_set import OutputSetStatus
from app.schemas.output import OutputRead


class OutputSetRead(BaseModel):
    id: uuid.UUID
    execution_request_id: uuid.UUID
    execution_request_name: str
    status: OutputSetStatus
    release_package_size: int | None
    outputs: List[OutputRead]
    file_count: int
    requested_by_id: uuid.UUID | None = None
    project_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OutputSetListItem(BaseModel):
    id: uuid.UUID
    execution_request_id: uuid.UUID
    execution_request_name: str
    status: OutputSetStatus
    file_count: int
    release_package_size: int | None
    requested_by_id: uuid.UUID | None = None
    project_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
