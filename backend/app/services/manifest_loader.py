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
