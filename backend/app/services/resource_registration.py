from sqlalchemy.orm import Session

from app.models.data_resource import DataResource
from app.providers.registry import registry
from app.providers.types import ProviderType


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


def register_from_manifest(
    db: Session, manifest_entries: list[dict]
) -> list[DataResource]:
    registered = []
    for entry in manifest_entries:
        resource = upsert_resource(db, entry)
        registered.append(resource)
    db.commit()
    for resource in registered:
        db.refresh(resource)
    return registered
