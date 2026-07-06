import uuid
from datetime import datetime

from pydantic import BaseModel


class ExecutionEnvironmentRead(BaseModel):
    id: uuid.UUID
    identifier: str
    name: str
    runtime: str
    description: str
    status: str
    image_reference: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
