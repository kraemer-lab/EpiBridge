import os
import tempfile
from pathlib import Path

import pytest
import yaml

from app.services.environment_manifest_loader import (
    load_environment_directory,
    load_environment_manifest,
)


def _make_yaml(path, data):
    Path(path).write_text(yaml.dump(data), encoding="utf-8")


class TestLoadEnvironmentManifest:
    def test_valid_manifest(self):
        data = {
            "environments": [
                {
                    "identifier": "python-3.14",
                    "name": "Python 3.14",
                    "runtime": "python-3.14",
                }
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            result = load_environment_manifest(path)
            assert len(result) == 1
            assert result[0]["identifier"] == "python-3.14"
            assert result[0]["runtime"] == "python-3.14"
        finally:
            os.unlink(path)

    def test_missing_environments_key(self):
        data = {"not_environments": []}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            with pytest.raises(ValueError, match="environments"):
                load_environment_manifest(path)
        finally:
            os.unlink(path)

    def test_environments_not_a_list(self):
        data = {"environments": "not a list"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            with pytest.raises(ValueError, match="list"):
                load_environment_manifest(path)
        finally:
            os.unlink(path)

    def test_missing_required_fields(self):
        data = {"environments": [{"identifier": "test-1"}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml.dump(data))
            path = f.name

        try:
            with pytest.raises(ValueError, match="required fields"):
                load_environment_manifest(path)
        finally:
            os.unlink(path)


class TestLoadEnvironmentDirectory:
    def test_load_flat_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_yaml(
                tmpdir + "/manifest.yaml",
                {
                    "environments": [
                        {
                            "identifier": "python-3.14",
                            "name": "Python 3.14",
                            "runtime": "python-3.14",
                        }
                    ]
                },
            )
            result = load_environment_directory(tmpdir)
            assert len(result) == 1
            assert result[0]["identifier"] == "python-3.14"
            assert "definition_path" not in result[0]

    def test_load_flat_multiple_manifests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_yaml(
                tmpdir + "/a.yaml",
                {
                    "environments": [
                        {
                            "identifier": "python-3.14",
                            "name": "Python 3.14",
                            "runtime": "python-3.14",
                        }
                    ]
                },
            )
            _make_yaml(
                tmpdir + "/b.yaml",
                {
                    "environments": [
                        {
                            "identifier": "conda",
                            "name": "Conda",
                            "runtime": "conda",
                        }
                    ]
                },
            )
            result = load_environment_directory(tmpdir)
            assert len(result) == 2
            assert {r["identifier"] for r in result} == {"python-3.14", "conda"}

    def test_load_artefact_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_dir = Path(tmpdir) / "python-3.14"
            env_dir.mkdir()
            _make_yaml(
                env_dir / "manifest.yaml",
                {
                    "identifier": "python-3.14",
                    "name": "Python 3.14",
                    "runtime": "python-3.14",
                },
            )
            (env_dir / "Dockerfile").write_text("FROM python:3.14-slim\n")

            result = load_environment_directory(tmpdir)
            assert len(result) == 1
            assert result[0]["identifier"] == "python-3.14"
            assert result[0]["definition_path"] == "python-3.14"

    def test_load_artefact_directory_multiple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("python-3.14", "conda"):
                env_dir = Path(tmpdir) / name
                env_dir.mkdir()
                _make_yaml(
                    env_dir / "manifest.yaml",
                    {
                        "identifier": name,
                        "name": name,
                        "runtime": name,
                    },
                )
                (env_dir / "Dockerfile").write_text("FROM scratch\n")

            result = load_environment_directory(tmpdir)
            assert len(result) == 2
            assert {r["identifier"] for r in result} == {"python-3.14", "conda"}
            for entry in result:
                assert entry["definition_path"] == entry["identifier"]

    def test_artefact_directory_missing_dockerfile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_dir = Path(tmpdir) / "python-3.14"
            env_dir.mkdir()
            _make_yaml(
                env_dir / "manifest.yaml",
                {
                    "identifier": "python-3.14",
                    "name": "Python 3.14",
                    "runtime": "python-3.14",
                },
            )

            with pytest.raises(ValueError, match="Dockerfile"):
                load_environment_directory(tmpdir)

    def test_artefact_directory_duplicate_identifier(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("python-3.14", "python-3.14"):
                env_dir = Path(tmpdir) / name
                if not env_dir.exists():
                    env_dir.mkdir()
            # Can't create duplicate directories with same name, so test
            # with two different dirs that claim the same identifier
            env_dir1 = Path(tmpdir) / "env-a"
            env_dir1.mkdir()
            _make_yaml(
                env_dir1 / "manifest.yaml",
                {
                    "identifier": "duplicate",
                    "name": "Duplicate",
                    "runtime": "python-3.14",
                },
            )
            (env_dir1 / "Dockerfile").write_text("FROM scratch\n")

            env_dir2 = Path(tmpdir) / "env-b"
            env_dir2.mkdir()
            _make_yaml(
                env_dir2 / "manifest.yaml",
                {
                    "identifier": "duplicate",
                    "name": "Duplicate Too",
                    "runtime": "python-3.14",
                },
            )
            (env_dir2 / "Dockerfile").write_text("FROM scratch\n")

            with pytest.raises(ValueError, match="Duplicate"):
                load_environment_directory(tmpdir)

    def test_not_a_directory(self):
        with pytest.raises(ValueError, match="Not a directory"):
            load_environment_directory("/nonexistent/path")

    def test_missing_required_fields_in_artefact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_dir = Path(tmpdir) / "test-env"
            env_dir.mkdir()
            _make_yaml(
                env_dir / "manifest.yaml",
                {"identifier": "test-env"},  # missing name, runtime
            )
            (env_dir / "Dockerfile").write_text("FROM scratch\n")

            with pytest.raises(ValueError, match="required fields"):
                load_environment_directory(tmpdir)
