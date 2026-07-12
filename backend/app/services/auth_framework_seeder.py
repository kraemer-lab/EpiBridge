import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.audit_event import SYSTEM_USER_ID, WORKER_USER_ID
from app.models.capability import ALL_CAPABILITIES, Capability, CapabilityRecord
from app.models.role import RoleRecord
from app.models.role_capability import RoleCapability
from app.models.user import User, UserRole

_ROLE_CAPABILITY_MAP: dict[UserRole, set[str]] = {
    UserRole.RESEARCHER: {
        Capability.PROJECT_MANAGE,
        Capability.BUNDLE_CREATE,
        Capability.BUNDLE_SUBMIT,
        Capability.EXECUTION_RUN,
        Capability.VALIDATION_RUN,
    },
    UserRole.MODERATOR: {
        Capability.PROJECT_MANAGE,
        Capability.PROJECT_MEMBERS_MANAGE,
        Capability.PROJECT_RESOURCES_MANAGE,
        Capability.BUNDLE_CREATE,
        Capability.BUNDLE_SUBMIT,
        Capability.BUNDLE_REVIEW,
        Capability.EXECUTION_RUN,
        Capability.OUTPUT_REVIEW,
        Capability.VALIDATION_RUN,
    },
    UserRole.MAINTAINER: {
        Capability.PROJECT_MANAGE,
        Capability.PROJECT_MEMBERS_MANAGE,
        Capability.PROJECT_RESOURCES_MANAGE,
        Capability.BUNDLE_CREATE,
        Capability.BUNDLE_SUBMIT,
        Capability.BUNDLE_REVIEW,
        Capability.EXECUTION_RUN,
        Capability.OUTPUT_REVIEW,
        Capability.OUTPUT_RELEASE,
        Capability.ENVIRONMENT_MANAGE,
        Capability.DATA_MANAGE,
        Capability.BUILD_CUSTOMIZE,
        Capability.TERMS_MANAGE,
        Capability.VALIDATION_RUN,
    },
    UserRole.ADMIN: set(ALL_CAPABILITIES),
}


def seed_auth_framework(db: Session) -> None:
    """Idempotently seed capabilities, roles, role-capability mappings, and system users."""  # noqa: E501
    _seed_capabilities(db)
    _seed_roles(db)
    _seed_role_capabilities(db)
    _seed_system_users(db)
    db.commit()


def _seed_capabilities(db: Session) -> None:
    existing = {r.name for r in db.query(CapabilityRecord).all()}
    for cap_name in ALL_CAPABILITIES:
        if cap_name not in existing:
            db.add(CapabilityRecord(name=cap_name))


def _seed_roles(db: Session) -> None:
    existing = {r.name for r in db.query(RoleRecord).all()}
    for role in UserRole:
        if role.value not in existing:
            db.add(RoleRecord(name=role.value))


def _seed_role_capabilities(db: Session) -> None:
    roles = {r.name: r for r in db.query(RoleRecord).all()}
    existing = {
        (rc.role_id, rc.capability_name) for rc in db.query(RoleCapability).all()
    }
    for user_role, capabilities in _ROLE_CAPABILITY_MAP.items():
        role_record = roles.get(user_role.value)
        if role_record is None:
            continue
        for cap_name in capabilities:
            if (role_record.id, cap_name) not in existing:
                db.add(RoleCapability(role_id=role_record.id, capability_name=cap_name))


def grant_all_capabilities(db: Session, user: User) -> None:
    _seed_capabilities(db)
    db.flush()
    for cap_name in ALL_CAPABILITIES:
        db.execute(
            text(
                "INSERT INTO user_capabilities (user_id, capability_name) "
                "VALUES (:uid, :cap) ON CONFLICT DO NOTHING"
            ),
            {"uid": user.id, "cap": cap_name},
        )


def grant_role_capabilities(db: Session, user: User) -> None:
    """Copy capabilities from the user's role template into UserCapability."""
    _seed_capabilities(db)
    _seed_roles(db)
    _seed_role_capabilities(db)
    db.flush()

    default_caps = _ROLE_CAPABILITY_MAP.get(user.role, set())
    for cap_name in default_caps:
        db.execute(
            text(
                "INSERT INTO user_capabilities (user_id, capability_name) "
                "VALUES (:uid, :cap) ON CONFLICT DO NOTHING"
            ),
            {"uid": user.id, "cap": cap_name},
        )


_SYSTEM_USERS: list[tuple[uuid.UUID, str, str]] = [
    (SYSTEM_USER_ID, "system@epibridge.internal", "System"),
    (WORKER_USER_ID, "execution_worker@epibridge.internal", "Execution Worker"),
]


def _seed_system_users(db: Session) -> None:
    """Idempotently seed system user accounts for autonomous platform components.

    System users use well-known UUIDs, have no password (cannot log in),
    and carry no capabilities. They exist solely as accountable actors
    referenced by Audit Events.

    A role value is required by the schema; MAINTAINER is used as the
    closest semantic match to a platform operator.
    """
    for user_id, email, display_name in _SYSTEM_USERS:
        existing = db.query(User).filter(User.id == user_id).first()
        if existing is not None:
            continue
        user = User(
            id=user_id,
            email=email,
            display_name=display_name,
            password_hash="",
            role=UserRole.MAINTAINER,
        )
        db.add(user)
