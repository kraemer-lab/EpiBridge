import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.capability import UserCapability
from app.models.project_membership import ProjectMembership

if TYPE_CHECKING:
    from app.models.user_role import UserRoleAssignment


class UserRole(str, enum.Enum):
    RESEARCHER = "researcher"
    MODERATOR = "moderator"
    MAINTAINER = "maintainer"
    ADMIN = "admin"


# Role templates: the canonical set of capabilities each role provides.
# These are authoritative for runtime capability derivation.
_ROLE_CAPABILITY_MAP: dict[UserRole, set[str]] = {}


def set_role_capability_map(mapping: dict[UserRole, set[str]]) -> None:
    _ROLE_CAPABILITY_MAP.clear()
    _ROLE_CAPABILITY_MAP.update(mapping)


def get_role_capability_map() -> dict[UserRole, set[str]]:
    return dict(_ROLE_CAPABILITY_MAP)


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

    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    advanced_capabilities: Mapped[list["UserCapability"]] = relationship(
        "UserCapability",
        cascade="all, delete-orphan",
    )
    project_memberships: Mapped[list[ProjectMembership]] = relationship(
        back_populates="user",
        foreign_keys=[ProjectMembership.user_id],
    )

    def _role_derived_capabilities(self) -> set[str]:
        caps: set[str] = set()
        for assignment in self.role_assignments:
            role_enum = _try_parse_role(assignment.role.name)
            if role_enum is not None:
                template = _ROLE_CAPABILITY_MAP.get(role_enum, set())
                caps.update(template)
        return caps

    @property
    def capability_names(self) -> list[str]:
        role_caps = self._role_derived_capabilities()
        advanced = {c.capability_name.value for c in self.advanced_capabilities}
        return list(role_caps | advanced)

    def has_capability(self, capability_name: str) -> bool:
        if any(
            c.capability_name == capability_name for c in self.advanced_capabilities
        ):
            return True
        for assignment in self.role_assignments:
            role_enum = _try_parse_role(assignment.role.name)
            if role_enum is not None:
                template = _ROLE_CAPABILITY_MAP.get(role_enum, set())
                if capability_name in template:
                    return True
        return False

    @property
    def role_names(self) -> list[str]:
        return [a.role.name for a in self.role_assignments]

    @property
    def roles(self) -> list["UserRole"]:
        result: list[UserRole] = []
        for a in self.role_assignments:
            role = _try_parse_role(a.role.name)
            if role is not None:
                result.append(role)
        return result


def _try_parse_role(name: str) -> UserRole | None:
    try:
        return UserRole(name)
    except ValueError:
        return None
