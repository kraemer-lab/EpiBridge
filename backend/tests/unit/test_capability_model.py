from app.models.capability import ALL_CAPABILITIES, Capability


def test_capability_enum_values():
    assert Capability.PROJECT_MANAGE.value == "project.manage"
    assert Capability.PROJECT_MEMBERS_MANAGE.value == "project.members.manage"
    assert Capability.PROJECT_RESOURCES_MANAGE.value == "project.resources.manage"
    assert Capability.BUNDLE_CREATE.value == "bundle.create"
    assert Capability.BUNDLE_SUBMIT.value == "bundle.submit"
    assert Capability.BUNDLE_REVIEW.value == "bundle.review"
    assert Capability.EXECUTION_RUN.value == "execution.run"
    assert Capability.OUTPUT_REVIEW.value == "output.review"
    assert Capability.OUTPUT_RELEASE.value == "output.release"
    assert Capability.ENVIRONMENT_MANAGE.value == "environment.manage"
    assert Capability.DATA_MANAGE.value == "data.manage"
    assert Capability.USER_MANAGE.value == "user.manage"
    assert Capability.BUILD_CUSTOMIZE.value == "build.customize"


def test_all_values_contains_all():
    expected = {c.value for c in Capability}
    assert ALL_CAPABILITIES == expected


def test_all_values_count():
    assert len(ALL_CAPABILITIES) == 13
