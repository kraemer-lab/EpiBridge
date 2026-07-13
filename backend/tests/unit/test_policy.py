import pytest

from app.auth.policy import PolicyError, require_capability
from app.models.capability import Capability, UserCapability
from app.models.user import User, UserRole


def _make_user(capability_names: list[str] | None = None) -> User:
    user = User(
        email="test@example.com",
        display_name="Test",
        password_hash="hash",
        role=UserRole.RESEARCHER,
    )
    if capability_names:
        user.advanced_capabilities = [
            UserCapability(capability_name=n) for n in capability_names
        ]
    return user


class TestRequireCapability:
    def test_passes_when_user_has_capability(self):
        user = _make_user([Capability.BUNDLE_CREATE])
        require_capability(user, Capability.BUNDLE_CREATE)

    def test_raises_when_user_lacks_capability(self):
        user = _make_user([Capability.BUNDLE_CREATE])
        with pytest.raises(PolicyError, match="Requires capability 'bundle.review'"):
            require_capability(user, Capability.BUNDLE_REVIEW)

    def test_raises_when_user_has_no_capabilities(self):
        user = _make_user()
        with pytest.raises(PolicyError, match="Requires capability 'project.manage'"):
            require_capability(user, Capability.PROJECT_MANAGE)

    def test_passes_with_multiple_capabilities(self):
        user = _make_user([Capability.BUNDLE_CREATE, Capability.BUNDLE_SUBMIT])
        require_capability(user, Capability.BUNDLE_SUBMIT)
        require_capability(user, Capability.BUNDLE_CREATE)

    def test_admin_has_all_capabilities(self):
        user = User(
            email="admin@example.com",
            display_name="Admin",
            password_hash="hash",
            role=UserRole.ADMIN,
        )
        user.advanced_capabilities = [
            UserCapability(capability_name=c.value) for c in Capability
        ]
        for c in Capability:
            require_capability(user, c.value)


class TestHasCapability:
    def test_has_capability_true(self):
        user = _make_user([Capability.EXECUTION_RUN])
        assert user.has_capability(Capability.EXECUTION_RUN) is True

    def test_has_capability_false(self):
        user = _make_user([Capability.BUNDLE_CREATE])
        assert user.has_capability(Capability.EXECUTION_RUN) is False

    def test_has_capability_empty(self):
        user = _make_user()
        assert user.has_capability(Capability.PROJECT_MANAGE) is False
