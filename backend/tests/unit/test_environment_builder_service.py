import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.models.analysis_bundle import AnalysisBundle
from app.models.build_request import BuildRequestStatus
from app.models.execution_environment import ExecutionEnvironment
from app.services.environment_builder_service import (
    ensure_build_request,
    get_cached_image,
    resolve_builder_for_bundle,
)


def _make_bundle(env_id=None, runtime="python-3.13"):
    env = ExecutionEnvironment(
        identifier="test-env",
        name="Test",
        runtime=runtime,
    )
    env.id = env_id or uuid.uuid4()
    bundle = AnalysisBundle(
        execution_environment_id=env.id,
    )
    bundle.id = uuid.uuid4()
    bundle.execution_environment = env
    return bundle


class TestGetCachedImage:
    def test_returns_none_when_missing(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = get_cached_image(db, uuid.uuid4(), "a" * 64)
        assert result is None

    def test_returns_image_when_found(self):
        db = MagicMock()
        img = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = img
        result = get_cached_image(db, uuid.uuid4(), "a" * 64)
        assert result is img


class TestResolveBuilderForBundle:
    def test_python_runtime(self):
        bundle = _make_bundle(runtime="python-3.13")
        builder = resolve_builder_for_bundle(bundle)
        assert builder.identifier() == "python"

    def test_unknown_runtime_returns_none(self):
        bundle = _make_bundle(runtime="unknown-1.0")
        assert resolve_builder_for_bundle(bundle) is None

    def test_no_environment_returns_none(self):
        bundle = AnalysisBundle()
        assert resolve_builder_for_bundle(bundle) is None


class TestEnsureBuildRequest:
    @patch("app.services.environment_builder_service.get_bundle_store")
    def test_cache_hit_returns_none(self, mock_get_store):
        mock_store = MagicMock()

        import tempfile

        bundle_dir = Path(tempfile.mkdtemp())
        (bundle_dir / "requirements.txt").write_text("")
        mock_store.get_path.return_value = bundle_dir
        mock_get_store.return_value = mock_store

        db = MagicMock()

        existing = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            existing,
        ]

        bundle = _make_bundle()
        with patch.object(bundle.execution_environment, "runtime", "python-3.13"):
            result = ensure_build_request(db, bundle)

        assert result is None

    @patch("app.services.environment_builder_service.get_bundle_store")
    def test_cache_miss_creates_build_request(self, mock_get_store):
        mock_store = MagicMock()

        import tempfile

        bundle_dir = Path(tempfile.mkdtemp())
        (bundle_dir / "requirements.txt").write_text("numpy")

        mock_store.get_path.return_value = bundle_dir
        mock_get_store.return_value = mock_store

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            None,
        ]

        bundle = _make_bundle()
        with patch.object(bundle.execution_environment, "runtime", "python-3.13"):
            result = ensure_build_request(db, bundle)

        assert result is not None
        assert result.analysis_bundle_id == bundle.id
        assert result.builder_type == "python"
        assert result.status == BuildRequestStatus.PENDING
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @patch("app.services.environment_builder_service.get_bundle_store")
    def test_missing_requirements_creates_build_request(self, mock_get_store):
        mock_store = MagicMock()

        import tempfile

        bundle_dir = Path(tempfile.mkdtemp())
        mock_store.get_path.return_value = bundle_dir
        mock_get_store.return_value = mock_store

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            None,
        ]

        bundle = _make_bundle()
        with patch.object(bundle.execution_environment, "runtime", "python-3.13"):
            result = ensure_build_request(db, bundle)

        assert result is not None
        assert result.builder_type == "python"

    @patch("app.services.environment_builder_service.get_bundle_store")
    def test_no_builder_returns_none(self, mock_get_store):
        bundle = _make_bundle(runtime="unknown-1.0")
        result = ensure_build_request(MagicMock(), bundle)
        assert result is None
