from typing import Any

from app.providers.base import (
    Mount,
    ResourceProvider,
    RuntimeConfig,
    normalize_mount_source,
)

RUNTIME_ROOT = "/read-only-data"


class CsvProvider(ResourceProvider):
    def validate_endpoint(self, endpoint: dict[str, Any]) -> dict[str, Any]:
        path = endpoint.get("path")
        if not path or not isinstance(path, str):
            raise ValueError("CsvProvider: 'path' must be a non-empty string")
        return {"path": path}

    def prepare_runtime(self, endpoint: dict[str, Any]) -> RuntimeConfig:
        source = normalize_mount_source(RUNTIME_ROOT, endpoint["path"])
        return RuntimeConfig(
            mounts=[Mount(source=source, read_only=True)],
        )
