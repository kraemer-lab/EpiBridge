import argon2
from sqlalchemy.orm import Session

from app.auth.base import AuthenticationError, IdentityProvider
from app.models.user import User

_ph = argon2.PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _ph.check_needs_rehash(password_hash)


class LocalIdentityProvider(IdentityProvider):
    def authenticate(self, db: Session, *, email: str, password: str) -> User:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise AuthenticationError("Invalid email or password")
        if not verify_password(user.password_hash, password):
            raise AuthenticationError("Invalid email or password")
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            db.commit()
        return user
