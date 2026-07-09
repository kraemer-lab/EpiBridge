import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.role_capability import RoleCapability


class Capability(str, enum.Enum):
    PROJECT_MANAGE = "project.manage"
    PROJECT_MEMBERS_MANAGE = "project.members.manage"
    PROJECT_RESOURCES_MANAGE = "project.resources.manage"
    BUNDLE_CREATE = "bundle.create"
    BUNDLE_SUBMIT = "bundle.submit"
    BUNDLE_REVIEW = "bundle.review"
    EXECUTION_RUN = "execution.run"
    OUTPUT_REVIEW = "output.review"
    OUTPUT_RELEASE = "output.release"
    ENVIRONMENT_MANAGE = "environment.manage"
    DATA_MANAGE = "data.manage"
    USER_MANAGE = "user.manage"
    BUILD_CUSTOMIZE = "build.customize"

    @classmethod
    def all_values(cls) -> set[str]:
        return {c.value for c in cls}


ALL_CAPABILITIES: set[str] = Capability.all_values()


class CapabilityRecord(Base):
    __tablename__ = "capabilities"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)

    role_assignments: Mapped[list["RoleCapability"]] = relationship(
        back_populates="capability", passive_deletes=True
    )
    user_assignments: Mapped[list["UserCapability"]] = relationship(
        back_populates="capability", passive_deletes=True
    )


class UserCapability(Base):
    __tablename__ = "user_capabilities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    capability_name: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("capabilities.name", ondelete="CASCADE"),
        primary_key=True,
    )

    capability: Mapped["CapabilityRecord"] = relationship(
        back_populates="user_assignments"
    )
