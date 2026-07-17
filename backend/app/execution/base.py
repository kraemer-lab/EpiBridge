from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class CancelledError(Exception):
    """Raised when an execution is cancelled by an administrator."""


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str


class Executor(ABC):
    @abstractmethod
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
    ) -> ExecutionResult: ...
