import uuid

from app.models.project import Project


def test_project_creation():
    owner_id = uuid.uuid4()
    project = Project(
        name="Test Project",
        description="A test project",
        owner_id=owner_id,
    )
    assert project.name == "Test Project"
    assert project.description == "A test project"
    assert project.owner_id == owner_id


def test_project_default_description():
    owner_id = uuid.uuid4()
    project = Project(name="Minimal", owner_id=owner_id)
    assert project.description is None
