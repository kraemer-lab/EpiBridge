import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.output import OutputStatus


class OutputRead(BaseModel):
    id: uuid.UUID
    execution_request_id: uuid.UUID
    filename: str
    size: int
    status: OutputStatus
    created_at: datetime

    model_config = {"from_attributes": True}
