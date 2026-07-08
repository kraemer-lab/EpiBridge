import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.auth.local import hash_password
from app.core.config import settings
from app.models.audit_event import SYSTEM_USER_ID, AuditEventType
from app.models.user import User, UserRole
from app.services.audit_service import create_audit_event
from app.services.auth_framework_seeder import (
    grant_all_capabilities,
    grant_role_capabilities,
    seed_auth_framework,
)


def get_or_create_admin(db: Session) -> User:
    user = db.query(User).filter(User.email == settings.admin_email).first()
    if user is not None:
        if not user.capabilities:
            grant_all_capabilities(db, user)
            db.commit()
            db.refresh(user)
        return user

    seed_auth_framework(db)

    user = User(
        email=settings.admin_email,
        display_name="Administrator",
        password_hash=hash_password(settings.admin_password),
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.flush()
    grant_all_capabilities(db, user)
    db.commit()
    db.refresh(user)
    return user


def create_user(
    db: Session,
    email: str,
    display_name: str,
    password: str,
    role: UserRole = UserRole.RESEARCHER,
    actor_id: uuid.UUID | None = None,
) -> User:
    seed_auth_framework(db)

    user = User(
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.flush()
    grant_role_capabilities(db, user)
    create_audit_event(
        db,
        event_type=AuditEventType.USER_CREATED,
        actor_id=actor_id or SYSTEM_USER_ID,
        project_id=None,
        resource_type="user",
        resource_id=user.id,
        metadata={"user_email": email, "role": role.value},
    )
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> List[User]:
    return db.query(User).order_by(User.display_name).all()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()
