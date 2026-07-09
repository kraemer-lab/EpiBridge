import os

os.environ.setdefault("POSTGRES_PASSWORD", "test-pw")
os.environ["POSTGRES_DB"] = "epibridge_test"
os.environ.setdefault("REDIS_PASSWORD", "test-redis")
os.environ["REDIS_DB"] = "1"
os.environ.setdefault("SECRET_KEY", "a" * 32)
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-pw")
os.environ.setdefault("AUTO_REGISTER_RESOURCES", "false")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
