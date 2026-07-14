from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.ai.context import AIReviewContext


@dataclass
class AIReviewResult:
    summary: str = ""
    assessment: str = ""
    assessment_confidence: str = ""
    reviewer_notes: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def is_unavailable(self) -> bool:
        return bool(self.errors)


@dataclass
class ProviderStatus:
    ready: bool
    reason: str | None = None


class AIProvider(ABC):
    @abstractmethod
    def review(
        self,
        analysis_dir: Path,
        context: AIReviewContext | None = None,
    ) -> AIReviewResult: ...

    @abstractmethod
    def check_status(self) -> ProviderStatus: ...
