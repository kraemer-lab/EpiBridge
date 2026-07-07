import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis_bundle import AnalysisBundle
    from app.models.execution_environment import ExecutionEnvironment
    from app.models.execution_image import ExecutionImage


class BuildRequestStatus(str, enum.Enum):
    PENDING = "pending"
    BUILDING = "building"
    COMPLETED = "completed"
    FAILED = "failed"


class BuildRequest(Base):
    __tablename__ = "build_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    execution_environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("execution_environments.id"), nullable=False
    )
    analysis_bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_bundles.id"), nullable=False
    )
    dependency_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    builder_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[BuildRequestStatus] = mapped_column(
        String(20), nullable=False, default=BuildRequestStatus.PENDING
    )
    execution_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("execution_images.id"), nullable=True
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    execution_environment: Mapped["ExecutionEnvironment"] = relationship()
    analysis_bundle: Mapped["AnalysisBundle"] = relationship()
    execution_image: Mapped["ExecutionImage | None"] = relationship(
        back_populates="build_requests"
    )
