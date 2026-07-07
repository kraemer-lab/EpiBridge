from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from app.models.session import Session


def create_session(db: DBSession, user_id: str) -> Session:
    session = Session(user_id=user_id, expires_at=Session.default_expiry())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_valid_session(db: DBSession, session_id: str) -> Session | None:
    session = db.query(Session).filter(Session.id == session_id).first()
    if session is None:
        return None
    if session.expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return session


def delete_session(db: DBSession, session_id: str) -> None:
    session = db.query(Session).filter(Session.id == session_id).first()
    if session is not None:
        db.delete(session)
        db.commit()


def cleanup_expired_sessions(db: DBSession) -> int:
    now = datetime.now(timezone.utc)
    count = (
        db.query(Session)
        .filter(Session.expires_at < now)
        .delete(synchronize_session="fetch")
    )
    db.commit()
    return count
