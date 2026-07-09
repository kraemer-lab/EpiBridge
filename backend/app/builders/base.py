from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BuildResult:
    success: bool = True
    image_reference: str = ""
    build_log: str = ""
    duration_seconds: float = 0.0


class EnvironmentBuilder(ABC):
    @abstractmethod
    def identifier(self) -> str: ...

    @abstractmethod
    def dependency_hash(self, bundle_path: Path) -> str: ...

    @abstractmethod
    def build(
        self,
        *,
        bundle_path: Path,
        base_image: str,
        image_tag: str,
    ) -> BuildResult: ...
