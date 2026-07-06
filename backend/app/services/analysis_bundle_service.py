import uuid

from sqlalchemy.orm import Session

from app.models.analysis_bundle import AnalysisBundle, AnalysisBundleDataResource
from app.models.data_resource import DataResource

REQUIRED_MANIFEST_FIELDS = {"name", "runtime", "version", "entrypoint"}


def validate_manifest(data: dict) -> dict:
    missing = REQUIRED_MANIFEST_FIELDS - set(data.keys())
    if missing:
        msg = f"Missing required fields: {', '.join(sorted(missing))}"
        raise ValueError(msg)

    if not isinstance(data.get("name"), str) or not data["name"].strip():
        raise ValueError("'name' must be a non-empty string")

    if not isinstance(data.get("runtime"), str) or not data["runtime"].strip():
        raise ValueError("'runtime' must be a non-empty string")

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
    resource_identifiers: list[str], db: Session
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

    return resources


def create_bundle(
    db: Session,
    data: dict,
    project_id: uuid.UUID,
    created_by_id: uuid.UUID,
) -> AnalysisBundle:
    validate_manifest(data)
    validate_entrypoint(data["entrypoint"])
    resources = validate_resources(data.get("resource_identifiers", []), db)

    bundle = AnalysisBundle(
        project_id=project_id,
        created_by_id=created_by_id,
        name=data["name"],
        runtime=data["runtime"],
        version=data["version"],
        entrypoint=data["entrypoint"],
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


def update_bundle(db: Session, bundle_id: uuid.UUID, data: dict) -> AnalysisBundle:
    bundle = db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
    if bundle is None:
        raise ValueError("Analysis bundle not found")

    update_data = {k: v for k, v in data.items() if v is not None}

    if "name" in update_data:
        if not isinstance(update_data["name"], str) or not update_data["name"].strip():
            raise ValueError("'name' must be a non-empty string")
        bundle.name = update_data["name"]

    if "runtime" in update_data:
        if (
            not isinstance(update_data["runtime"], str)
            or not update_data["runtime"].strip()
        ):
            raise ValueError("'runtime' must be a non-empty string")
        bundle.runtime = update_data["runtime"]

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

    if "resource_identifiers" in update_data:
        resources = validate_resources(update_data["resource_identifiers"], db)
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
