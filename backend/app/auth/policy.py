import uuid

from app.models.user import User, UserRole


class PolicyError(Exception):
    """Raised when an authorisation policy check fails."""


def require_any_role(user: User, *roles: UserRole) -> None:
    """Require the user to have one of the specified governance roles."""
    if user.role not in roles:
        allowed = ", ".join(r.value for r in roles)
        raise PolicyError(
            f"Requires one of these roles: {allowed}; user has '{user.role.value}'"
        )


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
