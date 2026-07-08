import uuid

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent, AuditEventType


def create_audit_event(
    db: Session,
    *,
    event_type: AuditEventType | str,
    actor_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    resource_type: str,
    resource_id: uuid.UUID,
    metadata: dict | None = None,
) -> AuditEvent:
    if isinstance(event_type, str):
        event_type = AuditEventType(event_type)

    event = AuditEvent(
        event_type=event_type.value,
        actor_id=actor_id,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        event_metadata=metadata or {},
    )
    db.add(event)
    return event
