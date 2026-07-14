import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policy import PolicyError, require_capability
from app.db.session import get_db
from app.models.analysis_bundle import AnalysisBundle
from app.models.audit_event import AuditEventType
from app.models.build_request import BuildRequest
from app.models.capability import Capability
from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.platform_setting import SettingKey
from app.models.user import User
from app.schemas.ai_bundle_review import AIBundleReviewRead
from app.schemas.analysis_bundle import AnalysisBundleRead
from app.schemas.audit_event import AuditEventList
from app.schemas.data_resource import DataResourceRead
from app.schemas.execution_environment import ExecutionEnvironmentAdminRead
from app.schemas.execution_request import ExecutionRequestRead
from app.schemas.output import OutputRead
from app.schemas.output_set import OutputSetListItem, OutputSetRead
from app.schemas.platform_setting import PlatformSettingRead, PlatformSettingUpdate
from app.schemas.terms import TermsOfServicePublish, TermsOfServiceRead
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.analysis_bundle_service import (
    get_environment_runtime,
    get_resource_identifiers,
)
from app.services.audit_service import create_audit_event, query_audit_events
from app.services.bundle_store import get_bundle_store
from app.services.execution_request_service import (
    get_execution_request,
    list_execution_requests,
    request_to_read,
)
from app.services.notification_triggers import trigger_output_released_notifications
from app.services.output_service import get_output
from app.services.output_set_service import (
    get_output_set,
    get_output_set_by_execution,
    list_output_sets,
    list_outputs_by_set,
)
from app.services.platform_settings_service import (
    get_all_settings,
    set_setting,
)
from app.services.terms_service import (
    get_acceptance_counts,
    get_current_platform_terms,
    publish_platform_terms,
    publish_resource_terms,
)
from app.services.user_service import (
    create_user,
    get_user_by_id,
    list_users,
    update_user,
)
from app.workflow.bundle import approve_bundle, reject_bundle, supersede_bundle
from app.workflow.output_set import (
    approve_output_set,
    reject_output_set,
    release_output_set,
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


def _require_any_capability(current_user: User, capabilities: list[Capability]) -> None:
    for cap in capabilities:
        try:
            require_capability(current_user, cap)
            return
        except PolicyError:
            continue
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden",
    )


@router.get("/admin/resources", response_model=List[DataResourceRead])
def list_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.DATA_MANAGE)
    return db.query(DataResource).order_by(DataResource.name).all()


@router.get("/admin/resources/{resource_id}", response_model=DataResourceRead)
def get_resource(
    resource_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.DATA_MANAGE)
    resource = db.query(DataResource).filter(DataResource.id == resource_id).first()
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    return resource


@router.get(
    "/admin/execution-environments",
    response_model=List[ExecutionEnvironmentAdminRead],
)
def list_execution_environments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.ENVIRONMENT_MANAGE)
    return db.query(ExecutionEnvironment).order_by(ExecutionEnvironment.name).all()


@router.get(
    "/admin/execution-environments/{environment_id}",
    response_model=ExecutionEnvironmentAdminRead,
)
def get_execution_environment(
    environment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.ENVIRONMENT_MANAGE)
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


def _check_admin_view(current_user: User) -> None:
    """Allow access if user has any governance or admin capability."""
    for cap in (
        Capability.BUNDLE_REVIEW,
        Capability.OUTPUT_REVIEW,
        Capability.USER_MANAGE,
    ):
        try:
            require_capability(current_user, cap)
            return
        except PolicyError:
            continue
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _build_log_for_bundle(db: Session, bundle_id: uuid.UUID) -> str:
    latest = (
        db.query(BuildRequest)
        .filter(BuildRequest.analysis_bundle_id == bundle_id)
        .order_by(BuildRequest.created_at.desc())
        .first()
    )
    return latest.log if latest is not None else ""


@router.get("/admin/bundles", response_model=List[AnalysisBundleRead])
def list_bundles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin_view(current_user)
    bundles = db.query(AnalysisBundle).order_by(AnalysisBundle.name).all()
    result = []
    for b in bundles:
        ai_review_read = (
            AIBundleReviewRead.model_validate(b.ai_review)
            if b.ai_review is not None
            else None
        )
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
            build_strategy=b.build_strategy,
            build_status=b.build_status,
            build_error=b.build_error,
            build_log=_build_log_for_bundle(db, b.id),
            created_at=b.created_at,
            updated_at=b.updated_at,
            ai_review=ai_review_read,
        )
        result.append(read)
    return result


@router.get("/admin/bundles/{bundle_id}", response_model=AnalysisBundleRead)
def get_bundle(
    bundle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin_view(current_user)
    bundle = db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        )
    ai_review_read = (
        AIBundleReviewRead.model_validate(bundle.ai_review)
        if bundle.ai_review is not None
        else None
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
        build_strategy=bundle.build_strategy,
        build_status=bundle.build_status,
        build_error=bundle.build_error,
        build_log=_build_log_for_bundle(db, bundle.id),
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
        ai_review=ai_review_read,
    )


@router.get("/admin/bundles/{bundle_id}/files")
def get_admin_bundle_files(
    bundle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin_view(current_user)
    bundle = _get_admin_bundle(bundle_id, db)
    store = get_bundle_store()
    files = store.list_files(bundle.id)
    return {
        "files": files,
        "total_size": store.get_total_size(bundle.id),
    }


MAX_PREVIEW_SIZE = 1024 * 1024

_TEXT_EXTENSIONS = frozenset(
    {
        ".py",
        ".r",
        ".R",
        ".sh",
        ".js",
        ".ipynb",
        ".txt",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".cfg",
        ".ini",
        ".conf",
        ".xml",
        ".html",
        ".css",
        ".ts",
        ".tsx",
        ".jsx",
        ".sql",
        ".csv",
        ".tsv",
    }
)


@router.get("/admin/bundles/{bundle_id}/files/{path:path}")
def get_admin_bundle_file(
    bundle_id: str,
    path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin_view(current_user)
    bundle = _get_admin_bundle(bundle_id, db)
    store = get_bundle_store()
    try:
        content = store.read_file(bundle.id, path)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    if len(content) > MAX_PREVIEW_SIZE:
        msg = (
            f"File too large to preview ({len(content)} bytes, "
            f"max {MAX_PREVIEW_SIZE} bytes)"
        )
        return Response(content=msg, media_type="text/plain", status_code=413)
    ext = Path(path).suffix
    if ext in _TEXT_EXTENSIONS:
        try:
            text = content.decode("utf-8")
            return PlainTextResponse(text)
        except UnicodeDecodeError:
            return Response(
                content=f"Binary file — {len(content)} bytes — preview unavailable",
                media_type="text/plain",
            )
    return Response(
        content=f"Binary file — {len(content)} bytes — preview unavailable",
        media_type="text/plain",
    )


@router.get("/admin/execution-requests", response_model=List[ExecutionRequestRead])
def list_admin_execution_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin_view(current_user)
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
    _check_admin_view(current_user)
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
    _require_capability(current_user, Capability.OUTPUT_REVIEW)
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
    _require_capability(current_user, Capability.OUTPUT_REVIEW)
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
    _require_capability(current_user, Capability.OUTPUT_REVIEW)
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
    _require_capability(current_user, Capability.OUTPUT_REVIEW)
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
    _require_capability(current_user, Capability.OUTPUT_REVIEW)
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
    _require_capability(current_user, Capability.OUTPUT_REVIEW)
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    output_set = get_output_set(db, output_set_id)
    if output_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output set not found",
        )
    _require_capability(current_user, Capability.OUTPUT_RELEASE)
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

    trigger_output_released_notifications(
        db,
        output_set=output_set,
        releaser=current_user,
        background_tasks=background_tasks,
    )

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
    _require_any_capability(
        current_user, [Capability.USER_MANAGE, Capability.USER_READ]
    )
    return list_users(db)


@router.get("/admin/users/{user_id}", response_model=UserRead)
def get_admin_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_any_capability(
        current_user, [Capability.USER_MANAGE, Capability.USER_READ]
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
    _require_capability(current_user, Capability.USER_MANAGE)

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
        roles=data.roles,
        actor_id=current_user.id,
    )
    return user


@router.put("/admin/users/{user_id}", response_model=UserRead)
def put_admin_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.USER_MANAGE)

    updated = update_user(
        db,
        user_id=user_id,
        display_name=data.display_name,
        password=data.password,
        roles=data.roles,
        advanced_capabilities=data.advanced_capabilities,
        actor_id=current_user.id,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return updated


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
    _check_admin_view(current_user)

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


def _admin_bundle_to_read(
    bundle: AnalysisBundle, db: Session | None = None
) -> AnalysisBundleRead:
    ai_review_read = (
        AIBundleReviewRead.model_validate(bundle.ai_review)
        if bundle.ai_review is not None
        else None
    )
    build_log = ""
    if db is not None:
        build_log = _build_log_for_bundle(db, bundle.id)
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
        ai_review=ai_review_read,
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
    _require_capability(current_user, Capability.BUNDLE_REVIEW)
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
    return _admin_bundle_to_read(bundle, db=db)


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
    _require_capability(current_user, Capability.BUNDLE_REVIEW)
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
    return _admin_bundle_to_read(bundle, db=db)


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
    if current_user.id != bundle.created_by_id:
        _require_capability(current_user, Capability.BUNDLE_REVIEW)
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
    return _admin_bundle_to_read(bundle, db=db)


@router.get("/admin/settings", response_model=dict[str, str])
def get_admin_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.SETTINGS_MANAGE)
    return get_all_settings(db)


@router.put("/admin/settings/{key}", response_model=PlatformSettingRead)
def put_admin_setting(
    key: SettingKey,
    body: PlatformSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.SETTINGS_MANAGE)
    return set_setting(db, key, body.value)


@router.post(
    "/admin/terms/platform",
    response_model=TermsOfServiceRead,
    status_code=201,
)
def post_admin_publish_platform_terms(
    body: TermsOfServicePublish,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.TERMS_MANAGE)
    return publish_platform_terms(
        db,
        published_by=current_user,
        title=body.title,
        content=body.content,
        version=body.version,
    )


@router.post(
    "/admin/resources/{resource_id}/terms/publish",
    response_model=TermsOfServiceRead,
    status_code=201,
)
def post_admin_publish_resource_terms(
    resource_id: uuid.UUID,
    body: TermsOfServicePublish,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.TERMS_MANAGE)
    try:
        return publish_resource_terms(
            db,
            published_by=current_user,
            data_resource_id=resource_id,
            title=body.title,
            content=body.content,
            version=body.version,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/admin/terms/status")
def get_admin_terms_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_capability(current_user, Capability.TERMS_MANAGE)
    from app.models.terms_of_service import TermsOfService

    counts = get_acceptance_counts(db)
    current_platform = get_current_platform_terms(db)

    all_platform_terms = (
        db.query(TermsOfService)
        .filter(TermsOfService.terms_type == "platform")
        .order_by(TermsOfService.published_at.desc())
        .all()
    )

    def _version_entry(terms):
        return {
            "id": str(terms.id),
            "version": terms.version,
            "title": terms.title,
            "published_at": terms.published_at.isoformat()
            if terms.published_at
            else None,
            "acceptance_count": counts.get(terms.id, 0),
        }

    platform_history = [_version_entry(t) for t in all_platform_terms]

    resource_ids = [
        row[0]
        for row in db.query(TermsOfService.data_resource_id)
        .filter(
            TermsOfService.terms_type == "data_resource",
            TermsOfService.data_resource_id.isnot(None),
        )
        .distinct()
        .all()
    ]

    resource_terms_list = []
    for rid in resource_ids:
        resource = db.query(DataResource).filter(DataResource.id == rid).first()
        all_resource_terms = (
            db.query(TermsOfService)
            .filter(
                TermsOfService.terms_type == "data_resource",
                TermsOfService.data_resource_id == rid,
            )
            .order_by(TermsOfService.published_at.desc())
            .all()
        )
        resource_terms_list.append(
            {
                "resource_id": str(rid),
                "resource_name": resource.name if resource else "Unknown",
                "current": _version_entry(all_resource_terms[0])
                if all_resource_terms
                else None,
                "history": [_version_entry(t) for t in all_resource_terms],
            }
        )

    return {
        "platform": {
            "current": _version_entry(current_platform) if current_platform else None,
            "history": platform_history,
        },
        "resource_terms": resource_terms_list,
    }
