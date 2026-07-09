from app.core.config import Settings


def test_settings_loads_with_minimal_env():
    s = Settings(
        _env_file=None,
        postgres_password="test-pw",
        postgres_host="localhost",
        postgres_db="epibridge",
        redis_password="test-redis",
        secret_key="test-key",
    )
    assert s.postgres_host == "localhost"
    assert s.postgres_port == 5432
    assert s.postgres_db == "epibridge"
    assert s.domain == "localhost"
    assert s.admin_email == "admin@epibridge.local"


def test_settings_database_url_property():
    s = Settings(
        postgres_user="custom",
        postgres_password="pw",
        postgres_host="db.example.com",
        postgres_port=15432,
        postgres_db="custom_db",
        redis_password="rpw",
        secret_key="sk",
    )
    assert s.database_url == "postgresql://custom:pw@db.example.com:15432/custom_db"


def test_settings_env_file_config():
    s = Settings(
        postgres_password="pw",
        redis_password="rpw",
        secret_key="sk",
    )
    assert s.model_config.get("env_file") == ".env"
