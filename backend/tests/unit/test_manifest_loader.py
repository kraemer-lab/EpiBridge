import os
import tempfile
from pathlib import Path

import pytest
import yaml

from app.services.manifest_loader import load_directory, load_manifest


def _make_yaml(path, data):
    Path(path).write_text(yaml.dump(data), encoding="utf-8")


class TestLoadManifest:
    def test_valid_manifest(self):
        data = {
            "resources": [
                {
                    "identifier": "test-1",
                    "name": "Test One",
                    "alias": "test_one",
                    "provider": "csv",
                    "endpoint": {"path": "data.csv"},
                }
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            result = load_manifest(path)
            assert len(result) == 1
            assert result[0]["identifier"] == "test-1"
            assert result[0]["alias"] == "test_one"
        finally:
            os.unlink(path)

    def test_missing_resources_key(self):
        data = {"not_resources": []}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            with pytest.raises(ValueError, match="resources"):
                load_manifest(path)
        finally:
            os.unlink(path)

    def test_resources_not_a_list(self):
        data = {"resources": "not a list"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            with pytest.raises(ValueError, match="list"):
                load_manifest(path)
        finally:
            os.unlink(path)

    def test_missing_required_fields(self):
        data = {"resources": [{"identifier": "test-1", "name": "Incomplete"}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            with pytest.raises(ValueError, match="required fields"):
                load_manifest(path)
        finally:
            os.unlink(path)

    def test_endpoint_not_a_dict(self):
        data = {
            "resources": [
                {
                    "identifier": "test-1",
                    "name": "Bad Endpoint",
                    "alias": "bad",
                    "provider": "csv",
                    "endpoint": "not a dict",
                }
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            with pytest.raises(ValueError, match="endpoint.*dict"):
                load_manifest(path)
        finally:
            os.unlink(path)

    def test_description_version_status_defaults(self):
        data = {
            "resources": [
                {
                    "identifier": "test-1",
                    "name": "Minimal",
                    "alias": "minimal",
                    "provider": "csv",
                    "endpoint": {"path": "data.csv"},
                }
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            result = load_manifest(path)
            assert len(result) == 1
            assert "description" not in result[0]
            assert "version" not in result[0]
        finally:
            os.unlink(path)


class TestLoadDirectory:
    def test_load_single_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_yaml(
                tmpdir + "/manifest.yaml",
                {
                    "resources": [
                        {
                            "identifier": "a",
                            "name": "A",
                            "alias": "a",
                            "provider": "csv",
                            "endpoint": {"path": "a.csv"},
                        }
                    ]
                },
            )
            result = load_directory(tmpdir)
            assert len(result) == 1
            assert result[0]["identifier"] == "a"

    def test_load_multiple_manifests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_yaml(
                tmpdir + "/a.yaml",
                {
                    "resources": [
                        {
                            "identifier": "a",
                            "name": "A",
                            "alias": "a",
                            "provider": "csv",
                            "endpoint": {"path": "a.csv"},
                        }
                    ]
                },
            )
            _make_yaml(
                tmpdir + "/b.yaml",
                {
                    "resources": [
                        {
                            "identifier": "b",
                            "name": "B",
                            "alias": "b",
                            "provider": "csv",
                            "endpoint": {"path": "b.csv"},
                        }
                    ]
                },
            )
            result = load_directory(tmpdir)
            assert len(result) == 2
            assert {r["identifier"] for r in result} == {"a", "b"}

    def test_duplicate_identifier_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_yaml(
                tmpdir + "/a.yaml",
                {
                    "resources": [
                        {
                            "identifier": "dup",
                            "name": "First",
                            "alias": "first",
                            "provider": "csv",
                            "endpoint": {"path": "a.csv"},
                        }
                    ]
                },
            )
            _make_yaml(
                tmpdir + "/b.yaml",
                {
                    "resources": [
                        {
                            "identifier": "dup",
                            "name": "Second",
                            "alias": "second",
                            "provider": "csv",
                            "endpoint": {"path": "b.csv"},
                        }
                    ]
                },
            )
            with pytest.raises(ValueError, match="Duplicate"):
                load_directory(tmpdir)

    def test_not_a_directory(self):
        with pytest.raises(ValueError, match="Not a directory"):
            load_directory("/nonexistent/path")
