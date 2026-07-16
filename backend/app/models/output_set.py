import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ai_output_set_review import AIOutputSetReview
    from app.models.execution_request import ExecutionRequest
    from app.models.output import Output
    from app.models.user import User


class OutputSetStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    RELEASED = "released"


class OutputSet(Base):
    __tablename__ = "output_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    execution_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_requests.id"),
        nullable=False,
        unique=True,
    )
    status: Mapped[OutputSetStatus] = mapped_column(
        String(64), nullable=False, default=OutputSetStatus.PENDING_REVIEW
    )
    release_package_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    release_package_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    execution_request: Mapped["ExecutionRequest"] = relationship(
        back_populates="output_set"
    )
    rejected_by: Mapped["User | None"] = relationship(foreign_keys=[rejected_by_id])
    outputs: Mapped[list["Output"]] = relationship(
        back_populates="output_set", cascade="all, delete-orphan"
    )
    ai_review: Mapped["AIOutputSetReview | None"] = relationship(
        back_populates="output_set", uselist=False
    )
