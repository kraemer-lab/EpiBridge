import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.capability import Capability
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.user import User


class PolicyError(Exception):
    """Raised when an authorisation policy check fails."""


def require_capability(user: User, capability: Capability | str) -> None:
    """Require the user to possess a specific capability."""
    cap_str = capability.value if isinstance(capability, Capability) else capability
    if not user.has_capability(cap_str):
        raise PolicyError(f"Requires capability '{cap_str}'; user lacks it")


def require_project_membership(
    db: Session, user: User, project_id: uuid.UUID
) -> Project:
    """Require the user to be a member of the project.

    Returns the project if the user is a member.
    """
    project = (
        db.query(Project)
        .join(ProjectMembership)
        .filter(
            Project.id == project_id,
            ProjectMembership.user_id == user.id,
        )
        .first()
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def _owner_id(resource) -> uuid.UUID | None:
    """Extract the owning user's ID from a domain resource."""
    if hasattr(resource, "created_by_id"):
        return resource.created_by_id
    if hasattr(resource, "owner_id"):
        return resource.owner_id
    return None


def require_owner(user: User, resource) -> None:
    """Require the user to be the owner or creator of the resource."""
    oid = _owner_id(resource)
    if oid is not None and user.id != oid:
        raise PolicyError("User does not own this resource")
