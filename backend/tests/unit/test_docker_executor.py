from unittest.mock import MagicMock, patch

import pytest

from app.execution.docker import DockerExecutor
from app.execution.util import parse_exit_code


class TestParseExitCode:
    def test_legacy_int(self):
        assert parse_exit_code(0) == 0
        assert parse_exit_code(1) == 1
        assert parse_exit_code(42) == 42

    def test_dict(self):
        assert parse_exit_code({"StatusCode": 0}) == 0
        assert parse_exit_code({"StatusCode": 1}) == 1
        assert parse_exit_code({"StatusCode": 42}) == 42

    def test_dict_missing_key(self):
        with pytest.raises(RuntimeError, match="without integer StatusCode"):
            parse_exit_code({})

    def test_dict_non_int_value(self):
        with pytest.raises(RuntimeError, match="without integer StatusCode"):
            parse_exit_code({"StatusCode": "oops"})

    def test_none(self):
        with pytest.raises(RuntimeError, match="Unexpected container wait result type"):
            parse_exit_code(None)

    def test_list(self):
        with pytest.raises(RuntimeError, match="Unexpected container wait result type"):
            parse_exit_code([0])


@patch("app.execution.docker.docker")
class TestDockerExecutorHardening:
    def test_container_created_with_security_options(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.images.get.return_value = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = 0
        mock_container.logs.return_value = b""
        mock_container.get_archive.return_value = ([], None)

        executor = DockerExecutor(client=mock_client)
        with (
            patch.object(executor, "_put_directory"),
            patch.object(executor, "_extract_output"),
        ):
            executor.run(
                image="test:latest",
                analysis_dir=__import__("pathlib").Path("/tmp"),
                command=["python", "run.py"],
                mounts=[],
                output_dir=__import__("pathlib").Path("/tmp/out"),
                timeout=60,
                env={},
            )

        kwargs = mock_client.containers.create.call_args.kwargs
        assert kwargs.get("cap_drop") == ["ALL"]
        assert (
            kwargs.get("read_only") is not True
        )  # intentionally not set (see docker.py note)
        assert kwargs.get("security_opt") == ["no-new-privileges:true"]
        assert "tmpfs" in kwargs
        assert "/tmp" in kwargs["tmpfs"]
        assert "/output" not in kwargs["tmpfs"]
        assert kwargs.get("network_disabled") is True

    def test_container_created_with_resource_limits(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.images.get.return_value = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = 0
        mock_container.logs.return_value = b""
        mock_container.get_archive.return_value = ([], None)

        executor = DockerExecutor(client=mock_client)
        with (
            patch.object(executor, "_put_directory"),
            patch.object(executor, "_extract_output"),
        ):
            executor.run(
                image="test:latest",
                analysis_dir=__import__("pathlib").Path("/tmp"),
                command=["python", "run.py"],
                mounts=[],
                output_dir=__import__("pathlib").Path("/tmp/out"),
                timeout=60,
                env={},
            )

        kwargs = mock_client.containers.create.call_args.kwargs
        assert "mem_limit" in kwargs
        assert "nano_cpus" in kwargs
        assert "pids_limit" in kwargs

    def test_container_runs_as_nonroot(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.images.get.return_value = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = 0
        mock_container.logs.return_value = b""
        mock_container.get_archive.return_value = ([], None)

        executor = DockerExecutor(client=mock_client)
        with (
            patch.object(executor, "_put_directory"),
            patch.object(executor, "_extract_output"),
        ):
            executor.run(
                image="test:latest",
                analysis_dir=__import__("pathlib").Path("/tmp"),
                command=["python", "run.py"],
                mounts=[],
                output_dir=__import__("pathlib").Path("/tmp/out"),
                timeout=60,
                env={},
            )

        kwargs = mock_client.containers.create.call_args.kwargs
        assert kwargs.get("user") == "nobody"
        assert kwargs.get("network_disabled") is True

    def test_data_mounts_are_read_only(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.images.get.return_value = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.create.return_value = mock_container
        mock_container.wait.return_value = 0
        mock_container.logs.return_value = b""
        mock_container.get_archive.return_value = ([], None)

        executor = DockerExecutor(client=mock_client)
        with (
            patch.object(executor, "_put_directory"),
            patch.object(executor, "_extract_output"),
        ):
            executor.run(
                image="test:latest",
                analysis_dir=__import__("pathlib").Path("/tmp"),
                command=["python", "run.py"],
                mounts=[("/data/source.csv", "/data/target.csv", True)],
                output_dir=__import__("pathlib").Path("/tmp/out"),
                timeout=60,
                env={},
            )

        volumes = mock_client.containers.create.call_args.kwargs["volumes"]
        assert "/data/source.csv" in volumes
        assert volumes["/data/source.csv"]["mode"] == "ro"
