import uuid
from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectMemberRead(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str
    added_at: datetime


class AddProjectMemberBody(BaseModel):
    email: str
