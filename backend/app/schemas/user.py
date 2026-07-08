import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.user import UserRole


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    capabilities: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
