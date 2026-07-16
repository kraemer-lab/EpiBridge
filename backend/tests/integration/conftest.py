import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth.local import hash_password
from app.core.config import settings
from app.db.base import Base
from app.db.migration import ensure_migrated
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.capability import ALL_CAPABILITIES, UserCapability
from app.models.role import RoleRecord
from app.models.user import User, UserRole
from app.models.user_role import UserRoleAssignment
from app.services.auth_framework_seeder import (
    cleanup_role_derived_capabilities,
    seed_auth_framework,
)
from app.services.session_service import create_session


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    ensure_migrated()
    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()
    yield
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS user_role"))


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
        db=settings.redis_db,
        decode_responses=True,
    )
    yield r
    r.close()


@pytest.fixture
def admin_user(db_session):
    seed_auth_framework(db_session)
    user = User(
        email=settings.admin_email,
        display_name="Administrator",
        password_hash=hash_password(settings.admin_password),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.flush()

    role_record = (
        db_session.query(RoleRecord)
        .filter(RoleRecord.name == UserRole.ADMIN.value)
        .first()
    )
    if role_record is not None:
        db_session.add(UserRoleAssignment(user_id=user.id, role_id=role_record.id))

    for cap_name in ALL_CAPABILITIES:
        db_session.execute(
            text("INSERT INTO capabilities (name) VALUES (:n) ON CONFLICT DO NOTHING"),
            {"n": cap_name},
        )
        db_session.add(UserCapability(user_id=user.id, capability_name=cap_name))

    cleanup_role_derived_capabilities(db_session, user)

    db_session.commit()
    db_session.refresh(user)
    return user


def _make_user(db_session, email, display_name, role):
    seed_auth_framework(db_session)
    user = User(
        email=email,
        display_name=display_name,
        password_hash=hash_password("password"),
        role=role,
    )
    db_session.add(user)
    db_session.flush()
    role_record = (
        db_session.query(RoleRecord).filter(RoleRecord.name == role.value).first()
    )
    if role_record is not None:
        db_session.add(UserRoleAssignment(user_id=user.id, role_id=role_record.id))
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def researcher_user(db_session):
    return _make_user(
        db_session, "researcher@test.local", "Researcher User", UserRole.RESEARCHER
    )


@pytest.fixture
def moderator_user(db_session):
    return _make_user(
        db_session, "moderator@test.local", "Moderator User", UserRole.MODERATOR
    )


@pytest.fixture
def maintainer_user(db_session):
    return _make_user(
        db_session, "maintainer@test.local", "Maintainer User", UserRole.MAINTAINER
    )


def _make_client(db_session, user):
    test_client = TestClient(app)
    session = create_session(db_session, user.id)
    test_client.cookies.set("session_id", session.id)
    return test_client


@pytest.fixture
def client(db_session, admin_user):
    return _make_client(db_session, admin_user)


@pytest.fixture
def researcher_client(db_session, researcher_user):
    return _make_client(db_session, researcher_user)


@pytest.fixture
def moderator_client(db_session, moderator_user):
    return _make_client(db_session, moderator_user)


@pytest.fixture
def maintainer_client(db_session, maintainer_user):
    return _make_client(db_session, maintainer_user)


@pytest.fixture
def anon_client():
    return TestClient(app)
