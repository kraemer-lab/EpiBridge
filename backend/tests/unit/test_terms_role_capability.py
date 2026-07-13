from app.models.capability import Capability
from app.models.user import UserRole


class TestTermsManageCapabilitySeeding:
    def test_terms_manage_in_admin_role(self):
        from app.services.auth_framework_seeder import _ROLE_CAPABILITY_MAP

        admin_caps = _ROLE_CAPABILITY_MAP[UserRole.ADMIN]
        assert Capability.TERMS_MANAGE in admin_caps

    def test_terms_manage_not_in_researcher_role(self):
        from app.services.auth_framework_seeder import _ROLE_CAPABILITY_MAP

        researcher_caps = _ROLE_CAPABILITY_MAP[UserRole.RESEARCHER]
        assert Capability.TERMS_MANAGE not in researcher_caps

    def test_terms_manage_not_in_moderator_role(self):
        from app.services.auth_framework_seeder import _ROLE_CAPABILITY_MAP

        moderator_caps = _ROLE_CAPABILITY_MAP[UserRole.MODERATOR]
        assert Capability.TERMS_MANAGE not in moderator_caps
