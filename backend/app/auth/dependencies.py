from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from app.db.session import get_db
from app.models.user import User
from app.services.session_service import get_valid_session


def get_current_user(
    request: Request,
    db: DBSession = Depends(get_db),
) -> User:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    session = get_valid_session(db, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    return session.user


def require_platform_terms_accepted(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    from app.services.terms_service import (
        get_current_platform_terms,
        has_accepted_latest,
    )

    terms = get_current_platform_terms(db)
    if terms is None:
        return current_user

    if not has_accepted_latest(db, current_user.id, terms.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform terms not accepted",
        )
    return current_user
