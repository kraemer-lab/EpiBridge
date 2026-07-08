import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.audit_event import AuditEventType


class AuditEventRead(BaseModel):
    id: uuid.UUID
    event_type: AuditEventType
    actor_id: uuid.UUID
    actor_display_name: str
    actor_email: str
    project_id: uuid.UUID | None
    resource_type: str
    resource_id: uuid.UUID
    event_metadata: dict
    occurred_at: datetime

    model_config = {"from_attributes": True}


class AuditEventList(BaseModel):
    items: list[AuditEventRead]
    total: int
    limit: int
    offset: int
