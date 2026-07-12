import uuid
from unittest.mock import MagicMock, patch

from app.models.analysis_bundle import AnalysisBundle
from app.services.validation_service import compute_execution_fingerprint


def _make_bundle(**kwargs) -> AnalysisBundle:
    bundle = MagicMock(spec=AnalysisBundle)
    bundle.id = kwargs.get("id", uuid.uuid4())
    bundle.execution_environment_id = kwargs.get("execution_environment_id")
    bundle.entrypoint = kwargs.get("entrypoint", "run.py")
    bundle.interpreter = kwargs.get("interpreter", "python")
    bundle.arguments = kwargs.get("arguments", "")
    bundle.build_strategy = kwargs.get("build_strategy", "institutional")
    bundle.data_resources = kwargs.get("data_resources", [])
    return bundle


class TestComputeExecutionFingerprint:
    def test_returns_deterministic_hash(self, tmp_path):
        bundle = _make_bundle()
        with patch("app.services.validation_service.get_bundle_store") as mock_store:
            store = MagicMock()
            store.get_content_hash.return_value = "abc123"
            mock_store.return_value = store

            h1 = compute_execution_fingerprint(bundle)
            h2 = compute_execution_fingerprint(bundle)
            assert h1 == h2
            assert isinstance(h1, str)
            assert len(h1) == 64  # SHA-256 hex digest

    def test_different_files_produce_different_hashes(self, tmp_path):
        bundle_a = _make_bundle()
        bundle_b = _make_bundle()
        with patch("app.services.validation_service.get_bundle_store") as mock_store:
            store_a = MagicMock()
            store_a.get_content_hash.return_value = "hash_a"
            store_b = MagicMock()
            store_b.get_content_hash.return_value = "hash_b"

            mock_store.side_effect = [store_a, store_b]
            h_a = compute_execution_fingerprint(bundle_a)
            h_b = compute_execution_fingerprint(bundle_b)
            assert h_a != h_b

    def test_different_config_produces_different_hash(self, tmp_path):
        with patch("app.services.validation_service.get_bundle_store") as mock_store:
            store = MagicMock()
            store.get_content_hash.return_value = "same_files"
            mock_store.return_value = store

            bundle_a = _make_bundle(entrypoint="run.py")
            bundle_b = _make_bundle(entrypoint="analyze.py")

            h_a = compute_execution_fingerprint(bundle_a)
            h_b = compute_execution_fingerprint(bundle_b)
            assert h_a != h_b

    def test_different_resource_ids_produce_different_hash(self, tmp_path):
        with patch("app.services.validation_service.get_bundle_store") as mock_store:
            store = MagicMock()
            store.get_content_hash.return_value = "same_files"
            mock_store.return_value = store

            dr1 = MagicMock()
            dr1.identifier = "resource-a"
            dr2 = MagicMock()
            dr2.identifier = "resource-b"

            bundle_a = _make_bundle(data_resources=[dr1])
            bundle_b = _make_bundle(data_resources=[dr2])

            h_a = compute_execution_fingerprint(bundle_a)
            h_b = compute_execution_fingerprint(bundle_b)
            assert h_a != h_b

    def test_resource_ids_are_sorted_deterministically(self, tmp_path):
        with patch("app.services.validation_service.get_bundle_store") as mock_store:
            store = MagicMock()
            store.get_content_hash.return_value = "same_files"
            mock_store.return_value = store

            dr1 = MagicMock()
            dr1.identifier = "resource-a"
            dr2 = MagicMock()
            dr2.identifier = "resource-b"

            bundle_a = _make_bundle(data_resources=[dr1, dr2])
            bundle_b = _make_bundle(data_resources=[dr2, dr1])

            h_a = compute_execution_fingerprint(bundle_a)
            h_b = compute_execution_fingerprint(bundle_b)
            assert h_a == h_b

    def test_excludes_metadata_fields(self, tmp_path):
        with patch("app.services.validation_service.get_bundle_store") as mock_store:
            store = MagicMock()
            store.get_content_hash.return_value = "same_files"
            mock_store.return_value = store

            bundle_a = _make_bundle(entrypoint="run.py")
            bundle_b = _make_bundle(entrypoint="run.py")

            h_a = compute_execution_fingerprint(bundle_a)
            h_b = compute_execution_fingerprint(bundle_b)
            assert h_a == h_b

    def test_includes_build_strategy(self, tmp_path):
        with patch("app.services.validation_service.get_bundle_store") as mock_store:
            store = MagicMock()
            store.get_content_hash.return_value = "same_files"
            mock_store.return_value = store

            bundle_a = _make_bundle(build_strategy="institutional")
            bundle_b = _make_bundle(build_strategy="custom")

            h_a = compute_execution_fingerprint(bundle_a)
            h_b = compute_execution_fingerprint(bundle_b)
            assert h_a != h_b

    def test_empty_bundle_returns_hash(self, tmp_path):
        bundle = _make_bundle()
        with patch("app.services.validation_service.get_bundle_store") as mock_store:
            store = MagicMock()
            store.get_content_hash.return_value = ""
            mock_store.return_value = store

            h = compute_execution_fingerprint(bundle)
            assert isinstance(h, str)
            assert len(h) == 64
