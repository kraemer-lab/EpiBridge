from typing import Any

from app.providers.base import ResourceProvider, RuntimeConfig


class PostgresProvider(ResourceProvider):
    def validate_endpoint(self, endpoint: dict[str, Any]) -> dict[str, Any]:
        for field in ("host", "database"):
            if field not in endpoint or not isinstance(endpoint[field], str):
                msg = f"PostgresProvider: '{field}' must be a non-empty string"
                raise ValueError(msg)
        return {
            "host": endpoint["host"],
            "database": endpoint["database"],
            "schema": endpoint.get("schema", "public"),
        }

    def prepare_runtime(self, endpoint: dict[str, Any]) -> RuntimeConfig:
        return RuntimeConfig(
            env={
                "PGHOST": endpoint["host"],
                "PGDATABASE": endpoint["database"],
                "PGSCHEMA": endpoint.get("schema", "public"),
            },
        )
