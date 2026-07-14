import mimetypes
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.data_resource import DataResourceRead
from app.services.resource_publication_service import (
    get_artefact_root,
    is_published_artefact,
    list_published_artefacts,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


class ArtefactList(BaseModel):
    artefacts: list[str]


@router.get(
    "/resources",
    response_model=List[DataResourceRead],
)
def get_resources(
    db: Session = Depends(get_db),
):
    from app.models.data_resource import DataResource

    return (
        db.query(DataResource)
        .filter(DataResource.status == "active")
        .order_by(DataResource.name)
        .all()
    )


@router.get(
    "/resources/{identifier}",
    response_model=DataResourceRead,
)
def get_resource(
    identifier: str,
    db: Session = Depends(get_db),
):
    from app.models.data_resource import DataResource

    resource = (
        db.query(DataResource).filter(DataResource.identifier == identifier).first()
    )
    if resource is None or resource.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data resource not found",
        )
    return resource


@router.get(
    "/resources/{identifier}/artefacts",
    response_model=ArtefactList,
)
def list_resource_artefacts(
    identifier: str,
    db: Session = Depends(get_db),
):
    from app.models.data_resource import DataResource

    resource = (
        db.query(DataResource).filter(DataResource.identifier == identifier).first()
    )
    if resource is None or resource.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data resource not found",
        )
    files = list_published_artefacts(resource)
    return ArtefactList(artefacts=files)


@router.get(
    "/resources/{identifier}/artefacts/{path:path}",
    response_class=FileResponse,
)
def get_resource_artefact(
    identifier: str,
    path: str,
    db: Session = Depends(get_db),
):
    from app.models.data_resource import DataResource

    resource = (
        db.query(DataResource).filter(DataResource.identifier == identifier).first()
    )
    if resource is None or resource.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data resource not found",
        )

    artefact_root = get_artefact_root(resource)
    if not artefact_root.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artefact directory not available",
        )

    artefact_root = artefact_root.resolve()
    requested = (artefact_root / path).resolve()

    try:
        requested.relative_to(artefact_root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path traversal blocked",
        )

    if not is_published_artefact(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artefact not found",
        )

    if not requested.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artefact not found",
        )

    media_type, _ = mimetypes.guess_type(str(requested))
    if media_type is None:
        media_type = "application/octet-stream"

    return FileResponse(requested, media_type=media_type)
