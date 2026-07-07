import pytest

from app.auth.base import AuthenticationError, IdentityProvider


def test_identity_provider_is_abstract():
    with pytest.raises(TypeError):
        IdentityProvider()


def test_authentication_error_is_exception():
    exc = AuthenticationError("test")
    assert isinstance(exc, Exception)
    assert str(exc) == "test"
