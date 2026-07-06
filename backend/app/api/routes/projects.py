import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis_bundle import AnalysisBundle
from app.models.project import Project
from app.models.user import User
from app.schemas.analysis_bundle import AnalysisBundleCreate, AnalysisBundleRead
from app.schemas.data_resource import DataResourceRead
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.analysis_bundle_service import (
    create_bundle,
    get_resource_identifiers,
)
from app.services.project_service import create_project, list_projects

router = APIRouter()


def _get_owned_project(
    db: Session, project_id: uuid.UUID, owner_id: uuid.UUID
) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == owner_id)
        .first()
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


@router.get("/projects", response_model=List[ProjectRead])
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_projects(db, owner_id=current_user.id)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_project(db, project_id, current_user.id)


@router.get(
    "/projects/{project_id}/resources",
    response_model=List[DataResourceRead],
)
def get_project_resources(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_owned_project(db, project_id, current_user.id)
    return project.data_resources


@router.get(
    "/projects/{project_id}/bundles",
    response_model=List[AnalysisBundleRead],
)
def get_project_bundles(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_owned_project(db, project_id, current_user.id)
    bundles = (
        db.query(AnalysisBundle)
        .filter(AnalysisBundle.project_id == project.id)
        .order_by(AnalysisBundle.name)
        .all()
    )
    result = []
    for b in bundles:
        read = AnalysisBundleRead(
            id=b.id,
            project_id=b.project_id,
            created_by_id=b.created_by_id,
            name=b.name,
            runtime=b.runtime,
            version=b.version,
            entrypoint=b.entrypoint,
            description=b.description,
            resource_identifiers=get_resource_identifiers(b),
            outputs=b.outputs,
            parameters=b.parameters,
            created_at=b.created_at,
            updated_at=b.updated_at,
        )
        result.append(read)
    return result


@router.post("/projects", response_model=ProjectRead, status_code=201)
def post_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_project(db, data, owner_id=current_user.id)


@router.post(
    "/projects/{project_id}/bundles",
    response_model=AnalysisBundleRead,
    status_code=201,
)
def post_project_bundle(
    project_id: uuid.UUID,
    data: AnalysisBundleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user.id)

    bundle = create_bundle(db, data.model_dump(), project_id, current_user.id)
    return AnalysisBundleRead(
        id=bundle.id,
        project_id=bundle.project_id,
        created_by_id=bundle.created_by_id,
        name=bundle.name,
        runtime=bundle.runtime,
        version=bundle.version,
        entrypoint=bundle.entrypoint,
        description=bundle.description,
        resource_identifiers=get_resource_identifiers(bundle),
        outputs=bundle.outputs,
        parameters=bundle.parameters,
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
    )
