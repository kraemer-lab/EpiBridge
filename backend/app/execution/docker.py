import io
import os
import tarfile
import time
from collections.abc import Callable
from pathlib import Path

import docker
from docker.errors import ImageNotFound

from app.core.config import settings
from app.execution.base import CancelledError, ExecutionResult, Executor
from app.execution.util import parse_exit_code

NONROOT_USER = "nobody"
WORKDIR = "/work"
ANALYSIS_TARGET = "/analysis"
OUTPUT_TARGET = "/output"
MAX_EXTRACT_SIZE = settings.max_output_size_mb * 1024 * 1024


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

    POLL_INTERVAL = 5

    def run(
        self,
        *,
        image: str,
        analysis_dir: Path,
        command: list[str],
        mounts: list[tuple[str, str, bool]],
        output_dir: Path,
        timeout: int,
        env: dict[str, str],
        network_enabled: bool = False,
        cancel_check: Callable[[], bool] | None = None,
    ) -> ExecutionResult:
        try:
            self._client.images.get(image)
        except ImageNotFound:
            self._client.images.pull(image)

        output_dir.mkdir(parents=True, exist_ok=True)

        volume_bindings = {}
        for source, target, read_only in mounts:
            mode = "ro" if read_only else "rw"
            volume_bindings[self._remap_source(source)] = {"bind": target, "mode": mode}
        # NOTE: read_only=True is intentionally NOT set here.
        #
        # Docker Engine rejects all put_archive() calls when ReadonlyRootfs
        # is enabled, regardless of target path or tmpfs status. The trusted
        # worker injects the analysis bundle via put_archive() before the
        # container starts — this would fail with a read-only rootfs.
        #
        # The remaining sandbox protections (cap_drop=["ALL"],
        # no-new-privileges, non-root user, network isolation, resource
        # limits) provide the required security for the current architecture.
        # A future improvement could mount the bundle store as a host volume,
        # enabling read_only=True without breaking bundle injection.
        container = self._client.containers.create(
            image,
            command=command,
            network_disabled=not network_enabled,
            working_dir=WORKDIR,
            user=NONROOT_USER,
            volumes=volume_bindings,
            environment=env,
            cap_drop=["ALL"],
            # tmpfs for /tmp only — prevents disk exhaustion from ephemeral
            # container writes. /output is NOT tmpfs because Docker Engine's
            # get_archive() does not include files on tmpfs mounts, which
            # would break output extraction by the trusted worker.
            tmpfs={"/tmp": "mode=1777"},
            security_opt=["no-new-privileges:true"],
            mem_limit=settings.execution_mem_limit,
            nano_cpus=int(settings.execution_cpu_limit * 1e9),
            pids_limit=settings.execution_pids_limit,
        )

        self._put_directory(container, analysis_dir, ANALYSIS_TARGET)

        container.start()

        try:
            exit_code = self._poll_container(container, timeout, cancel_check)
        except TimeoutError:
            container.stop()
            container.remove()
            raise
        except CancelledError:
            container.stop()
            container.remove()
            raise

        stdout = (container.logs(stdout=True, stderr=False) or b"").decode()
        stderr = (container.logs(stdout=False, stderr=True) or b"").decode()

        self._extract_output(container, output_dir)

        container.remove()

        return ExecutionResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )

    @staticmethod
    def _poll_container(
        container: docker.models.containers.Container,
        timeout: int,
        cancel_check: Callable[[], bool] | None = None,
    ) -> int:
        start = time.monotonic()
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                raise TimeoutError(f"Execution timed out after {timeout} seconds")

            container.reload()

            if container.status == "exited":
                wait_result = container.wait(timeout=30)
                return parse_exit_code(wait_result)

            if cancel_check is not None and cancel_check():
                raise CancelledError("Execution cancelled administratively")

            time.sleep(DockerExecutor.POLL_INTERVAL)

    def _put_directory(self, container, source_dir: Path, target: str) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for item in source_dir.iterdir():
                if item.is_symlink():
                    raise ValueError(
                        f"Symlink not allowed in analysis bundle: {item.name}"
                    )
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
            total_size = 0
            for member in tar.getmembers():
                member.name = (
                    member.name[len(prefix) :]
                    if member.name.startswith(prefix)
                    else member.name
                )
                resolved = (output_dir / member.name).resolve()
                if not str(resolved).startswith(str(output_dir.resolve())):
                    raise ValueError(f"Path traversal in output archive: {member.name}")
                if member.issym() or member.islnk():
                    raise ValueError(f"Symlink in output archive: {member.name}")
                total_size += member.size
                if total_size > MAX_EXTRACT_SIZE:
                    raise ValueError(
                        f"Output archive exceeds maximum size of "
                        f"{MAX_EXTRACT_SIZE} bytes"
                    )
            tar.extractall(path=str(output_dir))
