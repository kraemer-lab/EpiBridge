from app.providers.base import Mount, ResourceProvider, RuntimeConfig
from app.providers.csv import CsvProvider
from app.providers.duckdb import DuckDBProvider
from app.providers.excel import ExcelProvider
from app.providers.parquet import ParquetProvider
from app.providers.postgres import PostgresProvider
from app.providers.registry import registry
from app.providers.types import ProviderType

registry.register(ProviderType.CSV, CsvProvider)
registry.register(ProviderType.DUCKDB, DuckDBProvider)
registry.register(ProviderType.POSTGRES, PostgresProvider)
registry.register(ProviderType.EXCEL, ExcelProvider)
registry.register(ProviderType.PARQUET, ParquetProvider)

__all__ = [
    "Mount",
    "ProviderType",
    "ResourceProvider",
    "RuntimeConfig",
    "registry",
]
