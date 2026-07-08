import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent, AuditEventType
from app.models.user import User


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


def query_audit_events(
    db: Session,
    *,
    project_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    order: str = "desc",
) -> tuple[list[dict], int]:
    query = db.query(
        AuditEvent.id,
        AuditEvent.event_type,
        AuditEvent.actor_id,
        User.display_name.label("actor_display_name"),
        User.email.label("actor_email"),
        AuditEvent.project_id,
        AuditEvent.resource_type,
        AuditEvent.resource_id,
        AuditEvent.event_metadata,
        AuditEvent.occurred_at,
    ).join(User, AuditEvent.actor_id == User.id)

    if project_id is not None:
        query = query.filter(AuditEvent.project_id == project_id)
    if actor_id is not None:
        query = query.filter(AuditEvent.actor_id == actor_id)
    if resource_type is not None:
        query = query.filter(AuditEvent.resource_type == resource_type)
    if resource_id is not None:
        query = query.filter(AuditEvent.resource_id == resource_id)
    if event_type is not None:
        query = query.filter(AuditEvent.event_type == event_type)
    if date_from is not None:
        query = query.filter(AuditEvent.occurred_at >= date_from)
    if date_to is not None:
        query = query.filter(AuditEvent.occurred_at <= date_to)

    total = query.count()

    order_column = (
        AuditEvent.occurred_at.desc()
        if order == "desc"
        else AuditEvent.occurred_at.asc()
    )
    rows = query.order_by(order_column).offset(offset).limit(limit).all()

    items = [
        {
            "id": row.id,
            "event_type": row.event_type,
            "actor_id": row.actor_id,
            "actor_display_name": row.actor_display_name,
            "actor_email": row.actor_email,
            "project_id": row.project_id,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "event_metadata": row.event_metadata,
            "occurred_at": row.occurred_at,
        }
        for row in rows
    ]
    return items, total
