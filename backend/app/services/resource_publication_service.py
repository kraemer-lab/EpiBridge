from pathlib import Path

from app.core.config import settings
from app.models.data_resource import DataResource

# Publication boundary: files under this prefix contain runtime datasets
# and must only be accessed through authorised execution, never served
# through the publication API.  This enforces the institutional governance
# model: real data reaches researchers only via released analysis outputs.
RUNTIME_DATA_PREFIX = "data/"


def get_artefact_root(resource: DataResource) -> Path:
    return Path(settings.resource_manifest_dir) / resource.identifier


def is_published_artefact(path: str) -> bool:
    """Return True if the artefact path is a published resource artefact
    (documentation, schema, representative dataset, etc.) rather than
    runtime data that must be protected by the execution governance model.

    The convention is that ``data/`` contains runtime datasets and is
    excluded from publication.  This is the publication-boundary policy.
    """
    return not path.startswith(RUNTIME_DATA_PREFIX)


def list_artefact_files(resource: DataResource) -> list[str]:
    root = get_artefact_root(resource)
    if not root.is_dir():
        return []
    return sorted(str(f.relative_to(root)) for f in root.rglob("*") if f.is_file())


def list_published_artefacts(resource: DataResource) -> list[str]:
    """Like list_artefact_files but filtered to published artefacts only,
    excluding runtime data that must not be exposed through the API.
    """
    return [f for f in list_artefact_files(resource) if is_published_artefact(f)]
