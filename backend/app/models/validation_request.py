import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis_bundle import AnalysisBundle
    from app.models.project import Project
    from app.models.user import User


class ValidationRequestStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationRequest(Base):
    __tablename__ = "validation_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    analysis_bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_bundles.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    parameter_overrides: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    status: Mapped[ValidationRequestStatus] = mapped_column(
        String(64), nullable=False, default=ValidationRequestStatus.PENDING
    )
    log: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output_files: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    bundle_content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship()
    analysis_bundle: Mapped["AnalysisBundle"] = relationship()
    requested_by: Mapped["User"] = relationship()
