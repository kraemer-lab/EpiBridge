from app.builders.base import EnvironmentBuilder


class BuilderRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, type[EnvironmentBuilder]] = {}

    def register(
        self, runtime_prefix: str, builder_cls: type[EnvironmentBuilder]
    ) -> None:
        self._builders[runtime_prefix] = builder_cls

    def get_for_runtime(self, runtime: str) -> EnvironmentBuilder | None:
        for prefix, cls in self._builders.items():
            if runtime.startswith(prefix):
                return cls()
        return None

    def get_by_identifier(self, identifier: str) -> EnvironmentBuilder:
        for cls in self._builders.values():
            if cls().identifier() == identifier:
                return cls()
        raise ValueError(f"No builder registered with identifier: {identifier}")

    def list_builders(self) -> list[str]:
        return [cls().identifier() for cls in self._builders.values()]


registry = BuilderRegistry()
