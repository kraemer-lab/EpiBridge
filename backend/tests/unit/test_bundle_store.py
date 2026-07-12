import io
import uuid
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.services.bundle_store import (
    LocalFileSystemBundleStore,
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
        info.external_attr = 0o120777 << 16
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
    def test_excessive_uncompressed_size_rejected(self, store, tmp_path):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("small.py", b"x" * 1024)
            zf.writestr("run.py", b"print('hello')")
        content = buf.getvalue()

        with patch("app.services.bundle_store.BUNDLE_STORE_ROOT", tmp_path):
            with patch.object(store.__class__, "MAX_SIZE", 10 * 1024 * 1024):
                upload = _mock_upload(content)
                store.store(uuid.uuid4(), upload, "run.py")

    def test_empty_archive_rejected(self, store):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as _:
            pass
        upload = _mock_upload(buf.getvalue())
        with pytest.raises(ValueError, match="empty"):
            store.store(uuid.uuid4(), upload, "run.py")

    def test_empty_file_rejected(self, store):
        upload = _mock_upload(b"")
        with pytest.raises(ValueError, match="empty"):
            store.store(uuid.uuid4(), upload, "run.py")


class TestBundleStoreContentHash:
    def test_empty_store_returns_empty(self, store, tmp_path):
        with patch("app.services.bundle_store.BUNDLE_STORE_ROOT", tmp_path):
            h = store.get_content_hash(uuid.uuid4())
            assert h == ""

    def test_single_file_hash(self, store, tmp_path):
        bundle_id = uuid.uuid4()
        bundle_dir = tmp_path / str(bundle_id)
        bundle_dir.mkdir(parents=True)
        (bundle_dir / "run.py").write_text("print('hello')")
        with patch("app.services.bundle_store.BUNDLE_STORE_ROOT", tmp_path):
            h = store.get_content_hash(bundle_id)
            assert isinstance(h, str)
            assert len(h) == 64

    def test_same_content_produces_same_hash(self, store, tmp_path):
        with patch("app.services.bundle_store.BUNDLE_STORE_ROOT", tmp_path):
            id_a = uuid.uuid4()
            (tmp_path / str(id_a)).mkdir()
            (tmp_path / str(id_a) / "run.py").write_text("x")

            id_b = uuid.uuid4()
            (tmp_path / str(id_b)).mkdir()
            (tmp_path / str(id_b) / "run.py").write_text("x")

            assert store.get_content_hash(id_a) == store.get_content_hash(id_b)

    def test_different_content_produces_different_hash(self, store, tmp_path):
        with patch("app.services.bundle_store.BUNDLE_STORE_ROOT", tmp_path):
            id_a = uuid.uuid4()
            (tmp_path / str(id_a)).mkdir()
            (tmp_path / str(id_a) / "a.py").write_text("content_a")

            id_b = uuid.uuid4()
            (tmp_path / str(id_b)).mkdir()
            (tmp_path / str(id_b) / "b.py").write_text("content_b")

            assert store.get_content_hash(id_a) != store.get_content_hash(id_b)

    def test_multiple_files_sorted(self, store, tmp_path):
        bundle_id = uuid.uuid4()
        bundle_dir = tmp_path / str(bundle_id)
        bundle_dir.mkdir(parents=True)
        (bundle_dir / "z.py").write_text("last")
        (bundle_dir / "a.py").write_text("first")
        (bundle_dir / "m.py").write_text("middle")
        with patch("app.services.bundle_store.BUNDLE_STORE_ROOT", tmp_path):
            h = store.get_content_hash(bundle_id)
            assert isinstance(h, str)
            assert len(h) == 64
