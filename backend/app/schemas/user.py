import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user import UserRole
from app.schemas.common import ValidEmail


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    roles: list[UserRole]
    capabilities: list[str] = Field(validation_alias="capability_names")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class UserCreate(BaseModel):
    email: ValidEmail
    display_name: str
    password: str = Field(min_length=8)
    roles: list[UserRole] = [UserRole.RESEARCHER]


class UserUpdate(BaseModel):
    display_name: str | None = None
    password: str | None = Field(default=None, min_length=8)
    roles: list[UserRole] | None = None
    advanced_capabilities: list[str] | None = None
