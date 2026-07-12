import json
import uuid
from datetime import datetime
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
from app.auth.policy import (
    PolicyError,
    require_capability,
    require_project_membership,
)
from app.db.session import get_db
from app.models.analysis_bundle import (
    AnalysisBundle,
    AnalysisBundleStatus,
    BuildStrategy,
)
from app.models.audit_event import AuditEventType
from app.models.build_request import BuildRequest
from app.models.capability import Capability
from app.models.data_resource import DataResource
from app.models.project_data_resource import ProjectResourceAllocation
from app.models.user import User
from app.schemas.ai_bundle_review import AIBundleReviewRead
from app.schemas.analysis_bundle import (
    AnalysisBundleCreate,
    AnalysisBundleRead,
    AnalysisBundleUpdate,
)
from app.schemas.data_resource import DataResourceRead
from app.schemas.execution_request import (
    ExecutionRequestCreate,
    ExecutionRequestRead,
)
from app.schemas.output import OutputRead
from app.schemas.output_set import OutputSetRead
from app.schemas.project import (
    AddProjectMemberBody,
    ProjectCreate,
    ProjectMemberRead,
    ProjectRead,
)
from app.services.ai_review_service import request_and_perform_review
from app.services.analysis_bundle_service import (
    create_bundle,
    get_environment_runtime,
    get_resource_identifiers,
    update_bundle,
    validate_build_strategy,
)
from app.services.audit_service import create_audit_event
from app.services.bundle_store import get_bundle_store
from app.services.execution_request_service import (
    create_execution_request,
    get_execution_request,
    list_execution_requests,
    request_to_read,
)
from app.services.output_set_service import (
    get_released_output_set,
    list_outputs_by_set,
    stream_release_package,
)
from app.services.project_service import (
    add_member,
    create_project,
    list_members,
    list_projects,
    remove_member,
)
from app.services.terms_service import (
    get_current_resource_terms,
    has_accepted_latest,
)
from app.workflow.bundle import submit_bundle


def _require_capability(current_user: User, capability: Capability) -> None:
    try:
        require_capability(current_user, capability)
    except PolicyError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


router = APIRouter()


def _require_resource_terms_accepted(
    db: Session,
    user: User,
    resources: list[DataResource],
) -> None:
    unaccepted = []
    for r in resources:
        terms = get_current_resource_terms(db, r.id)
        if terms is not None and not has_accepted_latest(db, user.id, terms.id):
            unaccepted.append(r.name)
    if unaccepted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=("Terms not accepted for resource(s): " + ", ".join(unaccepted)),
        )


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
        build_strategy=bundle.build_strategy,
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
    return list_projects(db, user_id=current_user.id)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_project_membership(db, current_user, project_id)


@router.get(
    "/projects/{project_id}/resources",
    response_model=List[DataResourceRead],
)
def get_project_resources(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project_membership(db, current_user, project_id)
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
    project = require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.PROJECT_RESOURCES_MANAGE)
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
    _require_resource_terms_accepted(db, current_user, resources)

    existing_resources = {
        a.data_resource_id
        for a in db.query(ProjectResourceAllocation).filter(
            ProjectResourceAllocation.project_id == project.id,
            ProjectResourceAllocation.revoked_at.is_(None),
        )
    }
    allocated_resources = []
    for r in resources:
        if r.id not in existing_resources:
            allocation = ProjectResourceAllocation(
                project_id=project.id,
                data_resource_id=r.id,
                created_by_id=current_user.id,
            )
            db.add(allocation)
            allocated_resources.append({"name": r.name, "identifier": r.identifier})

    if allocated_resources:
        create_audit_event(
            db,
            event_type=AuditEventType.PROJECT_RESOURCE_ALLOCATED,
            actor_id=current_user.id,
            project_id=project.id,
            resource_type="project",
            resource_id=project.id,
            metadata={"resources": allocated_resources},
        )
    db.commit()

    allocations = (
        db.query(ProjectResourceAllocation)
        .filter(
            ProjectResourceAllocation.project_id == project.id,
            ProjectResourceAllocation.revoked_at.is_(None),
        )
        .all()
    )
    return [a.data_resource for a in allocations]


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
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.PROJECT_RESOURCES_MANAGE)
    join = (
        db.query(ProjectResourceAllocation)
        .filter(
            ProjectResourceAllocation.project_id == project_id,
            ProjectResourceAllocation.data_resource_id == resource_id,
            ProjectResourceAllocation.revoked_at.is_(None),
        )
        .first()
    )
    if join is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not attached to this project",
        )
    join.revoked_by_id = current_user.id
    join.revoked_at = datetime.utcnow()
    resource_name = join.data_resource.name if join.data_resource else ""
    resource_identifier = join.data_resource.identifier if join.data_resource else ""
    create_audit_event(
        db,
        event_type=AuditEventType.PROJECT_RESOURCE_DEALLOCATED,
        actor_id=current_user.id,
        project_id=project_id,
        resource_type="project",
        resource_id=project_id,
        metadata={
            "resource_name": resource_name,
            "resource_identifier": resource_identifier,
        },
    )
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
    project = require_project_membership(db, current_user, project_id)
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
    require_project_membership(db, current_user, project_id)
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
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_CREATE)
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
    if current_user.id != bundle.created_by_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    if bundle.status != AnalysisBundleStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot edit bundle in state: {bundle.status}",
        )

    if data.build_strategy == BuildStrategy.CUSTOM.value:
        _require_capability(current_user, Capability.BUILD_CUSTOMIZE)

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
    _require_capability(current_user, Capability.PROJECT_MANAGE)
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
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_CREATE)
    if data.build_strategy == BuildStrategy.CUSTOM.value:
        _require_capability(current_user, Capability.BUILD_CUSTOMIZE)
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
    build_strategy: str = Form("institutional"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_CREATE)

    if build_strategy == BuildStrategy.CUSTOM.value:
        _require_capability(current_user, Capability.BUILD_CUSTOMIZE)

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
        "build_strategy": build_strategy,
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

    update_bundle(db, bundle.id, {"source_path": store_path})

    background_tasks.add_task(request_and_perform_review, bundle.id)

    db.refresh(bundle)
    return _bundle_to_read(bundle)


@router.post(
    "/projects/{project_id}/bundles/{bundle_id}/submit",
    response_model=AnalysisBundleRead,
    status_code=200,
)
def post_submit_bundle(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_SUBMIT)

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

    if current_user.id != bundle.created_by_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    if bundle.build_strategy == BuildStrategy.CUSTOM.value:
        _require_capability(current_user, Capability.BUILD_CUSTOMIZE)

    _require_resource_terms_accepted(db, current_user, bundle.data_resources)

    bundle_path = get_bundle_store().get_path(bundle.id) if bundle.source_path else None
    strategy_error = validate_build_strategy(bundle, bundle_path)
    if strategy_error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=strategy_error,
        )

    try:
        submit_bundle(db, bundle)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    create_audit_event(
        db,
        event_type=AuditEventType.BUNDLE_SUBMITTED,
        actor_id=current_user.id,
        project_id=project_id,
        resource_type="analysis_bundle",
        resource_id=bundle.id,
        metadata={"bundle_name": bundle.name},
    )
    db.commit()
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
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_CREATE)
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
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.EXECUTION_RUN)
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
    require_project_membership(db, current_user, project_id)
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
    require_project_membership(db, current_user, project_id)
    request = get_execution_request(db, request_id)
    if request is None or request.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution request not found",
        )
    return request_to_read(request)


@router.get(
    "/projects/{project_id}/execution-requests/{request_id}/outputs",
    response_model=OutputSetRead,
)
def get_execution_request_outputs(
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    request = get_execution_request(db, request_id)
    if request is None or request.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution request not found",
        )
    output_set = get_released_output_set(db, request_id)
    if output_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No released outputs found for this execution request",
        )
    outputs = list_outputs_by_set(db, output_set.id)
    return OutputSetRead(
        id=output_set.id,
        execution_request_id=output_set.execution_request_id,
        execution_request_name=request.name,
        status=output_set.status,
        release_package_size=output_set.release_package_size,
        outputs=[
            OutputRead(
                id=o.id,
                output_set_id=o.output_set_id,
                filename=o.filename,
                size=o.size,
                created_at=o.created_at,
            )
            for o in outputs
        ],
        file_count=len(outputs),
        created_at=output_set.created_at,
        updated_at=output_set.updated_at,
    )


@router.get(
    "/projects/{project_id}/execution-requests/{request_id}/outputs/download",
)
def download_execution_request_outputs(
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    request = get_execution_request(db, request_id)
    if request is None or request.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution request not found",
        )
    output_set = get_released_output_set(db, request_id)
    if output_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No released outputs found for this execution request",
        )
    return stream_release_package(output_set)


@router.get(
    "/projects/{project_id}/members",
    response_model=List[ProjectMemberRead],
)
def get_project_members(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    return list_members(db, project_id)


@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberRead,
    status_code=201,
)
def post_project_member(
    project_id: uuid.UUID,
    body: AddProjectMemberBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.PROJECT_MEMBERS_MANAGE)

    member = db.query(User).filter(User.email == body.email).first()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    membership = add_member(db, project_id, member, invited_by_id=current_user.id)
    return {
        "user_id": member.id,
        "email": member.email,
        "display_name": member.display_name,
        "added_at": membership.created_at,
    }


@router.delete(
    "/projects/{project_id}/members/{user_id}",
    status_code=204,
)
def delete_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.PROJECT_MEMBERS_MANAGE)

    removed = remove_member(db, project_id, user_id, actor_id=current_user.id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )


def _require_draft_status(bundle: AnalysisBundle) -> None:
    if bundle.status != AnalysisBundleStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot modify bundle in state: {bundle.status}",
        )


def _get_project_bundle(
    bundle_id: uuid.UUID, project_id: uuid.UUID, db: Session
) -> AnalysisBundle:
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
    return bundle


@router.get(
    "/projects/{project_id}/bundles/{bundle_id}/files",
)
def get_bundle_files(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    bundle = _get_project_bundle(bundle_id, project_id, db)
    store = get_bundle_store()
    files = store.list_files(bundle.id)
    return {
        "files": files,
        "total_size": store.get_total_size(bundle.id),
    }


@router.post(
    "/projects/{project_id}/bundles/{bundle_id}/files/upload",
    status_code=200,
)
def post_bundle_files_upload(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_CREATE)
    bundle = _get_project_bundle(bundle_id, project_id, db)
    _require_draft_status(bundle)

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file must be a ZIP archive",
        )

    store = get_bundle_store()
    try:
        store.replace_contents(bundle.id, file)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    update_bundle(db, bundle.id, {"source_path": str(bundle.id)})
    return {"status": "ok"}


@router.post(
    "/projects/{project_id}/bundles/{bundle_id}/files/import",
    status_code=200,
)
def post_bundle_files_import(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_CREATE)
    bundle = _get_project_bundle(bundle_id, project_id, db)
    _require_draft_status(bundle)

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file must be a ZIP archive",
        )

    store = get_bundle_store()
    try:
        store.import_archive(bundle.id, file)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    update_bundle(db, bundle.id, {"source_path": str(bundle.id)})
    return {"status": "ok"}


@router.post(
    "/projects/{project_id}/bundles/{bundle_id}/files/single",
    status_code=200,
)
def post_bundle_files_single(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_CREATE)
    bundle = _get_project_bundle(bundle_id, project_id, db)
    _require_draft_status(bundle)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required",
        )

    content = file.file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is empty",
        )

    store = get_bundle_store()
    try:
        store.add_file(bundle.id, file.filename, content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    update_bundle(db, bundle.id, {"source_path": str(bundle.id)})
    return {"status": "ok"}


@router.delete(
    "/projects/{project_id}/bundles/{bundle_id}/files/{path:path}",
    status_code=200,
)
def delete_bundle_file(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_CREATE)
    bundle = _get_project_bundle(bundle_id, project_id, db)
    _require_draft_status(bundle)

    store = get_bundle_store()
    try:
        store.remove_file(bundle.id, path)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return {"status": "ok"}


@router.delete(
    "/projects/{project_id}/bundles/{bundle_id}/files",
    status_code=200,
)
def delete_bundle_files(
    project_id: uuid.UUID,
    bundle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_membership(db, current_user, project_id)
    _require_capability(current_user, Capability.BUNDLE_CREATE)
    bundle = _get_project_bundle(bundle_id, project_id, db)
    _require_draft_status(bundle)

    store = get_bundle_store()
    store.clear_contents(bundle.id)
    update_bundle(db, bundle.id, {"source_path": ""})
    return {"status": "ok"}
