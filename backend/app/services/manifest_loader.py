from pathlib import Path

import yaml

REQUIRED_FIELDS = {"identifier", "name", "alias", "provider", "endpoint"}


def load_manifest(path: str | Path) -> list[dict]:
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    if not isinstance(data, dict) or "resources" not in data:
        msg = f"Manifest at {path} is missing top-level 'resources' key"
        raise ValueError(msg)

    resources = data["resources"]
    if not isinstance(resources, list):
        msg = f"Manifest at {path}: 'resources' must be a list"
        raise ValueError(msg)

    validated = []
    for i, entry in enumerate(resources):
        entry_path = f"{path}[{i}]"
        missing = REQUIRED_FIELDS - set(entry.keys())
        if missing:
            msg = f"{entry_path}: missing required fields: {', '.join(sorted(missing))}"
            raise ValueError(msg)

        if not isinstance(entry.get("endpoint"), dict):
            msg = f"{entry_path}: 'endpoint' must be a dict"
            raise ValueError(msg)

        validated.append(entry)

    return validated


def load_directory(dir_path: str | Path) -> list[dict]:
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        msg = f"Not a directory: {dir_path}"
        raise ValueError(msg)

    all_resources = []
    seen = set()

    for yaml_path in sorted(dir_path.glob("*.yaml")):
        entries = load_manifest(yaml_path)
        for entry in entries:
            ident = entry["identifier"]
            if ident in seen:
                msg = f"Duplicate identifier '{ident}' across manifests"
                raise ValueError(msg)
            seen.add(ident)
            all_resources.append(entry)

    return all_resources


def load_resource_directory(dir_path: str | Path) -> list[dict]:
    """Load resources from per-directory manifests mirroring EE pattern.

    Scans <dir>/*/manifest.yaml where each manifest is a single mapping
    (not a list under a 'resources' key). The directory name must match
    the resource identifier.
    """
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        msg = f"Not a directory: {dir_path}"
        raise ValueError(msg)

    manifest_files = sorted(dir_path.glob("*/manifest.yaml"))
    if not manifest_files:
        msg = f"No resource manifests found in {dir_path} (expected */manifest.yaml)"
        raise ValueError(msg)

    all_entries = []
    seen = set()

    for manifest_file in manifest_files:
        resource_dir = manifest_file.parent
        with open(manifest_file) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            msg = f"Manifest {manifest_file} must contain a top-level mapping"
            raise ValueError(msg)

        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            msg = f"Missing required fields {sorted(missing)} in {manifest_file}"
            raise ValueError(msg)

        if not isinstance(data.get("endpoint"), dict):
            msg = f"Manifest {manifest_file}: 'endpoint' must be a dict"
            raise ValueError(msg)

        identifier = data["identifier"]
        if identifier != resource_dir.name:
            msg = (
                f"Resource identifier '{identifier}' in {manifest_file} "
                f"must match directory name '{resource_dir.name}'"
            )
            raise ValueError(msg)

        if identifier in seen:
            msg = f"Duplicate resource identifier '{identifier}' across manifests"
            raise ValueError(msg)
        seen.add(identifier)

        entry = {
            "identifier": identifier,
            "name": data["name"],
            "alias": data["alias"],
            "provider": data["provider"],
            "endpoint": data["endpoint"],
            "description": data.get("description", ""),
            "version": data.get("version", "1.0.0"),
            "status": data.get("status", "active"),
        }
        all_entries.append(entry)

    return all_entries
