from app.ai.base import AIProvider, AIReviewResult, ProviderStatus
from app.ai.context import AIReviewContext
from app.ai.ollama import OllamaProvider
from app.core.config import settings


def get_ai_provider() -> AIProvider:
    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout_seconds,
    )


__all__ = [
    "AIProvider",
    "AIReviewContext",
    "AIReviewResult",
    "OllamaProvider",
    "ProviderStatus",
    "get_ai_provider",
]
