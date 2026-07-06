import uuid
from datetime import datetime

from pydantic import BaseModel


class OutputRead(BaseModel):
    id: uuid.UUID
    execution_request_id: uuid.UUID
    filename: str
    size: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
