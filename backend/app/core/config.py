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
    firebase_project_id: str = ""
    firebase_private_key_id: str = ""
    firebase_private_key: str = ""
    firebase_client_email: str = ""
    firebase_client_id: str = ""

    domain: str = "localhost"
    admin_email: str = "admin@epibridge.local"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env"}


settings = Settings()
