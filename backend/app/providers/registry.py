from app.providers.base import ResourceProvider
from app.providers.types import ProviderType


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[ProviderType, type[ResourceProvider]] = {}

    def register(
        self, provider_type: ProviderType, provider_cls: type[ResourceProvider]
    ) -> None:
        self._providers[provider_type] = provider_cls

    def get(self, provider_type: ProviderType) -> ResourceProvider:
        cls = self._providers.get(provider_type)
        if cls is None:
            raise ValueError(f"No provider registered for {provider_type.value}")
        return cls()

    def list_types(self) -> list[ProviderType]:
        return list(self._providers.keys())


registry = ProviderRegistry()
