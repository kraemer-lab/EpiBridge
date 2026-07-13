import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.role_capability import RoleCapability
    from app.models.user_role import UserRoleAssignment


class RoleRecord(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    capability_assignments: Mapped[list["RoleCapability"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    user_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
