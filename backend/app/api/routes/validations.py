import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policy import PolicyError, require_capability, require_project_membership
from app.db.session import get_db
from app.models.capability import Capability
from app.models.user import User
from app.schemas.validation_request import (
    BundleValidationStatus,
    ValidationRequestCreate,
    ValidationRequestRead,
)
from app.services.validation_service import (
    create_validation_request,
    get_bundle_validation_status,
    get_validation_request,
    list_validation_requests,
    request_to_read,
)

router = APIRouter()


def _require_capability(current_user: User, capability: Capability) -> None:
    try:
        require_capability(current_user, capability)
    except PolicyError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


@router.get(
    "/projects/{project_id}/bundles/{bundle_id}/validations",
    response_model=List[ValidationRequestRead],
)
def list_bundle_validations(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    requests = list_validation_requests(db, project_id=project_id, bundle_id=bundle_id)
    return [request_to_read(r) for r in requests]


@router.post(
    "/projects/{project_id}/bundles/{bundle_id}/validations",
    response_model=ValidationRequestRead,
    status_code=201,
)
def post_validation_request(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    data: ValidationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.VALIDATION_RUN)

    if data.analysis_bundle_id != bundle_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="analysis_bundle_id must match the bundle in the URL",
        )

    try:
        request = create_validation_request(
            db, data.model_dump(), project_id, current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    return request_to_read(request)


@router.get(
    "/projects/{project_id}/bundles/{bundle_id}/validations/{validation_id}",
    response_model=ValidationRequestRead,
)
def get_bundle_validation(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    validation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    request = get_validation_request(db, validation_id)
    if (
        request is None
        or request.project_id != project_id
        or request.analysis_bundle_id != bundle_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation request not found",
        )
    return request_to_read(request)


@router.get(
    "/projects/{project_id}/bundles/{bundle_id}/validation-status",
    response_model=BundleValidationStatus,
)
def get_bundle_validation_status_endpoint(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    return get_bundle_validation_status(db, bundle_id)
