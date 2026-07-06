import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis_bundle import AnalysisBundle
from app.models.project import Project
from app.models.user import User
from app.schemas.analysis_bundle import (
    AnalysisBundleCreate,
    AnalysisBundleRead,
    AnalysisBundleUpdate,
)
from app.schemas.data_resource import DataResourceRead
from app.schemas.execution_environment import ExecutionEnvironmentRead
from app.schemas.execution_request import (
    ExecutionRequestCreate,
    ExecutionRequestRead,
)
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.analysis_bundle_service import (
    create_bundle,
    get_environment_runtime,
    get_resource_identifiers,
    update_bundle,
)
from app.services.execution_environment_service import list_environments
from app.services.execution_request_service import (
    create_execution_request,
    get_execution_request,
    list_execution_requests,
    request_to_read,
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


def _bundle_to_read(bundle: AnalysisBundle) -> AnalysisBundleRead:
    return AnalysisBundleRead(
        id=bundle.id,
        project_id=bundle.project_id,
        created_by_id=bundle.created_by_id,
        execution_environment_id=bundle.execution_environment_id,
        name=bundle.name,
        status=bundle.status,
        runtime=get_environment_runtime(bundle),
        version=bundle.version,
        entrypoint=bundle.entrypoint,
        description=bundle.description,
        resource_identifiers=get_resource_identifiers(bundle),
        outputs=bundle.outputs,
        parameters=bundle.parameters,
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
    )


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
    return [_bundle_to_read(b) for b in bundles]


@router.get(
    "/projects/{project_id}/bundles/{bundle_id}",
    response_model=AnalysisBundleRead,
)
def get_project_bundle(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user.id)
    bundle = (
        db.query(AnalysisBundle)
        .filter(
            AnalysisBundle.id == bundle_id,
            AnalysisBundle.project_id == project_id,
        )
        .first()
    )
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis bundle not found",
        )
    return _bundle_to_read(bundle)


@router.put(
    "/projects/{project_id}/bundles/{bundle_id}",
    response_model=AnalysisBundleRead,
)
def put_project_bundle(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    data: AnalysisBundleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user.id)
    bundle = (
        db.query(AnalysisBundle)
        .filter(
            AnalysisBundle.id == bundle_id,
            AnalysisBundle.project_id == project_id,
        )
        .first()
    )
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis bundle not found",
        )
    try:
        updated = update_bundle(db, bundle_id, data.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    return _bundle_to_read(updated)


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
    return _bundle_to_read(bundle)


@router.post(
    "/projects/{project_id}/execution-requests",
    response_model=ExecutionRequestRead,
    status_code=201,
)
def post_execution_request(
    project_id: uuid.UUID,
    data: ExecutionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user.id)
    try:
        request = create_execution_request(
            db, data.model_dump(), project_id, current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    return request_to_read(request)


@router.get(
    "/projects/{project_id}/execution-requests",
    response_model=List[ExecutionRequestRead],
)
def get_project_execution_requests(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user.id)
    requests = list_execution_requests(db, project_id=project_id)
    return [request_to_read(r) for r in requests]


@router.get(
    "/projects/{project_id}/execution-requests/{request_id}",
    response_model=ExecutionRequestRead,
)
def get_project_execution_request(
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user.id)
    request = get_execution_request(db, request_id)
    if request is None or request.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution request not found",
        )
    return request_to_read(request)


@router.get(
    "/execution-environments",
    response_model=List[ExecutionEnvironmentRead],
)
def get_execution_environments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_environments(db, status="active")
