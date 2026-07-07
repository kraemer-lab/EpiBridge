from app.auth.base import AuthenticationError, IdentityProvider
from app.auth.local import LocalIdentityProvider


def get_identity_provider() -> IdentityProvider:
    return LocalIdentityProvider()


__all__ = [
    "AuthenticationError",
    "IdentityProvider",
    "LocalIdentityProvider",
    "get_identity_provider",
]
