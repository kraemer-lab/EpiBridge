import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policy import PolicyError, require_capability
from app.db.session import get_db
from app.models.analysis_bundle import AnalysisBundle
from app.models.audit_event import AuditEventType
from app.models.capability import Capability
from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.user import User
from app.schemas.analysis_bundle import AnalysisBundleRead
from app.schemas.audit_event import AuditEventList
from app.schemas.data_resource import DataResourceRead
from app.schemas.execution_environment import ExecutionEnvironmentRead
from app.schemas.execution_request import ExecutionRequestRead
from app.schemas.output import OutputRead
from app.schemas.output_set import OutputSetListItem, OutputSetRead
from app.schemas.user import UserCreate, UserRead
from app.services.analysis_bundle_service import (
    get_environment_runtime,
    get_resource_identifiers,
)
from app.services.audit_service import create_audit_event, query_audit_events
from app.services.execution_request_service import (
    get_execution_request,
    list_execution_requests,
    request_to_read,
)
from app.services.output_service import get_output
from app.services.output_set_service import (
    get_output_set,
    get_output_set_by_execution,
    list_output_sets,
    list_outputs_by_set,
)
from app.services.user_service import create_user, get_user_by_id, list_users
from app.workflow.bundle import approve_bundle, reject_bundle, supersede_bundle
from app.workflow.output_set import (
    approve_output_set,
    reject_output_set,
    release_output_set,
)

router = APIRouter()


@router.get("/admin/resources", response_model=List[DataResourceRead])
def list_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(DataResource).order_by(DataResource.name).all()


@router.get("/admin/resources/{resource_id}", response_model=DataResourceRead)
def get_resource(
    resource_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = db.query(DataResource).filter(DataResource.id == resource_id).first()
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    return resource


@router.get(
    "/admin/execution-environments",
    response_model=List[ExecutionEnvironmentRead],
)
def list_execution_environments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ExecutionEnvironment).order_by(ExecutionEnvironment.name).all()


@router.get(
    "/admin/execution-environments/{environment_id}",
    response_model=ExecutionEnvironmentRead,
)
def get_execution_environment(
    environment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    env = (
        db.query(ExecutionEnvironment)
        .filter(ExecutionEnvironment.id == environment_id)
        .first()
    )
    if env is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution environment not found",
        )
    return env


@router.get("/admin/bundles", response_model=List[AnalysisBundleRead])
def list_bundles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bundles = db.query(AnalysisBundle).order_by(AnalysisBundle.name).all()
    result = []
    for b in bundles:
        read = AnalysisBundleRead(
            id=b.id,
            project_id=b.project_id,
            created_by_id=b.created_by_id,
            execution_environment_id=b.execution_environment_id,
            name=b.name,
            source_path=b.source_path,
            status=b.status,
            runtime=get_environment_runtime(b),
            version=b.version,
            entrypoint=b.entrypoint,
            interpreter=b.interpreter,
            arguments=b.arguments,
            description=b.description,
            resource_identifiers=get_resource_identifiers(b),
            outputs=b.outputs,
            parameters=b.parameters,
            build_status=b.build_status,
            build_error=b.build_error,
            build_log="",
            created_at=b.created_at,
            updated_at=b.updated_at,
        )
        result.append(read)
    return result


@router.get("/admin/bundles/{bundle_id}", response_model=AnalysisBundleRead)
def get_bundle(
    bundle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bundle = db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        )
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
        build_log="",
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
    )


@router.get("/admin/execution-requests", response_model=List[ExecutionRequestRead])
def list_admin_execution_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    requests = list_execution_requests(db)
    return [request_to_read(r) for r in requests]


@router.get(
    "/admin/execution-requests/{request_id}",
    response_model=ExecutionRequestRead,
)
def get_admin_execution_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = get_execution_request(db, request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution request not found",
        )
    return request_to_read(request)


@router.get(
    "/admin/output-sets",
    response_model=List[OutputSetListItem],
)
def list_admin_output_sets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sets = list_output_sets(db)
    result: list[OutputSetListItem] = []
    for s in sets:
        req = s.execution_request
        result.append(
            OutputSetListItem(
                id=s.id,
                execution_request_id=s.execution_request_id,
                execution_request_name=req.name if req else "",
                status=s.status,
                file_count=len(s.outputs) if s.outputs else 0,
                release_package_size=s.release_package_size,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )
    return result


@router.get(
    "/admin/output-sets/{output_set_id}",
    response_model=OutputSetRead,
)
def get_admin_output_set(
    output_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    output_set = get_output_set(db, output_set_id)
    if output_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output set not found",
        )
    outputs = list_outputs_by_set(db, output_set.id)
    req = output_set.execution_request
    return OutputSetRead(
        id=output_set.id,
        execution_request_id=output_set.execution_request_id,
        execution_request_name=req.name if req else "",
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
    "/admin/execution-requests/{request_id}/outputs",
    response_model=OutputSetRead,
)
def list_admin_execution_request_outputs(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = get_execution_request(db, request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution request not found",
        )
    output_set = get_output_set_by_execution(db, request.id)
    if output_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output set not found",
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
    "/admin/outputs/{output_id}",
    response_model=OutputRead,
)
def get_admin_output(
    output_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    output = get_output(db, output_id)
    if output is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output not found",
        )
    return OutputRead(
        id=output.id,
        output_set_id=output.output_set_id,
        filename=output.filename,
        size=output.size,
        created_at=output.created_at,
    )


# --- Output Set governance (admin / moderator) ---


@router.post(
    "/admin/output-sets/{output_set_id}/approve",
    response_model=OutputSetRead,
)
def post_admin_approve_output_set(
    output_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    output_set = get_output_set(db, output_set_id)
    if output_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output set not found",
        )
    try:
        require_capability(current_user, Capability.OUTPUT_REVIEW)
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    try:
        approve_output_set(db, output_set)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    create_audit_event(
        db,
        event_type=AuditEventType.OUTPUT_SET_APPROVED,
        actor_id=current_user.id,
        project_id=output_set.execution_request.project_id,
        resource_type="output_set",
        resource_id=output_set.id,
        metadata={},
    )
    db.commit()
    db.refresh(output_set)
    req = output_set.execution_request
    outputs = list_outputs_by_set(db, output_set.id)
    return OutputSetRead(
        id=output_set.id,
        execution_request_id=output_set.execution_request_id,
        execution_request_name=req.name if req else "",
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


@router.post(
    "/admin/output-sets/{output_set_id}/reject",
    response_model=OutputSetRead,
)
def post_admin_reject_output_set(
    output_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    output_set = get_output_set(db, output_set_id)
    if output_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output set not found",
        )
    try:
        require_capability(current_user, Capability.OUTPUT_REVIEW)
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    try:
        reject_output_set(db, output_set)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    create_audit_event(
        db,
        event_type=AuditEventType.OUTPUT_SET_REJECTED,
        actor_id=current_user.id,
        project_id=output_set.execution_request.project_id,
        resource_type="output_set",
        resource_id=output_set.id,
        metadata={},
    )
    db.commit()
    db.refresh(output_set)
    req = output_set.execution_request
    outputs = list_outputs_by_set(db, output_set.id)
    return OutputSetRead(
        id=output_set.id,
        execution_request_id=output_set.execution_request_id,
        execution_request_name=req.name if req else "",
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


@router.post(
    "/admin/output-sets/{output_set_id}/release",
    response_model=OutputSetRead,
)
def post_admin_release_output_set(
    output_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    output_set = get_output_set(db, output_set_id)
    if output_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output set not found",
        )
    try:
        require_capability(current_user, Capability.OUTPUT_RELEASE)
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    try:
        release_output_set(db, output_set)
    except (ValueError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    create_audit_event(
        db,
        event_type=AuditEventType.OUTPUT_SET_RELEASED,
        actor_id=current_user.id,
        project_id=output_set.execution_request.project_id,
        resource_type="output_set",
        resource_id=output_set.id,
        metadata={
            "file_count": len(output_set.outputs) if output_set.outputs else 0,
            "total_size_bytes": output_set.release_package_size or 0,
        },
    )
    db.commit()
    db.refresh(output_set)
    req = output_set.execution_request
    outputs = list_outputs_by_set(db, output_set.id)
    return OutputSetRead(
        id=output_set.id,
        execution_request_id=output_set.execution_request_id,
        execution_request_name=req.name if req else "",
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


# --- User management ---


@router.get("/admin/users", response_model=List[UserRead])
def list_admin_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        require_capability(current_user, Capability.USER_MANAGE)
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    return list_users(db)


@router.get("/admin/users/{user_id}", response_model=UserRead)
def get_admin_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        require_capability(current_user, Capability.USER_MANAGE)
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.post("/admin/users", response_model=UserRead, status_code=201)
def post_admin_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        require_capability(current_user, Capability.USER_MANAGE)
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    existing = db.query(User).filter(User.email == data.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = create_user(
        db,
        email=data.email,
        display_name=data.display_name,
        password=data.password,
        role=data.role,
        actor_id=current_user.id,
    )
    return user


# --- Audit event query ---


@router.get("/admin/audit-events", response_model=AuditEventList)
def get_admin_audit_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_id: Optional[uuid.UUID] = Query(None),
    actor_id: Optional[uuid.UUID] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[uuid.UUID] = Query(None),
    event_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    try:
        require_capability(current_user, Capability.BUNDLE_REVIEW)
    except PolicyError:
        try:
            require_capability(current_user, Capability.OUTPUT_REVIEW)
        except PolicyError:
            try:
                require_capability(current_user, Capability.USER_MANAGE)
            except PolicyError as e:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(e),
                )

    items, total = query_audit_events(
        db,
        project_id=project_id,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        order=order,
    )
    return AuditEventList(items=items, total=total, limit=limit, offset=offset)


def _admin_bundle_to_read(bundle: AnalysisBundle) -> AnalysisBundleRead:
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
        build_log="",
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
        ai_review=None,
    )


def _get_admin_bundle(bundle_id: str, db: Session) -> AnalysisBundle:
    bundle = db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        )
    return bundle


@router.post(
    "/admin/bundles/{bundle_id}/approve",
    response_model=AnalysisBundleRead,
)
def post_admin_approve_bundle(
    bundle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bundle = _get_admin_bundle(bundle_id, db)
    try:
        require_capability(current_user, Capability.BUNDLE_REVIEW)
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    try:
        approve_bundle(db, bundle)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    create_audit_event(
        db,
        event_type=AuditEventType.BUNDLE_APPROVED,
        actor_id=current_user.id,
        project_id=bundle.project_id,
        resource_type="analysis_bundle",
        resource_id=bundle.id,
        metadata={"bundle_name": bundle.name},
    )
    db.commit()
    db.refresh(bundle)
    return _admin_bundle_to_read(bundle)


@router.post(
    "/admin/bundles/{bundle_id}/reject",
    response_model=AnalysisBundleRead,
)
def post_admin_reject_bundle(
    bundle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bundle = _get_admin_bundle(bundle_id, db)
    try:
        require_capability(current_user, Capability.BUNDLE_REVIEW)
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    try:
        reject_bundle(db, bundle)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    create_audit_event(
        db,
        event_type=AuditEventType.BUNDLE_REJECTED,
        actor_id=current_user.id,
        project_id=bundle.project_id,
        resource_type="analysis_bundle",
        resource_id=bundle.id,
        metadata={"bundle_name": bundle.name},
    )
    db.commit()
    db.refresh(bundle)
    return _admin_bundle_to_read(bundle)


@router.post(
    "/admin/bundles/{bundle_id}/supersede",
    response_model=AnalysisBundleRead,
)
def post_admin_supersede_bundle(
    bundle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bundle = _get_admin_bundle(bundle_id, db)
    try:
        if current_user.id != bundle.created_by_id:
            require_capability(current_user, Capability.BUNDLE_REVIEW)
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    try:
        supersede_bundle(db, bundle)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    create_audit_event(
        db,
        event_type=AuditEventType.BUNDLE_SUPERSEDED,
        actor_id=current_user.id,
        project_id=bundle.project_id,
        resource_type="analysis_bundle",
        resource_id=bundle.id,
        metadata={"bundle_name": bundle.name},
    )
    db.commit()
    db.refresh(bundle)
    return _admin_bundle_to_read(bundle)
