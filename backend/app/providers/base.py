from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Mount:
    source: str
    read_only: bool = True


@dataclass
class RuntimeConfig:
    mounts: list[Mount] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


class ResourceProvider(ABC):
    @abstractmethod
    def validate_endpoint(self, endpoint: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def prepare_runtime(self, endpoint: dict[str, Any]) -> RuntimeConfig: ...
