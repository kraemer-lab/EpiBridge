from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policy import PolicyError, require_any_role
from app.db.session import get_db
from app.models.analysis_bundle import AnalysisBundle
from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.output import Output
from app.models.user import User, UserRole
from app.schemas.analysis_bundle import AnalysisBundleRead
from app.schemas.data_resource import DataResourceRead
from app.schemas.execution_environment import ExecutionEnvironmentRead
from app.schemas.execution_request import ExecutionRequestRead
from app.schemas.output import OutputRead
from app.services.analysis_bundle_service import (
    get_environment_runtime,
    get_resource_identifiers,
)
from app.services.execution_request_service import (
    get_execution_request,
    list_execution_requests,
    request_to_read,
)
from app.services.output_service import get_output, list_outputs
from app.workflow.bundle import approve_bundle, reject_bundle, supersede_bundle
from app.workflow.output import approve_output, reject_output, release_output

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
    "/admin/outputs",
    response_model=List[OutputRead],
)
def list_admin_outputs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Output).order_by(Output.created_at.desc()).all()


@router.get(
    "/admin/execution-requests/{request_id}/outputs",
    response_model=List[OutputRead],
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
    return list_outputs(db, request.id)


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
    return output


@router.post(
    "/admin/outputs/{output_id}/approve",
    response_model=OutputRead,
)
def post_admin_approve_output(
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
    try:
        require_any_role(
            current_user, UserRole.MODERATOR, UserRole.MAINTAINER, UserRole.ADMIN
        )
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    try:
        approve_output(db, output)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    db.commit()
    db.refresh(output)
    return output


@router.post(
    "/admin/outputs/{output_id}/reject",
    response_model=OutputRead,
)
def post_admin_reject_output(
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
    try:
        require_any_role(
            current_user, UserRole.MODERATOR, UserRole.MAINTAINER, UserRole.ADMIN
        )
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    try:
        reject_output(db, output)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    db.commit()
    db.refresh(output)
    return output


@router.post(
    "/admin/outputs/{output_id}/release",
    response_model=OutputRead,
)
def post_admin_release_output(
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
    try:
        require_any_role(
            current_user, UserRole.MODERATOR, UserRole.MAINTAINER, UserRole.ADMIN
        )
    except PolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    try:
        release_output(db, output)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    db.commit()
    db.refresh(output)
    return output


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
        require_any_role(
            current_user, UserRole.MODERATOR, UserRole.MAINTAINER, UserRole.ADMIN
        )
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
        require_any_role(
            current_user, UserRole.MODERATOR, UserRole.MAINTAINER, UserRole.ADMIN
        )
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
            require_any_role(
                current_user,
                UserRole.MODERATOR,
                UserRole.MAINTAINER,
                UserRole.ADMIN,
            )
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
    db.commit()
    db.refresh(bundle)
    return _admin_bundle_to_read(bundle)
