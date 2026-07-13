from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


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
    ) -> ExecutionResult: ...
