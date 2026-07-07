from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.models.session import Session
from app.services.session_service import (
    cleanup_expired_sessions,
    create_session,
    delete_session,
    get_valid_session,
)


def _make_session(expires_at: datetime) -> Session:
    s = Session(user_id="00000000-0000-0000-0000-000000000001")
    s.id = "test-session-id"
    s.expires_at = expires_at
    return s


def test_create_session():
    db = MagicMock()
    session = create_session(db, "user-1")
    assert session.user_id == "user-1"
    assert session.expires_at > datetime.now(timezone.utc)
    db.add.assert_called_once_with(session)
    db.commit.assert_called_once()


def test_get_valid_session_returns_valid():
    db = MagicMock()
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    session = _make_session(future)
    db.query.return_value.filter.return_value.first.return_value = session

    result = get_valid_session(db, "test-session-id")
    assert result is session


def test_get_valid_session_returns_none_for_expired():
    db = MagicMock()
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    session = _make_session(past)
    db.query.return_value.filter.return_value.first.return_value = session

    result = get_valid_session(db, "test-session-id")
    assert result is None
    db.delete.assert_called_once_with(session)
    db.commit.assert_called_once()


def test_get_valid_session_returns_none_for_missing():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    result = get_valid_session(db, "nonexistent")
    assert result is None


def test_delete_session_existing():
    db = MagicMock()
    session = _make_session(datetime.now(timezone.utc) + timedelta(hours=1))
    db.query.return_value.filter.return_value.first.return_value = session

    delete_session(db, "test-session-id")
    db.delete.assert_called_once_with(session)
    db.commit.assert_called_once()


def test_delete_session_nonexistent():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    delete_session(db, "nonexistent")
    db.delete.assert_not_called()


def test_cleanup_expired_sessions():
    db = MagicMock()
    db.query.return_value.filter.return_value.delete.return_value = 3

    count = cleanup_expired_sessions(db)
    assert count == 3
    db.commit.assert_called_once()
