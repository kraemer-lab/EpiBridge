from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User, UserRole


def get_or_create_admin(db: Session) -> User:
    user = db.query(User).filter(User.email == settings.admin_email).first()
    if user is not None:
        return user

    user = User(
        email=settings.admin_email,
        display_name="Administrator",
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
