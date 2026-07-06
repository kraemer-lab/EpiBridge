import io
import os
import tarfile
from pathlib import Path

import docker
from docker.errors import ImageNotFound

from app.execution.base import ExecutionResult, Executor
from app.execution.util import parse_exit_code

NONROOT_USER = "nobody"
WORKDIR = "/work"
ANALYSIS_TARGET = "/analysis"
OUTPUT_TARGET = "/output"


class DockerExecutor(Executor):
    def __init__(
        self,
        client: docker.DockerClient | None = None,
        mount_remap: dict[str, str] | None = None,
    ):
        self._client = client or docker.from_env()
        self._mount_remap = mount_remap or {}

    def _remap_source(self, source: str) -> str:
        for prefix, replacement in self._mount_remap.items():
            if source.startswith(prefix):
                return replacement + source[len(prefix) :]
        return source

    def run(
        self,
        *,
        image: str,
        analysis_dir: Path,
        entrypoint: str,
        mounts: list[tuple[str, str, bool]],
        output_dir: Path,
        timeout: int,
        env: dict[str, str],
    ) -> ExecutionResult:
        try:
            self._client.images.get(image)
        except ImageNotFound:
            self._client.images.pull(image)

        output_dir.mkdir(parents=True, exist_ok=True)
        output_dir.chmod(0o777)

        volume_bindings = {}
        for source, target, read_only in mounts:
            mode = "ro" if read_only else "rw"
            volume_bindings[self._remap_source(source)] = {"bind": target, "mode": mode}
        container = self._client.containers.create(
            image,
            entrypoint=["python", f"{ANALYSIS_TARGET}/{entrypoint}"],
            network_disabled=True,
            working_dir=WORKDIR,
            user=NONROOT_USER,
            volumes=volume_bindings,
            environment=env,
        )

        self._put_directory(container, analysis_dir, ANALYSIS_TARGET)

        container.start()

        try:
            wait_result = container.wait(timeout=timeout)
            exit_code = parse_exit_code(wait_result)
        except docker.errors.TimeoutError:
            container.stop()
            container.remove()
            raise TimeoutError(f"Execution timed out after {timeout} seconds")

        stdout = (container.logs(stdout=True, stderr=False) or b"").decode()
        stderr = (container.logs(stdout=False, stderr=True) or b"").decode()

        self._extract_output(container, output_dir)

        container.remove()

        return ExecutionResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )

    def _put_directory(self, container, source_dir: Path, target: str) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for item in source_dir.iterdir():
                tar.add(str(item), arcname=item.name)
        buf.seek(0)
        container.put_archive(target, buf)

    def _put_file(self, container, source_path: Path, target_dir: str) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            tar.add(str(source_path), arcname=source_path.name)
        buf.seek(0)
        container.put_archive(target_dir, buf)

    def _put_single_file_content(
        self, container, content: str, target_path: str
    ) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo(name=os.path.basename(target_path))
            data = content.encode()
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        buf.seek(0)
        container.put_archive(os.path.dirname(target_path), buf)

    def _extract_output(self, container, output_dir: Path) -> None:
        archive, _ = container.get_archive(OUTPUT_TARGET)
        buf = io.BytesIO()
        for chunk in archive:
            buf.write(chunk)
        buf.seek(0)
        with tarfile.open(fileobj=buf, mode="r") as tar:
            prefix = OUTPUT_TARGET.strip("/") + "/"
            for member in tar.getmembers():
                if member.name.startswith(prefix):
                    member.name = member.name[len(prefix) :]
            tar.extractall(path=str(output_dir))
