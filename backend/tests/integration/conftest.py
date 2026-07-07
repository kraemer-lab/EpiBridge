import pytest
from fastapi.testclient import TestClient

from app.auth.local import hash_password
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.user import User, UserRole
from app.services.session_service import create_session


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()


@pytest.fixture
def db_connection():
    with engine.connect() as conn:
        yield conn


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def redis_client():
    import redis as redis_lib

    r = redis_lib.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        decode_responses=True,
    )
    yield r
    r.close()


@pytest.fixture
def admin_user(db_session):
    user = User(
        email=settings.admin_email,
        display_name="Administrator",
        password_hash=hash_password(settings.admin_password),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session, admin_user):
    test_client = TestClient(app)
    session = create_session(db_session, admin_user.id)
    test_client.cookies.set("session_id", session.id)
    return test_client


@pytest.fixture
def anon_client():
    return TestClient(app)
