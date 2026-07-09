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

    artefact_dirs = sorted(dir_path.glob("*/manifest.yaml"))
    if artefact_dirs:
        return _load_artefact_directory(dir_path, artefact_dirs)

    return _load_flat_environment_directory(dir_path)


def _validate_artefact_structure(artefact_dir: Path) -> None:
    dockerfile = artefact_dir / "Dockerfile"
    if not dockerfile.is_file():
        raise ValueError(
            f"Execution environment artefact directory {artefact_dir} "
            f"is missing required file: Dockerfile"
        )


def _load_artefact_directory(dir_path: Path, artefact_dirs: list[Path]) -> list[dict]:
    all_entries = []
    seen = set()

    for manifest_file in artefact_dirs:
        artefact_dir = manifest_file.parent
        with open(manifest_file) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(
                f"Manifest {manifest_file} must contain a top-level mapping"
            )

        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            msg = f"Missing required fields {missing} in {manifest_file}"
            raise ValueError(msg)

        identifier = data["identifier"]
        if identifier in seen:
            raise ValueError(
                f"Duplicate environment identifier '{identifier}' "
                f"across artefact directories"
            )
        seen.add(identifier)

        _validate_artefact_structure(artefact_dir)

        entry = {
            "identifier": identifier,
            "name": data["name"],
            "runtime": data["runtime"],
            "description": data.get("description", ""),
            "status": data.get("status", "active"),
            "image_reference": data.get("image_reference", ""),
            "definition_path": artefact_dir.name,
        }
        all_entries.append(entry)

    return all_entries


def _load_flat_environment_directory(dir_path: Path) -> list[dict]:
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
