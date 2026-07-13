import uuid
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.local import hash_password
from app.core.config import settings
from app.models.audit_event import SYSTEM_USER_ID, WORKER_USER_ID, AuditEventType
from app.models.role import RoleRecord
from app.models.user import User, UserRole
from app.models.user_role import UserRoleAssignment
from app.services.audit_service import create_audit_event
from app.services.auth_framework_seeder import (
    cleanup_role_derived_capabilities,
    seed_auth_framework,
)


def _assign_roles(db: Session, user: User, roles: list[UserRole]) -> None:
    """Replace role assignments for a user with the given set of roles."""
    db.query(UserRoleAssignment).filter(UserRoleAssignment.user_id == user.id).delete()
    role_records = (
        db.query(RoleRecord).filter(RoleRecord.name.in_([r.value for r in roles])).all()
    )
    role_name_to_record = {r.name: r for r in role_records}
    for role_enum in roles:
        record = role_name_to_record.get(role_enum.value)
        if record is not None:
            db.add(UserRoleAssignment(user_id=user.id, role_id=record.id))


def get_or_create_admin(db: Session) -> User:
    admin_email = settings.admin_email
    user = db.query(User).filter(User.email == admin_email).first()
    if user is not None:
        if not user.role_assignments:
            _assign_roles(db, user, [UserRole.ADMIN])
            cleanup_role_derived_capabilities(db, user)
            db.commit()
            db.refresh(user)
        return user

    seed_auth_framework(db)

    user = User(
        email=admin_email,
        display_name="Administrator",
        password_hash=hash_password(settings.admin_password),
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.flush()
    _assign_roles(db, user, [UserRole.ADMIN])
    db.commit()
    db.refresh(user)
    return user


def get_or_create_user(
    db: Session,
    email: str,
    display_name: str,
    password: str,
    role: UserRole,
    roles: list[UserRole] | None = None,
) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is not None:
        assigned_roles = roles if roles else [role]
        if user.role_assignments:
            current_roles = {a.role.name for a in user.role_assignments}
            requested_roles = {r.value for r in assigned_roles}
            if current_roles != requested_roles:
                _assign_roles(db, user, assigned_roles)
                cleanup_role_derived_capabilities(db, user)
                db.commit()
                db.refresh(user)
        else:
            _assign_roles(db, user, assigned_roles)
            cleanup_role_derived_capabilities(db, user)
            db.commit()
            db.refresh(user)
        return user

    seed_auth_framework(db)

    assigned_roles = roles if roles else [role]

    user = User(
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.flush()
    _assign_roles(db, user, assigned_roles)
    create_audit_event(
        db,
        event_type=AuditEventType.USER_CREATED,
        actor_id=SYSTEM_USER_ID,
        project_id=None,
        resource_type="user",
        resource_id=user.id,
        metadata={
            "user_email": email,
            "roles": [r.value for r in assigned_roles],
        },
    )
    db.commit()
    db.refresh(user)
    return user


def create_user(
    db: Session,
    email: str,
    display_name: str,
    password: str,
    roles: list[UserRole] | None = None,
    actor_id: uuid.UUID | None = None,
) -> User:
    seed_auth_framework(db)

    assigned_roles = roles if roles else [UserRole.RESEARCHER]

    user = User(
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
        role=assigned_roles[0] if assigned_roles else UserRole.RESEARCHER,
    )
    db.add(user)
    db.flush()
    _assign_roles(db, user, assigned_roles)
    create_audit_event(
        db,
        event_type=AuditEventType.USER_CREATED,
        actor_id=actor_id or SYSTEM_USER_ID,
        project_id=None,
        resource_type="user",
        resource_id=user.id,
        metadata={
            "user_email": email,
            "roles": [r.value for r in assigned_roles],
        },
    )
    db.commit()
    db.refresh(user)
    return user


def _sync_advanced_capabilities(db: Session, user: User, caps: list[str]) -> None:
    """Replace advanced capability grants with the given list.
    Only capabilities NOT covered by any role template are stored
    in user_capabilities. Role-derived capabilities are computed
    at runtime and are not written here."""
    existing = {c.capability_name for c in user.advanced_capabilities}
    to_add = set(caps) - existing
    to_remove = existing - set(caps)
    for cap_name in to_add:
        db.execute(
            text(
                "INSERT INTO user_capabilities (user_id, capability_name) "
                "VALUES (:uid, :cap) ON CONFLICT DO NOTHING"
            ),
            {"uid": user.id, "cap": cap_name},
        )
    for cap_name in to_remove:
        db.execute(
            text(
                "DELETE FROM user_capabilities "
                "WHERE user_id = :uid AND capability_name = :cap"
            ),
            {"uid": user.id, "cap": cap_name},
        )


def update_user(
    db: Session,
    user_id: uuid.UUID,
    display_name: str | None = None,
    password: str | None = None,
    roles: list[UserRole] | None = None,
    advanced_capabilities: list[str] | None = None,
    actor_id: uuid.UUID | None = None,
) -> User | None:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None

    if display_name is not None:
        user.display_name = display_name

    if password is not None:
        user.password_hash = hash_password(password)

    if roles is not None:
        _assign_roles(db, user, roles)
        cleanup_role_derived_capabilities(db, user)

    if advanced_capabilities is not None:
        _sync_advanced_capabilities(db, user, advanced_capabilities)

    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> List[User]:
    return (
        db.query(User)
        .filter(~User.id.in_([SYSTEM_USER_ID, WORKER_USER_ID]))
        .order_by(User.display_name)
        .all()
    )


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()
