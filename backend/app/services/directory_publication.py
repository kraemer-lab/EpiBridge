import mimetypes
from pathlib import Path
from typing import List

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.auth.dependencies import get_current_user


class PublicationEntry(BaseModel):
    identifier: str
    name: str
    description: str
    execution_environment_identifier: str | None = None
    data_resource_identifiers: list[str] = []
    entrypoint: str | None = None
    expected_outputs: list[str] = []


class ArtefactList(BaseModel):
    artefacts: list[str]


REQUIRED_FIELDS = {"identifier", "name"}


def _load_manifest(manifest_file: Path) -> dict:
    with open(manifest_file) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Manifest {manifest_file} must be a top-level mapping")
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ValueError(
            f"Missing required fields {sorted(missing)} in {manifest_file}"
        )
    identifier = data["identifier"]
    if identifier != manifest_file.parent.name:
        raise ValueError(
            f"Identifier '{identifier}' in {manifest_file} "
            f"must match directory name '{manifest_file.parent.name}'"
        )
    return data


class DirectoryPublication:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir).resolve()

    def list_items(
        self, environment: str | None = None, resource: str | None = None
    ) -> List[dict]:
        if not self.root_dir.is_dir():
            return []
        results = []
        for manifest_file in sorted(self.root_dir.glob("*/manifest.yaml")):
            try:
                data = _load_manifest(manifest_file)
            except (ValueError, yaml.YAMLError):
                continue
            entry = self._entry_from_manifest(data)
            if (
                environment
                and entry.get("execution_environment_identifier") != environment
            ):
                continue
            if resource and resource not in entry.get("data_resource_identifiers", []):
                continue
            results.append(entry)
        return results

    def get(self, identifier: str) -> dict | None:
        manifest_file = self.root_dir / identifier / "manifest.yaml"
        if not manifest_file.is_file():
            return None
        try:
            data = _load_manifest(manifest_file)
        except (ValueError, yaml.YAMLError):
            return None
        return self._entry_from_manifest(data)

    def list_artefacts(self, identifier: str) -> List[str]:
        artefact_dir = self.root_dir / identifier
        if not artefact_dir.is_dir():
            return []
        return sorted(
            f.name
            for f in artefact_dir.iterdir()
            if f.is_file() and f.name != "manifest.yaml"
        )

    def _entry_from_manifest(self, data: dict) -> dict:
        return {
            "identifier": data["identifier"],
            "name": data["name"],
            "description": data.get("description", ""),
            "execution_environment_identifier": data.get(
                "execution_environment_identifier"
            ),
            "data_resource_identifiers": data.get("data_resource_identifiers", []),
            "entrypoint": data.get("entrypoint"),
            "expected_outputs": data.get("expected_outputs", []),
        }

    def get_artefact_path(self, identifier: str, path: str) -> Path:
        artefact_root = (self.root_dir / identifier).resolve()
        if not artefact_root.is_dir():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Publication not found",
            )
        requested = (artefact_root / path).resolve()
        try:
            requested.relative_to(artefact_root)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Path traversal blocked",
            )
        if not requested.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artefact not found",
            )
        return requested


def create_publication_router(
    prefix: str,
    publication: DirectoryPublication,
) -> APIRouter:
    router = APIRouter(prefix=prefix, dependencies=[Depends(get_current_user)])

    @router.get("")
    def list_publications(
        environment: str | None = None,
        resource: str | None = None,
    ):
        return publication.list_items(environment=environment, resource=resource)

    @router.get("/{identifier}")
    def get_item(identifier: str):
        item = publication.get(identifier)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Publication not found",
            )
        return item

    @router.get("/{identifier}/artefacts", response_model=ArtefactList)
    def list_artefacts(identifier: str):
        files = publication.list_artefacts(identifier)
        return ArtefactList(artefacts=files)

    @router.get(
        "/{identifier}/artefacts/{path:path}",
        response_class=FileResponse,
    )
    def get_artefact(identifier: str, path: str):
        artefact_path = publication.get_artefact_path(identifier, path)
        media_type, _ = mimetypes.guess_type(str(artefact_path))
        if media_type is None:
            media_type = "application/octet-stream"
        return FileResponse(artefact_path, media_type=media_type)

    return router
