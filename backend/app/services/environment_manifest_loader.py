from pathlib import Path

import yaml

REQUIRED_FIELDS = {"identifier", "name", "runtime"}


def load_environment_manifest(path: str | Path) -> list[dict]:
    path = Path(path)
    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "environments" not in data:
        raise ValueError(f"Manifest {path} must contain top-level 'environments' key")

    entries = data["environments"]
    if not isinstance(entries, list):
        raise ValueError(f"'environments' in {path} must be a list")

    seen = set()
    for entry in entries:
        missing = REQUIRED_FIELDS - set(entry.keys())
        if missing:
            msg = f"Missing required fields {missing} in {path}"
            raise ValueError(msg)

        if entry["identifier"] in seen:
            raise ValueError(
                f"Duplicate environment identifier '{entry['identifier']}' in {path}"
            )
        seen.add(entry["identifier"])

    return entries


def load_environment_directory(dir_path: str | Path) -> list[dict]:
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {dir_path}")

    all_entries = []
    seen = set()

    for manifest_file in sorted(dir_path.glob("*.yaml")):
        entries = load_environment_manifest(manifest_file)
        for entry in entries:
            if entry["identifier"] in seen:
                raise ValueError(
                    f"Duplicate environment identifier '{entry['identifier']}' "
                    f"across manifests"
                )
            seen.add(entry["identifier"])
            all_entries.append(entry)

    return all_entries
