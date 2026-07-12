import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
WORKER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


class AuditEventType(str, enum.Enum):
    PROJECT_CREATED = "project.created"
    PROJECT_MEMBER_ADDED = "project.member.added"
    PROJECT_MEMBER_REMOVED = "project.member.removed"
    PROJECT_RESOURCE_ALLOCATED = "project.resource.allocated"
    PROJECT_RESOURCE_DEALLOCATED = "project.resource.deallocated"

    BUNDLE_CREATED = "bundle.created"
    BUNDLE_SUBMITTED = "bundle.submitted"
    BUNDLE_APPROVED = "bundle.approved"
    BUNDLE_REJECTED = "bundle.rejected"
    BUNDLE_SUPERSEDED = "bundle.superseded"

    EXECUTION_REQUESTED = "execution.requested"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    EXECUTION_CANCELLED = "execution.cancelled"

    OUTPUT_SET_CREATED = "output_set.created"
    OUTPUT_SET_APPROVED = "output_set.approved"
    OUTPUT_SET_REJECTED = "output_set.rejected"
    OUTPUT_SET_RELEASED = "output_set.released"

    USER_CREATED = "user.created"

    PLATFORM_TERMS_PUBLISHED = "platform_terms.published"
    DATASET_TERMS_PUBLISHED = "dataset_terms.published"
    PLATFORM_TERMS_ACCEPTED = "platform_terms.accepted"
    DATASET_TERMS_ACCEPTED = "dataset_terms.accepted"

    VALIDATION_COMPLETED = "validation.completed"
    VALIDATION_FAILED = "validation.failed"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    __table_args__ = (
        Index("ix_audit_events_resource", "resource_type", "resource_id"),
        Index("ix_audit_events_occurred_at", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
