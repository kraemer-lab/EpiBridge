import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.build_request import BuildRequest


class ExecutionImage(Base):
    __tablename__ = "execution_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    execution_environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    dependency_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    image_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    builder_type: Mapped[str] = mapped_column(String(50), nullable=False)
    build_log: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    build_requests: Mapped[list["BuildRequest"]] = relationship(
        back_populates="execution_image"
    )

    __table_args__ = (
        UniqueConstraint(
            "execution_environment_id",
            "dependency_hash",
            name="uq_execution_image_env_hash",
        ),
    )
