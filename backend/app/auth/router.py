from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.auth import get_identity_provider
from app.auth.base import AuthenticationError
from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead
from app.services.session_service import create_session, delete_session

router = APIRouter(prefix="/auth")


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/login", response_model=UserRead)
def login(
    body: LoginBody,
    response: Response,
    db: DBSession = Depends(get_db),
):
    provider = get_identity_provider()
    try:
        user = provider.authenticate(db, email=body.email, password=body.password)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    session = create_session(db, user.id)
    response.set_cookie(
        key="session_id",
        value=session.id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return user


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(db, session_id)
    response.delete_cookie(
        key="session_id",
        path="/",
    )
