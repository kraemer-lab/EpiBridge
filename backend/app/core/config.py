from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_db: str = "epibridge"
    postgres_user: str = "epibridge"
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    redis_password: str
    redis_host: str = "localhost"
    redis_port: int = 6379

    secret_key: str

    domain: str = "localhost"
    admin_email: str = "admin@epibridge.local"
    admin_password: str = "admin"
    session_ttl_seconds: int = 86400
    auto_create_schema: bool = True
    auto_register_resources: bool = True
    resource_manifest_dir: str = ""
    auto_register_environments: bool = True
    environment_manifest_dir: str = ""
    output_dir: str = "/tmp/epibridge-outputs"
    analysis_bundle_root: str = ""
    bundle_store_dir: str = "/var/lib/epibridge/bundles"
    data_root: str = "/read-only-data"
    host_data_root: str = ""

    ai_assist_enabled: bool = False
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env"}


settings = Settings()
