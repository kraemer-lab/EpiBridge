import hashlib
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

    @abstractmethod
    def list_files(self, bundle_id: uuid.UUID) -> list[dict]: ...

    @abstractmethod
    def replace_contents(self, bundle_id: uuid.UUID, archive: UploadFile) -> str: ...

    @abstractmethod
    def import_archive(self, bundle_id: uuid.UUID, archive: UploadFile) -> str: ...

    @abstractmethod
    def add_file(self, bundle_id: uuid.UUID, filename: str, content: bytes) -> None: ...

    @abstractmethod
    def remove_file(self, bundle_id: uuid.UUID, path: str) -> None: ...

    @abstractmethod
    def clear_contents(self, bundle_id: uuid.UUID) -> None: ...

    @abstractmethod
    def get_total_size(self, bundle_id: uuid.UUID) -> int: ...

    @abstractmethod
    def get_content_hash(self, bundle_id: uuid.UUID) -> str: ...


class LocalFileSystemBundleStore(BundleStore):
    MAX_SIZE = 100 * 1024 * 1024

    def store(self, bundle_id: uuid.UUID, archive: UploadFile, entrypoint: str) -> str:
        store_path = self.get_path(bundle_id)
        if store_path.exists():
            raise ValueError(f"Bundle already exists: {bundle_id}")

        zf = self._read_and_validate_zip(archive)
        self._extract_zip(zf, store_path)

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

    def list_files(self, bundle_id: uuid.UUID) -> list[dict]:
        store_path = self.get_path(bundle_id)
        if not store_path.is_dir():
            return []
        files = []
        for root, dirs, filenames in os.walk(store_path):
            for fname in filenames:
                fpath = Path(root) / fname
                relative = str(fpath.relative_to(store_path))
                files.append(
                    {
                        "path": relative,
                        "size": fpath.stat().st_size,
                    }
                )
        files.sort(key=lambda f: f["path"])
        return files

    def replace_contents(self, bundle_id: uuid.UUID, archive: UploadFile) -> str:
        store_path = self.get_path(bundle_id)
        zf = self._read_and_validate_zip(archive)
        if store_path.exists():
            shutil.rmtree(store_path)
        self._extract_zip(zf, store_path)
        return str(bundle_id)

    def import_archive(self, bundle_id: uuid.UUID, archive: UploadFile) -> str:
        store_path = self.get_path(bundle_id)
        if not store_path.is_dir():
            store_path.mkdir(parents=True, exist_ok=True)
        zf = self._read_and_validate_zip(archive)

        current_size = self._current_dir_size(store_path)
        accumulated = current_size
        for zi in zf.infolist():
            if not zi.is_dir():
                accumulated += zi.file_size
                if accumulated > MAX_DECOMPRESSED_SIZE:
                    raise ValueError(
                        f"Import would exceed maximum decompressed size of "
                        f"{MAX_DECOMPRESSED_SIZE // (1024 * 1024)} MB"
                    )

        try:
            zf.extractall(path=str(store_path))
        except Exception as e:
            raise ValueError(f"Failed to extract archive: {e}")
        return str(bundle_id)

    def add_file(self, bundle_id: uuid.UUID, filename: str, content: bytes) -> None:
        store_path = self.get_path(bundle_id)
        if not store_path.is_dir():
            store_path.mkdir(parents=True, exist_ok=True)

        cleaned = os.path.normpath(filename)
        if cleaned != filename:
            raise ValueError(f"Invalid filename: {filename}")
        if (
            filename.startswith("/")
            or filename.startswith("..")
            or os.path.isabs(filename)
        ):
            raise ValueError(f"Invalid filename: {filename}")

        target = (store_path / filename).resolve()
        if not str(target).startswith(str(store_path.resolve())):
            raise ValueError(f"Path traversal detected: {filename}")

        target.parent.mkdir(parents=True, exist_ok=True)
        current_size = self._current_dir_size(store_path)
        if current_size + len(content) > MAX_DECOMPRESSED_SIZE:
            raise ValueError(
                f"Adding file would exceed maximum size of "
                f"{MAX_DECOMPRESSED_SIZE // (1024 * 1024)} MB"
            )
        target.write_bytes(content)

    def remove_file(self, bundle_id: uuid.UUID, path: str) -> None:
        store_path = self.get_path(bundle_id)
        cleaned = os.path.normpath(path)
        target = (store_path / cleaned).resolve()
        if not str(target).startswith(str(store_path.resolve())):
            raise ValueError(f"Path traversal detected: {path}")
        if not target.exists():
            raise ValueError(f"File not found: {path}")
        if not target.is_file():
            raise ValueError(f"Not a file: {path}")
        target.unlink()

    def clear_contents(self, bundle_id: uuid.UUID) -> None:
        store_path = self.get_path(bundle_id)
        if store_path.exists():
            shutil.rmtree(store_path)
            store_path.mkdir(parents=True, exist_ok=True)

    def get_total_size(self, bundle_id: uuid.UUID) -> int:
        return self._current_dir_size(self.get_path(bundle_id))

    def get_content_hash(self, bundle_id: uuid.UUID) -> str:
        store_path = self.get_path(bundle_id)
        if not store_path.is_dir():
            return ""
        hasher = hashlib.sha256()
        files = sorted(f for f in store_path.rglob("*") if f.is_file())
        for fpath in files:
            relative = str(fpath.relative_to(store_path))
            hasher.update(relative.encode())
            hasher.update(fpath.read_bytes())
        return hasher.hexdigest()

    def _read_and_validate_zip(self, archive: UploadFile) -> zipfile.ZipFile:
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
            self._validate_zip_entry(zi)
            total_uncompressed += zi.file_size
            if total_uncompressed > MAX_DECOMPRESSED_SIZE:
                raise ValueError(
                    f"Archive too large when decompressed "
                    f"(exceeds {MAX_DECOMPRESSED_SIZE // (1024 * 1024)} MB)"
                )

        return zf

    def _validate_zip_entry(self, zi: zipfile.ZipInfo) -> None:
        name = zi.filename
        cleaned = os.path.normpath(name)
        if cleaned != name:
            raise ValueError(f"Path traversal detected: {name}")
        if name.startswith("/") or name.startswith("..") or os.path.isabs(name):
            raise ValueError(f"Path traversal detected: {name}")

        external_attr = zi.external_attr >> 16
        if stat.S_ISLNK(external_attr):
            raise ValueError(f"Symlinks are not allowed in bundles: {name}")

    def _extract_zip(self, zf: zipfile.ZipFile, target_path: Path) -> None:
        target_path.mkdir(parents=True, exist_ok=True)
        try:
            zf.extractall(path=str(target_path))
        except Exception as e:
            shutil.rmtree(target_path, ignore_errors=True)
            raise ValueError(f"Failed to extract archive: {e}")

    @staticmethod
    def _current_dir_size(path: Path) -> int:
        if not path.is_dir():
            return 0
        total = 0
        for root, dirs, files in os.walk(path):
            for fname in files:
                fpath = Path(root) / fname
                total += fpath.stat().st_size
        return total


_bundle_store: BundleStore | None = None


def get_bundle_store() -> BundleStore:
    global _bundle_store
    if _bundle_store is None:
        BUNDLE_STORE_ROOT.mkdir(parents=True, exist_ok=True)
        _bundle_store = LocalFileSystemBundleStore()
    return _bundle_store
