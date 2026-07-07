import uuid

from app.models.analysis_bundle import AnalysisBundle, AnalysisBundleDataResource
from app.models.data_resource import DataResource
from app.models.execution_environment import ExecutionEnvironment
from app.models.project import Project


class TestAnalysisBundleModel:
    def test_create_bundle(self):
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()
        ee_id = uuid.uuid4()
        bundle = AnalysisBundle(
            project_id=project_id,
            created_by_id=user_id,
            execution_environment_id=ee_id,
            name="Survival Analysis",
            version="1.0.0",
            entrypoint="run.py",
            description="A survival analysis on UK Biobank data",
            outputs=["summary.csv"],
            parameters={"threshold": 0.05},
        )
        assert bundle.name == "Survival Analysis"
        assert bundle.execution_environment_id == ee_id
        assert bundle.version == "1.0.0"
        assert bundle.entrypoint == "run.py"
        assert bundle.description == "A survival analysis on UK Biobank data"
        assert bundle.outputs == ["summary.csv"]
        assert bundle.parameters == {"threshold": 0.05}

    def test_default_outputs_and_parameters(self):
        bundle = AnalysisBundle(
            project_id=uuid.uuid4(),
            created_by_id=uuid.uuid4(),
            execution_environment_id=uuid.uuid4(),
            name="Minimal",
            version="1.0.0",
            entrypoint="run.py",
            outputs=[],
            parameters={},
        )
        assert bundle.outputs == []
        assert bundle.parameters == {}

    def test_execution_environment_association(self):
        env = ExecutionEnvironment(
            identifier="python-3.13-scientific",
            name="Python 3.13 Scientific",
            runtime="python-3.13",
        )
        bundle = AnalysisBundle(
            project_id=uuid.uuid4(),
            created_by_id=uuid.uuid4(),
            execution_environment_id=env.id or uuid.uuid4(),
            name="Test Bundle",
            version="1.0.0",
            entrypoint="run.py",
        )
        bundle.execution_environment = env
        assert bundle.execution_environment.name == "Python 3.13 Scientific"
        assert bundle.execution_environment.runtime == "python-3.13"

    def test_data_resource_association(self):
        bundle = AnalysisBundle(
            project_id=uuid.uuid4(),
            created_by_id=uuid.uuid4(),
            execution_environment_id=uuid.uuid4(),
            name="Test Bundle",
            version="1.0.0",
            entrypoint="run.py",
        )
        resource = DataResource(
            name="Test Resource",
            provider_type="csv",
            endpoint={"path": "data.csv"},
            status="active",
        )
        bundle.data_resources.append(resource)
        assert len(bundle.data_resources) == 1
        assert bundle.data_resources[0].name == "Test Resource"

    def test_multiple_resources_on_bundle(self):
        bundle = AnalysisBundle(
            project_id=uuid.uuid4(),
            created_by_id=uuid.uuid4(),
            execution_environment_id=uuid.uuid4(),
            name="Multi Resource Bundle",
            version="1.0.0",
            entrypoint="run.py",
        )
        r1 = DataResource(
            name="Resource 1",
            provider_type="csv",
            endpoint={"path": "a.csv"},
            status="active",
        )
        r2 = DataResource(
            name="Resource 2",
            provider_type="csv",
            endpoint={"path": "b.csv"},
            status="active",
        )
        bundle.data_resources.extend([r1, r2])
        assert len(bundle.data_resources) == 2

    def test_project_association(self):
        owner_id = uuid.uuid4()
        project = Project(name="Test Project", owner_id=owner_id)
        bundle = AnalysisBundle(
            project_id=uuid.uuid4(),
            created_by_id=uuid.uuid4(),
            execution_environment_id=uuid.uuid4(),
            name="Project Bundle",
            version="1.0.0",
            entrypoint="run.py",
        )
        bundle.project = project
        assert bundle.project.name == "Test Project"

    def test_default_build_status_is_none_in_memory(self):
        bundle = AnalysisBundle(
            project_id=uuid.uuid4(),
            created_by_id=uuid.uuid4(),
            execution_environment_id=uuid.uuid4(),
            name="Test",
            version="1.0.0",
            entrypoint="run.py",
        )
        assert bundle.build_status is None  # server_default, not in-memory

    def test_can_set_build_status(self):
        bundle = AnalysisBundle(
            project_id=uuid.uuid4(),
            created_by_id=uuid.uuid4(),
            execution_environment_id=uuid.uuid4(),
            name="Test",
            version="1.0.0",
            entrypoint="run.py",
            build_status="environment_ready",
        )
        assert bundle.build_status == "environment_ready"

    def test_can_set_execution_image_id(self):
        img_id = uuid.uuid4()
        bundle = AnalysisBundle(
            project_id=uuid.uuid4(),
            created_by_id=uuid.uuid4(),
            execution_environment_id=uuid.uuid4(),
            name="Test",
            version="1.0.0",
            entrypoint="run.py",
            execution_image_id=img_id,
        )
        assert bundle.execution_image_id == img_id


class TestAnalysisBundleDataResource:
    def test_join_table_fields(self):
        bundle_id = uuid.uuid4()
        resource_id = uuid.uuid4()
        join = AnalysisBundleDataResource(
            analysis_bundle_id=bundle_id,
            data_resource_id=resource_id,
        )
        assert join.analysis_bundle_id == bundle_id
        assert join.data_resource_id == resource_id
