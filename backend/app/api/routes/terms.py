import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.terms import TermsOfServiceRead
from app.services import terms_service

router = APIRouter()


@router.get(
    "/terms/platform/current",
    response_model=TermsOfServiceRead,
)
def get_platform_terms_current(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    terms = terms_service.get_current_platform_terms(db)
    if terms is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No platform terms published",
        )
    return terms


@router.post("/terms/platform/accept", status_code=200)
def accept_platform_terms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    terms = terms_service.get_current_platform_terms(db)
    if terms is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No platform terms published",
        )
    terms_service.accept_terms(db, user=current_user, terms_of_service=terms)
    db.commit()
    return {"status": "accepted"}


@router.get("/terms/status")
def get_terms_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return terms_service.get_acceptance_status(db, current_user.id)


@router.get(
    "/terms/resources/{resource_id}/current",
    response_model=TermsOfServiceRead,
)
def get_resource_terms_current(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    terms = terms_service.get_current_resource_terms(db, resource_id)
    if terms is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No terms published for this data resource",
        )
    return terms


@router.post("/terms/resources/{resource_id}/accept", status_code=200)
def accept_resource_terms(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    terms = terms_service.get_current_resource_terms(db, resource_id)
    if terms is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No terms published for this data resource",
        )
    terms_service.accept_terms(db, user=current_user, terms_of_service=terms)
    db.commit()
    return {"status": "accepted"}
