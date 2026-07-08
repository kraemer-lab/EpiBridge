import json
import logging
import uuid
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis_bundle import AnalysisBundle, AnalysisBundleStatus
from app.models.build_request import BuildRequest
from app.models.data_resource import DataResource
from app.models.project import Project
from app.models.project_data_resource import ProjectResourceAllocation
from app.models.user import User
from app.schemas.ai_bundle_review import AIBundleReviewRead
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
from app.schemas.output import OutputRead
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.ai_review_service import request_and_perform_review
from app.services.analysis_bundle_service import (
    create_bundle,
    get_environment_runtime,
    get_resource_identifiers,
    update_bundle,
)
from app.services.bundle_store import get_bundle_store
from app.services.environment_builder_service import ensure_build_request
from app.services.execution_environment_service import list_environments
from app.services.execution_request_service import (
    create_execution_request,
    get_execution_request,
    list_execution_requests,
    request_to_read,
)
from app.services.output_service import (
    get_output,
    list_outputs,
    stream_output,
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


def _bundle_to_read(bundle: AnalysisBundle, build_log: str = "") -> AnalysisBundleRead:
    ai_review = None
    if bundle.ai_review is not None:
        ai_review = AIBundleReviewRead.model_validate(bundle.ai_review)
    return AnalysisBundleRead(
        id=bundle.id,
        project_id=bundle.project_id,
        created_by_id=bundle.created_by_id,
        execution_environment_id=bundle.execution_environment_id,
        name=bundle.name,
        source_path=bundle.source_path,
        status=bundle.status,
        runtime=get_environment_runtime(bundle),
        version=bundle.version,
        entrypoint=bundle.entrypoint,
        interpreter=bundle.interpreter,
        arguments=bundle.arguments,
        description=bundle.description,
        resource_identifiers=get_resource_identifiers(bundle),
        outputs=bundle.outputs,
        parameters=bundle.parameters,
        build_status=bundle.build_status,
        build_error=bundle.build_error,
        build_log=build_log,
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
        ai_review=ai_review,
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


class _AttachResourcesBody(BaseModel):
    resource_identifiers: list[str]


@router.post(
    "/projects/{project_id}/resources",
    response_model=List[DataResourceRead],
    status_code=200,
)
def post_project_resources(
    project_id: uuid.UUID,
    body: _AttachResourcesBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_owned_project(db, project_id, current_user.id)
    resources = (
        db.query(DataResource)
        .filter(DataResource.identifier.in_(body.resource_identifiers))
        .all()
    )
    found = {r.identifier for r in resources}
    missing = set(body.resource_identifiers) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data resources not found: {', '.join(sorted(missing))}",
        )
    existing = {r.identifier for r in project.data_resources}
    for r in resources:
        if r.identifier not in existing:
            project.data_resources.append(r)
    db.commit()
    db.refresh(project)
    return project.data_resources


@router.delete(
    "/projects/{project_id}/resources/{resource_id}",
    status_code=204,
)
def delete_project_resource(
    project_id: uuid.UUID,
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user.id)
    join = (
        db.query(ProjectResourceAllocation)
        .filter(
            ProjectResourceAllocation.project_id == project_id,
            ProjectResourceAllocation.data_resource_id == resource_id,
        )
        .first()
    )
    if join is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not attached to this project",
        )
    db.delete(join)
    db.commit()


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
    build_log = ""
    latest = (
        db.query(BuildRequest)
        .filter(BuildRequest.analysis_bundle_id == bundle.id)
        .order_by(BuildRequest.created_at.desc())
        .first()
    )
    if latest is not None:
        build_log = latest.log
    return _bundle_to_read(bundle, build_log=build_log)


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
    "/projects/{project_id}/bundles/upload",
    response_model=AnalysisBundleRead,
    status_code=201,
)
async def post_project_bundle_upload(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(...),
    execution_environment_id: str = Form(...),
    version: str = Form(...),
    entrypoint: str = Form(...),
    interpreter: str = Form("python"),
    arguments: str = Form(""),
    description: str = Form(""),
    resource_identifiers: str = Form("[]"),
    outputs: str = Form("[]"),
    parameters: str = Form("{}"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user.id)

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file must be a ZIP archive",
        )

    ri = json.loads(resource_identifiers)
    if not isinstance(ri, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="resource_identifiers must be a JSON list",
        )
    outs = json.loads(outputs)
    if not isinstance(outs, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="outputs must be a JSON list",
        )
    params = json.loads(parameters)
    if not isinstance(params, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="parameters must be a JSON object",
        )

    bundle_data = {
        "name": name,
        "execution_environment_id": execution_environment_id,
        "version": version,
        "entrypoint": entrypoint,
        "interpreter": interpreter,
        "arguments": arguments,
        "source_path": "",
        "description": description,
        "resource_identifiers": ri,
        "outputs": outs,
        "parameters": params,
    }

    bundle = create_bundle(db, bundle_data, project_id, current_user.id)

    store = get_bundle_store()
    try:
        store_path = store.store(bundle.id, file, entrypoint)
    except ValueError as e:
        db.delete(bundle)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    update_bundle(
        db,
        bundle.id,
        {"source_path": store_path, "status": AnalysisBundleStatus.ACTIVE},
    )

    background_tasks.add_task(request_and_perform_review, bundle.id)

    if ensure_build_request(db, bundle) is None:
        logger = logging.getLogger("api.routes.projects")
        logger.info("Bundle %s registered without build request", bundle.id)

    db.refresh(bundle)
    return _bundle_to_read(bundle)


@router.post(
    "/projects/{project_id}/bundles/{bundle_id}/ai-review",
    response_model=AnalysisBundleRead,
    status_code=201,
)
def post_bundle_ai_review(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(request_and_perform_review, bundle.id)

    db.refresh(bundle)
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
    "/projects/{project_id}/execution-requests/{request_id}/outputs",
    response_model=List[OutputRead],
)
def get_execution_request_outputs(
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
    return list_outputs(db, request_id)


@router.get(
    "/projects/{project_id}/execution-requests/{request_id}/outputs/{output_id}",
    response_model=OutputRead,
)
def get_execution_request_output(
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    output_id: uuid.UUID,
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
    output = get_output(db, output_id)
    if output is None or output.execution_request_id != request_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output not found",
        )
    return output


@router.get(
    "/projects/{project_id}/execution-requests/{request_id}/outputs/{output_id}/download",
)
def download_execution_request_output(
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    output_id: uuid.UUID,
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
    output = get_output(db, output_id)
    if output is None or output.execution_request_id != request_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output not found",
        )
    return stream_output(request_id, output.filename)


@router.get(
    "/execution-environments",
    response_model=List[ExecutionEnvironmentRead],
)
def get_execution_environments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_environments(db, status="active")
