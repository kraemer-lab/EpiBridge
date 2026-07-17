from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.data_resource import DataResource
from app.providers.registry import registry
from app.providers.types import ProviderType


@dataclass
class RegisterResult:
    created: list[DataResource]
    skipped: list[str]
    errors: list[str]


def upsert_resource(db: Session, entry: dict) -> DataResource:
    provider_type = ProviderType(entry["provider"])
    provider = registry.get(provider_type)
    endpoint = provider.validate_endpoint(entry["endpoint"])

    existing = (
        db.query(DataResource)
        .filter(DataResource.identifier == entry["identifier"])
        .first()
    )

    if existing is not None:
        existing.name = entry["name"]
        existing.alias = entry["alias"]
        existing.endpoint = endpoint
        existing.description = entry.get("description", "")
        existing.version = entry.get("version", "1.0.0")
        existing.status = entry.get("status", "active")
        existing.provider_type = provider_type.value
        return existing

    resource = DataResource(
        identifier=entry["identifier"],
        name=entry["name"],
        alias=entry["alias"],
        provider_type=provider_type.value,
        endpoint=endpoint,
        description=entry.get("description", ""),
        version=entry.get("version", "1.0.0"),
        status=entry.get("status", "active"),
    )
    db.add(resource)
    return resource


def register_resource(db: Session, entry: dict) -> RegisterResult:
    created: list[DataResource] = []
    skipped: list[str] = []
    errors: list[str] = []

    try:
        exists = (
            db.query(DataResource.id)
            .filter(DataResource.identifier == entry["identifier"])
            .first()
        )
        if exists is not None:
            return RegisterResult(created=[], skipped=[entry["identifier"]], errors=[])

        provider_type = ProviderType(entry["provider"])
        provider = registry.get(provider_type)
        endpoint = provider.validate_endpoint(entry["endpoint"])

        resource = DataResource(
            identifier=entry["identifier"],
            name=entry["name"],
            alias=entry["alias"],
            provider_type=provider_type.value,
            endpoint=endpoint,
            description=entry.get("description", ""),
            version=entry.get("version", "1.0.0"),
            status=entry.get("status", "active"),
        )
        db.add(resource)
        db.flush()
        db.refresh(resource)
        created.append(resource)
    except Exception as e:
        errors.append(f"{entry['identifier']}: {e}")

    return RegisterResult(created=created, skipped=skipped, errors=errors)


def register_from_manifest(db: Session, manifest_entries: list[dict]) -> RegisterResult:
    result = RegisterResult(created=[], skipped=[], errors=[])
    for entry in manifest_entries:
        r = register_resource(db, entry)
        result.created.extend(r.created)
        result.skipped.extend(r.skipped)
        result.errors.extend(r.errors)
    if result.created:
        db.commit()
    return result
