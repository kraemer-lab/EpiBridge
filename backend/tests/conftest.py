import os

# Provide defaults so Settings can load during test discovery.
# Override with environment variables or .env as needed.
os.environ.setdefault("POSTGRES_PASSWORD", "test-pw")
os.environ.setdefault("REDIS_PASSWORD", "test-redis")
os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("DEV_AUTH", "true")
os.environ.setdefault("AUTO_REGISTER_RESOURCES", "false")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
