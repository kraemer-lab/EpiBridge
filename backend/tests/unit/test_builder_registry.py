from pathlib import Path

import pytest

from app.builders.base import EnvironmentBuilder
from app.builders.registry import BuilderRegistry


class _TestBuilder(EnvironmentBuilder):
    def identifier(self) -> str:
        return "test"

    def dependency_hash(self, bundle_path) -> str:
        return "d1" + "0" * 62

    def default_dependency_filename(self) -> str:
        return "requirements.txt"

    @classmethod
    def get_template_dockerfile(cls) -> Path:
        return Path("/nonexistent/Dockerfile")

    def build(self, *, bundle_path, dockerfile, base_image, image_tag):
        raise NotImplementedError


class _OtherBuilder(EnvironmentBuilder):
    def identifier(self) -> str:
        return "other"

    def dependency_hash(self, bundle_path) -> str:
        return "d2" + "0" * 62

    def default_dependency_filename(self) -> str:
        return "environment.yml"

    @classmethod
    def get_template_dockerfile(cls) -> Path:
        return Path("/nonexistent/Dockerfile")

    def build(self, *, bundle_path, dockerfile, base_image, image_tag):
        raise NotImplementedError


class TestBuilderRegistry:
    def setup_method(self):
        self.registry = BuilderRegistry()
        self.registry.register("test-", _TestBuilder)
        self.registry.register("other-", _OtherBuilder)

    def test_get_for_runtime_matches_prefix(self):
        builder = self.registry.get_for_runtime("test-1.0")
        assert isinstance(builder, _TestBuilder)

    def test_get_for_runtime_full_match(self):
        builder = self.registry.get_for_runtime("other-3.14")
        assert isinstance(builder, _OtherBuilder)

    def test_get_for_runtime_no_match_returns_none(self):
        result = self.registry.get_for_runtime("unknown-1.0")
        assert result is None

    def test_get_by_identifier(self):
        builder = self.registry.get_by_identifier("test")
        assert isinstance(builder, _TestBuilder)

    def test_get_by_identifier_missing_raises(self):
        with pytest.raises(ValueError, match="No builder registered with identifier"):
            self.registry.get_by_identifier("nonexistent")

    def test_list_builders(self):
        ids = self.registry.list_builders()
        assert "test" in ids
        assert "other" in ids

    def test_register_replaces_existing_prefix(self):
        registry2 = BuilderRegistry()
        registry2.register("py-", _TestBuilder)
        registry2.register("py-", _OtherBuilder)
        builder = registry2.get_for_runtime("py-3")
        assert isinstance(builder, _OtherBuilder)
