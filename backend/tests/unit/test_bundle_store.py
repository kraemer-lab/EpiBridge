import io
import uuid
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.services.bundle_store import (
    BUNDLE_STORE_ROOT,
    LocalFileSystemBundleStore,
    get_bundle_store,
)


@pytest.fixture
def store():
    return LocalFileSystemBundleStore()


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _make_zip_with_symlink(target_name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("evil_link")
        info.external_attr = (0o120777 << 16)
        zf.writestr(info, "/etc/passwd")
        zf.writestr("run.py", "print('hello')")
    return buf.getvalue()


def _mock_upload(content: bytes) -> MagicMock:
    upload = MagicMock()
    upload.file.read.return_value = content
    return upload


class TestBundleStoreContentValidation:
    def test_content_based_zip_validation(self, store):
        not_a_zip = b"this is not a zip file"
        upload = _mock_upload(not_a_zip)
        with pytest.raises(ValueError, match="Invalid ZIP"):
            store.store(uuid.uuid4(), upload, "run.py")

    def test_path_traversal_rejected(self, store):
        content = _make_zip({"../etc/passwd": b"root:x", "run.py": b"ok"})
        upload = _mock_upload(content)
        with pytest.raises(ValueError, match="Path traversal"):
            store.store(uuid.uuid4(), upload, "run.py")

    def test_absolute_path_rejected(self, store):
        content = _make_zip({"/etc/passwd": b"root:x", "run.py": b"ok"})
        upload = _mock_upload(content)
        with pytest.raises(ValueError, match="Path traversal"):
            store.store(uuid.uuid4(), upload, "run.py")

    def test_symlink_rejected(self, store):
        content = _make_zip_with_symlink("evil_link")
        upload = _mock_upload(content)
        with pytest.raises(ValueError, match="Symlinks"):
            store.store(uuid.uuid4(), upload, "run.py")


class TestBundleStoreDecompressionBomb:
    def test_excessive_uncompressed_size_rejected(self, store):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("small.py", b"x" * 1024)
            zf.writestr("run.py", b"print('hello')")
        content = buf.getvalue()

        with patch.object(store.__class__, "MAX_SIZE", 10 * 1024 * 1024):
            upload = _mock_upload(content)
            store.store(uuid.uuid4(), upload, "run.py")

    def test_empty_archive_rejected(self, store):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            pass
        upload = _mock_upload(buf.getvalue())
        with pytest.raises(ValueError, match="empty"):
            store.store(uuid.uuid4(), upload, "run.py")

    def test_empty_file_rejected(self, store):
        upload = _mock_upload(b"")
        with pytest.raises(ValueError, match="empty"):
            store.store(uuid.uuid4(), upload, "run.py")
