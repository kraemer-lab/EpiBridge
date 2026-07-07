from sqlalchemy.orm import Session

from app.auth.local import hash_password
from app.core.config import settings
from app.models.user import User, UserRole


def get_or_create_admin(db: Session) -> User:
    user = db.query(User).filter(User.email == settings.admin_email).first()
    if user is not None:
        return user

    user = User(
        email=settings.admin_email,
        display_name="Administrator",
        password_hash=hash_password(settings.admin_password),
        role=UserRole.ADMIN,
    )
    db.add(user)
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
    user = User(
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
