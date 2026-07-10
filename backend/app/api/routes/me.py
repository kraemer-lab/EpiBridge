from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead
from app.services.terms_service import get_acceptance_status

router = APIRouter()


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    terms = get_acceptance_status(db, current_user.id)
    user_data = UserRead.model_validate(current_user).model_dump()
    user_data["needs_platform_terms_acceptance"] = (
        terms["platform"]["has_terms"] and not terms["platform"]["accepted"]
    )
    user_data["platform_terms_version"] = terms["platform"]["version"]
    return user_data
