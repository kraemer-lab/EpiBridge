"""Test the publication-boundary policy directly (no database required).

These tests verify that the publication service correctly distinguishes
between published artefacts (documentation, schemas, representative
datasets) and runtime data that must only be accessible through
authorised execution.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from app.services.resource_publication_service import (
    RUNTIME_DATA_PREFIX,
    is_published_artefact,
    list_published_artefacts,
)


class TestPublicationBoundaryPolicy:
    """Verify the policy logic that protects runtime data."""

    def test_runtime_data_prefix_explicit(self):
        assert RUNTIME_DATA_PREFIX == "data/"
        """The prefix makes the security boundary visible at a glance."""

    def test_is_published_artefact_rejects_data_paths(self):
        assert is_published_artefact("data/demo.csv") is False
        assert is_published_artefact("data/subdir/foo.csv") is False
        assert is_published_artefact("data/") is False

    def test_is_published_artefact_accepts_documentation(self):
        assert is_published_artefact("DOCUMENTATION.md") is True
        assert is_published_artefact("SCHEMA.md") is True

    def test_is_published_artefact_accepts_representative_data(self):
        assert is_published_artefact("representative/demo.csv") is True
        assert is_published_artefact("representative/sample.csv") is True

    def test_is_published_artefact_accepts_manifest(self):
        assert is_published_artefact("manifest.yaml") is True

    def test_is_published_artefact_accepts_other_artefacts(self):
        """Future directories like licences/, examples/ are accepted."""
        assert is_published_artefact("licences/MIT.txt") is True
        assert is_published_artefact("examples/usage.py") is True

    def test_list_published_artefacts_excludes_data_files(self):
        """Verify that list_published_artefacts filters out data/ paths."""
        resource = MagicMock()
        resource.identifier = "test-resource"

        with tempfile.TemporaryDirectory() as tmpdir:
            resource_dir = Path(tmpdir) / "test-resource"
            resource_dir.mkdir()

            (resource_dir / "DOCUMENTATION.md").write_text("# Docs")
            (resource_dir / "SCHEMA.md").write_text("# Schema")

            data_dir = resource_dir / "data"
            data_dir.mkdir()
            (data_dir / "demo.csv").write_text("secret,data\n")

            rep_dir = resource_dir / "representative"
            rep_dir.mkdir()
            (rep_dir / "demo.csv").write_text("sample,data\n")

            from app.core.config import settings

            original = settings.resource_manifest_dir
            settings.resource_manifest_dir = tmpdir
            try:
                published = list_published_artefacts(resource)

                assert "data/demo.csv" not in published
                assert "DOCUMENTATION.md" in published
                assert "SCHEMA.md" in published
                assert "representative/demo.csv" in published
            finally:
                settings.resource_manifest_dir = original
