import uuid

from sqlalchemy.orm import Session

from app.models.analysis_bundle import (
    AnalysisBundle,
    AnalysisBundleDataResource,
    AnalysisBundleStatus,
)
from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.project_data_resource import ProjectResourceAllocation

REQUIRED_MANIFEST_FIELDS = {
    "name",
    "execution_environment_id",
    "version",
    "entrypoint",
}


def validate_manifest(data: dict) -> dict:
    missing = REQUIRED_MANIFEST_FIELDS - set(data.keys())
    if missing:
        msg = f"Missing required fields: {', '.join(sorted(missing))}"
        raise ValueError(msg)

    if not isinstance(data.get("name"), str) or not data["name"].strip():
        raise ValueError("'name' must be a non-empty string")

    if "source_path" in data and not isinstance(data["source_path"], str):
        raise ValueError("'source_path' must be a string")

    ee_id = data.get("execution_environment_id")
    if isinstance(ee_id, str):
        try:
            uuid.UUID(ee_id)
        except ValueError:
            raise ValueError("'execution_environment_id' must be a valid UUID")
    elif not isinstance(ee_id, uuid.UUID):
        raise ValueError("'execution_environment_id' must be a valid UUID")

    if not isinstance(data.get("version"), str) or not data["version"].strip():
        raise ValueError("'version' must be a non-empty string")

    if not isinstance(data.get("entrypoint"), str) or not data["entrypoint"].strip():
        raise ValueError("'entrypoint' must be a non-empty string")

    resources = data.get("resource_identifiers", [])
    if not isinstance(resources, list):
        raise ValueError("'resource_identifiers' must be a list")

    outputs = data.get("outputs", [])
    if not isinstance(outputs, list):
        raise ValueError("'outputs' must be a list")

    if "parameters" in data and not isinstance(data["parameters"], dict):
        raise ValueError("'parameters' must be a dict")

    return data


def validate_entrypoint(entrypoint: str) -> None:
    if not entrypoint or not entrypoint.strip():
        raise ValueError("Entrypoint must not be empty")
    if "/" in entrypoint or "\\" in entrypoint:
        raise ValueError("Entrypoint must be a filename, not a path")


def validate_resources(
    resource_identifiers: list[str], project_id: uuid.UUID, db: Session
) -> list[DataResource]:
    if not resource_identifiers:
        return []

    resources = (
        db.query(DataResource)
        .filter(DataResource.identifier.in_(resource_identifiers))
        .all()
    )

    found = {r.identifier for r in resources}
    missing = set(resource_identifiers) - found
    if missing:
        sorted_missing = ", ".join(sorted(missing))
        msg = f"Referenced Data Resources not found: {sorted_missing}"
        raise ValueError(msg)

    allocated = (
        db.query(ProjectResourceAllocation.data_resource_id)
        .filter(
            ProjectResourceAllocation.project_id == project_id,
            ProjectResourceAllocation.data_resource_id.in_([r.id for r in resources]),
            ProjectResourceAllocation.revoked_at.is_(None),
        )
        .all()
    )
    allocated_ids = {a[0] for a in allocated}
    unallocated = [r for r in resources if r.id not in allocated_ids]
    if unallocated:
        names = ", ".join(sorted(r.identifier for r in unallocated))
        msg = f"Data Resources not allocated to this project: {names}"
        raise ValueError(msg)

    return resources


def validate_execution_environment(
    execution_environment_id: uuid.UUID, db: Session
) -> ExecutionEnvironment:
    env = (
        db.query(ExecutionEnvironment)
        .filter(ExecutionEnvironment.id == execution_environment_id)
        .first()
    )
    if env is None:
        raise ValueError(f"Execution environment not found: {execution_environment_id}")
    return env


def create_bundle(
    db: Session,
    data: dict,
    project_id: uuid.UUID,
    created_by_id: uuid.UUID,
) -> AnalysisBundle:
    validate_manifest(data)
    validate_entrypoint(data["entrypoint"])
    resources = validate_resources(data.get("resource_identifiers", []), project_id, db)

    ee_id = data["execution_environment_id"]
    if isinstance(ee_id, str):
        ee_id = uuid.UUID(ee_id)
    validate_execution_environment(ee_id, db)

    bundle = AnalysisBundle(
        project_id=project_id,
        created_by_id=created_by_id,
        execution_environment_id=ee_id,
        name=data["name"],
        version=data["version"],
        entrypoint=data["entrypoint"],
        interpreter=data.get("interpreter", "python"),
        arguments=data.get("arguments", ""),
        source_path=data.get("source_path", ""),
        description=data.get("description", ""),
        outputs=data.get("outputs", []),
        parameters=data.get("parameters", {}),
    )
    db.add(bundle)
    db.flush()

    for resource in resources:
        join = AnalysisBundleDataResource(
            analysis_bundle_id=bundle.id,
            data_resource_id=resource.id,
        )
        db.add(join)

    db.commit()
    db.refresh(bundle)
    return bundle


def get_resource_identifiers(bundle: AnalysisBundle) -> list[str]:
    return [
        dr.identifier
        for dr in sorted(bundle.data_resources, key=lambda r: r.identifier)
    ]


def get_environment_runtime(bundle: AnalysisBundle) -> str:
    if bundle.execution_environment:
        return bundle.execution_environment.runtime
    return ""


def update_bundle(db: Session, bundle_id: uuid.UUID, data: dict) -> AnalysisBundle:
    bundle = db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
    if bundle is None:
        raise ValueError("Analysis bundle not found")

    update_data = {k: v for k, v in data.items() if v is not None}

    if "name" in update_data:
        if not isinstance(update_data["name"], str) or not update_data["name"].strip():
            raise ValueError("'name' must be a non-empty string")
        bundle.name = update_data["name"]

    if "execution_environment_id" in update_data:
        ee_id = update_data["execution_environment_id"]
        if isinstance(ee_id, str):
            ee_id = uuid.UUID(ee_id)
        if not isinstance(ee_id, uuid.UUID):
            raise ValueError("'execution_environment_id' must be a valid UUID")
        validate_execution_environment(ee_id, db)
        bundle.execution_environment_id = ee_id

    if "version" in update_data:
        if (
            not isinstance(update_data["version"], str)
            or not update_data["version"].strip()
        ):
            raise ValueError("'version' must be a non-empty string")
        bundle.version = update_data["version"]

    if "entrypoint" in update_data:
        if (
            not isinstance(update_data["entrypoint"], str)
            or not update_data["entrypoint"].strip()
        ):
            raise ValueError("'entrypoint' must be a non-empty string")
        validate_entrypoint(update_data["entrypoint"])
        bundle.entrypoint = update_data["entrypoint"]

    if "source_path" in update_data:
        if not isinstance(update_data["source_path"], str):
            raise ValueError("'source_path' must be a string")
        bundle.source_path = update_data["source_path"]

    if "description" in update_data:
        bundle.description = update_data["description"]

    if "outputs" in update_data:
        if not isinstance(update_data["outputs"], list):
            raise ValueError("'outputs' must be a list")
        bundle.outputs = update_data["outputs"]

    if "parameters" in update_data:
        if not isinstance(update_data["parameters"], dict):
            raise ValueError("'parameters' must be a dict")
        bundle.parameters = update_data["parameters"]

    if "status" in update_data:
        if not isinstance(update_data["status"], AnalysisBundleStatus):
            raise ValueError("'status' must be a valid AnalysisBundleStatus")
        bundle.status = update_data["status"]

    if "resource_identifiers" in update_data:
        resources = validate_resources(
            update_data["resource_identifiers"], bundle.project_id, db
        )
        db.query(AnalysisBundleDataResource).filter(
            AnalysisBundleDataResource.analysis_bundle_id == bundle.id
        ).delete()
        for resource in resources:
            join = AnalysisBundleDataResource(
                analysis_bundle_id=bundle.id,
                data_resource_id=resource.id,
            )
            db.add(join)

    db.commit()
    db.refresh(bundle)
    return bundle
