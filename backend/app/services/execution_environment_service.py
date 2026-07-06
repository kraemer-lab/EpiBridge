import uuid

from sqlalchemy.orm import Session

from app.models.execution_environment import ExecutionEnvironment

REQUIRED_FIELDS = {"identifier", "name", "runtime"}


def list_environments(
    db: Session, status: str | None = None
) -> list[ExecutionEnvironment]:
    query = db.query(ExecutionEnvironment).order_by(ExecutionEnvironment.name)
    if status:
        query = query.filter(ExecutionEnvironment.status == status)
    return query.all()


def get_environment(
    db: Session, environment_id: uuid.UUID
) -> ExecutionEnvironment | None:
    return (
        db.query(ExecutionEnvironment)
        .filter(ExecutionEnvironment.id == environment_id)
        .first()
    )


def get_environment_by_identifier(
    db: Session, identifier: str
) -> ExecutionEnvironment | None:
    return (
        db.query(ExecutionEnvironment)
        .filter(ExecutionEnvironment.identifier == identifier)
        .first()
    )


def validate_environment_entry(entry: dict) -> dict:
    missing = REQUIRED_FIELDS - set(entry.keys())
    if missing:
        msg = f"Missing required fields: {', '.join(sorted(missing))}"
        raise ValueError(msg)

    for field in ("identifier", "name", "runtime"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ValueError(f"'{field}' must be a non-empty string")

    return entry


def upsert_environment(db: Session, entry: dict) -> ExecutionEnvironment:
    validate_environment_entry(entry)

    existing = get_environment_by_identifier(db, entry["identifier"])

    if existing:
        existing.name = entry["name"]
        existing.runtime = entry["runtime"]
        existing.description = entry.get("description", "")
        existing.status = entry.get("status", "active")
        existing.image_reference = entry.get("image_reference", "")
        return existing

    env = ExecutionEnvironment(
        identifier=entry["identifier"],
        name=entry["name"],
        runtime=entry["runtime"],
        description=entry.get("description", ""),
        status=entry.get("status", "active"),
        image_reference=entry.get("image_reference", ""),
    )
    db.add(env)
    return env


def register_from_manifest(
    db: Session, manifest_entries: list[dict]
) -> list[ExecutionEnvironment]:
    results = []
    for entry in manifest_entries:
        env = upsert_environment(db, entry)
        results.append(env)
    db.commit()
    for env in results:
        db.refresh(env)
    return results
