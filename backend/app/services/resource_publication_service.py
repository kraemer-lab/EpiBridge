from pathlib import Path

from app.core.config import settings
from app.models.data_resource import DataResource


def get_artefact_root(resource: DataResource) -> Path:
    return Path(settings.resource_manifest_dir) / resource.identifier


def list_artefact_files(resource: DataResource) -> list[str]:
    root = get_artefact_root(resource)
    if not root.is_dir():
        return []
    return sorted(f.name for f in root.iterdir() if f.is_file())
