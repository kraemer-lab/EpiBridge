from unittest.mock import MagicMock

import pytest

from app.auth.base import AuthenticationError
from app.auth.local import LocalIdentityProvider, hash_password, verify_password
from app.models.user import User, UserRole

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "correct-horse-battery-staple"


def test_hash_and_verify():
    hashed = hash_password(TEST_PASSWORD)
    assert hashed != TEST_PASSWORD
    assert verify_password(hashed, TEST_PASSWORD) is True
    assert verify_password(hashed, "wrong-password") is False


def test_verify_invalid_hash():
    assert verify_password("not-a-valid-hash", TEST_PASSWORD) is False


def test_authenticate_success():
    db = MagicMock()
    hashed = hash_password(TEST_PASSWORD)
    user = User(
        email=TEST_EMAIL,
        display_name="Test User",
        password_hash=hashed,
        role=UserRole.RESEARCHER,
    )
    db.query.return_value.filter.return_value.first.return_value = user

    provider = LocalIdentityProvider()
    result = provider.authenticate(db, email=TEST_EMAIL, password=TEST_PASSWORD)
    assert result is user


def test_authenticate_wrong_password():
    db = MagicMock()
    hashed = hash_password(TEST_PASSWORD)
    user = User(
        email=TEST_EMAIL,
        display_name="Test User",
        password_hash=hashed,
        role=UserRole.RESEARCHER,
    )
    db.query.return_value.filter.return_value.first.return_value = user

    provider = LocalIdentityProvider()
    with pytest.raises(AuthenticationError):
        provider.authenticate(db, email=TEST_EMAIL, password="wrong-password")


def test_authenticate_nonexistent_user():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    provider = LocalIdentityProvider()
    with pytest.raises(AuthenticationError):
        provider.authenticate(db, email="nobody@example.com", password=TEST_PASSWORD)
