import uuid

import pytest

from app.models.data_resource import DataResource
from app.models.project import Project
from app.providers.csv import CsvProvider
from app.providers.registry import registry
from app.providers.types import ProviderType


class TestDataResourceModel:
    def test_create_data_resource(self):
        resource = DataResource(
            name="COVID Study Data",
            description="Primary cohort",
            provider_type="csv",
            endpoint={"path": "study123/data.csv"},
            status="active",
        )
        assert resource.name == "COVID Study Data"
        assert resource.description == "Primary cohort"
        assert resource.provider_type == "csv"
        assert resource.endpoint == {"path": "study123/data.csv"}
        assert resource.status == "active"

    def test_default_description(self):
        resource = DataResource(
            name="Minimal",
            provider_type="csv",
            endpoint={"path": "data.csv"},
        )
        assert resource.description is None

    def test_default_status(self):
        resource = DataResource(
            name="Test",
            provider_type="csv",
            endpoint={"path": "data.csv"},
        )
        assert resource.status is None


class TestDataResourceAssociation:
    def test_project_data_resource_association(self):
        owner_id = uuid.uuid4()
        project = Project(name="Test Project", owner_id=owner_id)
        resource = DataResource(
            name="Test Resource",
            provider_type="csv",
            endpoint={"path": "data.csv"},
            status="active",
        )

        from app.models.project_data_resource import ProjectResourceAllocation

        allocation = ProjectResourceAllocation(
            project_id=project.id,
            data_resource_id=resource.id,
            created_by_id=owner_id,
        )
        allocation.data_resource = resource
        project.resource_allocations.append(allocation)

        assert len(project.data_resources) == 1
        assert project.data_resources[0].name == "Test Resource"
        assert len(resource.projects) == 1
        assert resource.projects[0].name == "Test Project"

    def test_multiple_resources_on_project(self):
        owner_id = uuid.uuid4()
        project = Project(name="Multi Resource Project", owner_id=owner_id)
        ep = {"path": "a.csv"}
        r1 = DataResource(
            name="Resource 1", provider_type="csv", endpoint=ep, status="active"
        )
        ep2 = {"path": "b.csv"}
        r2 = DataResource(
            name="Resource 2", provider_type="csv", endpoint=ep2, status="active"
        )

        from app.models.project_data_resource import ProjectResourceAllocation

        a1 = ProjectResourceAllocation(
            project_id=project.id, data_resource_id=r1.id, created_by_id=owner_id
        )
        a1.data_resource = r1
        a2 = ProjectResourceAllocation(
            project_id=project.id, data_resource_id=r2.id, created_by_id=owner_id
        )
        a2.data_resource = r2
        project.resource_allocations.extend([a1, a2])

        assert len(project.data_resources) == 2

    def test_resource_shared_across_projects(self):
        owner_id = uuid.uuid4()
        project_a = Project(name="Project A", owner_id=owner_id)
        project_b = Project(name="Project B", owner_id=owner_id)
        ep = {"path": "shared.csv"}
        shared = DataResource(
            name="Shared", provider_type="csv", endpoint=ep, status="active"
        )

        from app.models.project_data_resource import ProjectResourceAllocation

        a1 = ProjectResourceAllocation(
            project_id=project_a.id,
            data_resource_id=shared.id,
            created_by_id=owner_id,
        )
        a1.data_resource = shared
        project_a.resource_allocations.append(a1)

        a2 = ProjectResourceAllocation(
            project_id=project_b.id,
            data_resource_id=shared.id,
            created_by_id=owner_id,
        )
        a2.data_resource = shared
        project_b.resource_allocations.append(a2)

        assert len(shared.projects) == 2


class TestCsvProvider:
    def test_validate_endpoint_valid(self):
        provider = CsvProvider()
        result = provider.validate_endpoint({"path": "study123/data.csv"})
        assert result == {"path": "study123/data.csv"}

    def test_validate_endpoint_missing_path(self):
        provider = CsvProvider()
        with pytest.raises(ValueError, match="path"):
            provider.validate_endpoint({})

    def test_validate_endpoint_empty_path(self):
        provider = CsvProvider()
        with pytest.raises(ValueError, match="path"):
            provider.validate_endpoint({"path": ""})

    def test_validate_endpoint_non_string_path(self):
        provider = CsvProvider()
        with pytest.raises(ValueError, match="path"):
            provider.validate_endpoint({"path": 123})

    def test_prepare_runtime(self):
        provider = CsvProvider()
        config = provider.prepare_runtime({"path": "demo.csv"})

        assert len(config.mounts) == 1
        mount = config.mounts[0]
        assert mount.source == "/read-only-data/demo.csv"
        assert mount.read_only is True

        assert config.env == {}

    def test_prepare_runtime_subdirectory(self):
        provider = CsvProvider()
        config = provider.prepare_runtime({"path": "study123/data.csv"})

        assert config.mounts[0].source == "/read-only-data/study123/data.csv"
        assert config.env == {}

    def test_executor_resolves_mount_target(self):
        provider = CsvProvider()
        config = provider.prepare_runtime({"path": "mexico_dengue_2026/dengue.csv"})

        assert len(config.mounts) == 1
        mount = config.mounts[0]
        assert mount.source == "/read-only-data/mexico_dengue_2026/dengue.csv"
        assert mount.read_only is True

        assert config.env == {}


class TestProviderRegistry:
    def test_get_csv_provider(self):
        provider = registry.get(ProviderType.CSV)
        assert isinstance(provider, CsvProvider)

    def test_get_unregistered_raises(self):
        with pytest.raises(ValueError, match="unregistered"):
            registry.get(ProviderType("unregistered"))  # type: ignore[arg-type]

    def test_list_types(self):
        types = registry.list_types()
        assert ProviderType.CSV in types
        assert ProviderType.DUCKDB in types
        assert ProviderType.POSTGRES in types
        assert ProviderType.EXCEL in types
        assert ProviderType.PARQUET in types
        assert len(types) == 5

    def test_registry_returns_new_instance(self):
        a = registry.get(ProviderType.CSV)
        b = registry.get(ProviderType.CSV)
        assert a is not b
        assert isinstance(a, CsvProvider)
        assert isinstance(b, CsvProvider)
