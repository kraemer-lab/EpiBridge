from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Mount:
    source: str
    read_only: bool = True


@dataclass
class RuntimeConfig:
    mounts: list[Mount] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


def normalize_mount_source(root: str, path: str) -> str:
    resolved = (Path(root) / path).resolve()
    root_resolved = Path(root).resolve()
    if not str(resolved).startswith(str(root_resolved)):
        raise ValueError(f"Mount path escapes data root: {path}")
    return str(resolved)


class ResourceProvider(ABC):
    @abstractmethod
    def validate_endpoint(self, endpoint: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def prepare_runtime(self, endpoint: dict[str, Any]) -> RuntimeConfig: ...
