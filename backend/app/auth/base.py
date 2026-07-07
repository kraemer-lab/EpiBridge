from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.models.user import User


class AuthenticationError(Exception):
    pass


class IdentityProvider(ABC):
    @abstractmethod
    def authenticate(self, db: Session, *, email: str, password: str) -> User: ...
