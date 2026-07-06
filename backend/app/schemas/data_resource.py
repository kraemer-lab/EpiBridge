import uuid
from datetime import datetime

from pydantic import BaseModel


class DataResourceRead(BaseModel):
    id: uuid.UUID
    identifier: str
    name: str
    alias: str
    description: str
    provider_type: str
    endpoint: dict
    version: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
