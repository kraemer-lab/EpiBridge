import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.capability import UserCapability
from app.models.project_membership import ProjectMembership


class UserRole(str, enum.Enum):
    RESEARCHER = "researcher"
    MODERATOR = "moderator"
    MAINTAINER = "maintainer"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    capabilities: Mapped[list[UserCapability]] = relationship(
        cascade="all, delete-orphan"
    )
    project_memberships: Mapped[list[ProjectMembership]] = relationship(
        back_populates="user",
        foreign_keys=[ProjectMembership.user_id],
    )

    def has_capability(self, capability_name: str) -> bool:
        return any(c.capability_name == capability_name for c in self.capabilities)
