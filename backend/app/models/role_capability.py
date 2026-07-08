import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.capability import CapabilityRecord
    from app.models.role import RoleRecord


class RoleCapability(Base):
    __tablename__ = "role_capabilities"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    capability_name: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("capabilities.name", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped["RoleRecord"] = relationship(back_populates="capability_assignments")
    capability: Mapped["CapabilityRecord"] = relationship(
        back_populates="role_assignments"
    )
