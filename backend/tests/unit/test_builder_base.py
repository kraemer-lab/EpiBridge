import pytest

from app.builders.base import BuildPolicy, BuildResult, EnvironmentBuilder


class TestBuildResult:
    def test_defaults(self):
        r = BuildResult()
        assert r.success is True
        assert r.image_reference == ""
        assert r.build_log == ""
        assert r.duration_seconds == 0.0

    def test_success_false(self):
        r = BuildResult(success=False, build_log="missing requirements.txt")
        assert r.success is False
        assert r.build_log == "missing requirements.txt"

    def test_all_fields(self):
        r = BuildResult(
            success=True,
            image_reference="epibridge/builds/python-3.13:abc123",
            build_log="Step 1: ...",
            duration_seconds=12.5,
        )
        assert r.success is True
        assert r.image_reference == "epibridge/builds/python-3.13:abc123"
        assert r.build_log == "Step 1: ..."
        assert r.duration_seconds == 12.5


class TestBuildPolicy:
    def test_defaults(self):
        p = BuildPolicy()
        assert p.network_access is True
        assert p.privileged is False
        assert p.allowed_mounts == []

    def test_custom(self):
        p = BuildPolicy(network_access=False, privileged=True, allowed_mounts=["/data"])
        assert p.network_access is False
        assert p.privileged is True
        assert p.allowed_mounts == ["/data"]


class TestEnvironmentBuilder:
    def test_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            EnvironmentBuilder()  # type: ignore
