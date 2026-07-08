from sqlalchemy.orm import Session

from app.auth.local import hash_password
from app.core.config import settings
from app.models.user import User, UserRole
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
    db.commit()
    db.refresh(user)
    return user
