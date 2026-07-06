import enum


class ProviderType(str, enum.Enum):
    CSV = "csv"
    DUCKDB = "duckdb"
    POSTGRES = "postgres"
    EXCEL = "excel"
    PARQUET = "parquet"
