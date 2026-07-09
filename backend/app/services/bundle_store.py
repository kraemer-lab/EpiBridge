import io
import os
import shutil
import stat
import uuid
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

BUNDLE_STORE_ROOT = Path(settings.bundle_store_dir)
MAX_DECOMPRESSED_SIZE = 500 * 1024 * 1024


class BundleStore(ABC):
    @abstractmethod
    def store(
        self, bundle_id: uuid.UUID, archive: UploadFile, entrypoint: str
    ) -> str: ...

    @abstractmethod
    def get_path(self, bundle_id: uuid.UUID) -> Path: ...

    @abstractmethod
    def delete(self, bundle_id: uuid.UUID) -> None: ...


class LocalFileSystemBundleStore(BundleStore):
    MAX_SIZE = 100 * 1024 * 1024

    def store(self, bundle_id: uuid.UUID, archive: UploadFile, entrypoint: str) -> str:
        store_path = BUNDLE_STORE_ROOT / str(bundle_id)
        if store_path.exists():
            raise ValueError(f"Bundle already exists: {bundle_id}")

        content = archive.file.read()
        if len(content) > self.MAX_SIZE:
            raise ValueError(
                f"Archive exceeds maximum size of {self.MAX_SIZE // (1024 * 1024)} MB"
            )
        if len(content) == 0:
            raise ValueError("Archive is empty")

        try:
            zf = zipfile.ZipFile(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Invalid ZIP archive: {e}")

        entries = zf.infolist()
        if not entries:
            raise ValueError("ZIP archive is empty (no entries)")

        has_files = any(not zi.is_dir() for zi in entries)
        if not has_files:
            raise ValueError("ZIP archive contains only directories, no files")

        total_uncompressed = 0
        for zi in entries:
            name = zi.filename
            cleaned = os.path.normpath(name)
            if cleaned != name:
                raise ValueError(f"Path traversal detected: {name}")
            if name.startswith("/") or name.startswith("..") or os.path.isabs(name):
                raise ValueError(f"Path traversal detected: {name}")

            external_attr = zi.external_attr >> 16
            if stat.S_ISLNK(external_attr):
                raise ValueError(f"Symlinks are not allowed in bundles: {name}")

            total_uncompressed += zi.file_size
            if total_uncompressed > MAX_DECOMPRESSED_SIZE:
                raise ValueError(
                    f"Archive too large when decompressed "
                    f"(exceeds {MAX_DECOMPRESSED_SIZE // (1024 * 1024)} MB)"
                )

        store_path.mkdir(parents=True, exist_ok=True)
        try:
            zf.extractall(path=str(store_path))
        except Exception as e:
            shutil.rmtree(store_path, ignore_errors=True)
            raise ValueError(f"Failed to extract archive: {e}")

        entrypoint_path = store_path / entrypoint
        if not entrypoint_path.exists() or not entrypoint_path.is_file():
            shutil.rmtree(store_path, ignore_errors=True)
            raise ValueError(f"Entrypoint '{entrypoint}' not found in uploaded bundle")

        return str(bundle_id)

    def get_path(self, bundle_id: uuid.UUID) -> Path:
        return BUNDLE_STORE_ROOT / str(bundle_id)

    def delete(self, bundle_id: uuid.UUID) -> None:
        store_path = self.get_path(bundle_id)
        if store_path.exists():
            shutil.rmtree(store_path)


_bundle_store: BundleStore | None = None


def get_bundle_store() -> BundleStore:
    global _bundle_store
    if _bundle_store is None:
        BUNDLE_STORE_ROOT.mkdir(parents=True, exist_ok=True)
        _bundle_store = LocalFileSystemBundleStore()
    return _bundle_store
