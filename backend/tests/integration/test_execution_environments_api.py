import pytest

from app.models.execution_environment import ExecutionEnvironment


@pytest.fixture
def seeded_environments(db_session):
    environments = [
        ExecutionEnvironment(
            identifier="python-3.13-scientific",
            name="Python 3.13 Scientific",
            runtime="python-3.13",
            description="NumPy, SciPy, Pandas",
            status="active",
        ),
        ExecutionEnvironment(
            identifier="r-4.5-tidyverse",
            name="R 4.5 Tidyverse",
            runtime="r-4.5",
            description="tidyverse, dplyr, ggplot2",
            status="active",
        ),
        ExecutionEnvironment(
            identifier="deprecated-env",
            name="Deprecated Env",
            runtime="python-3.10",
            description="Old environment",
            status="deprecated",
        ),
    ]
    for e in environments:
        db_session.add(e)
    db_session.commit()
    for e in environments:
        db_session.refresh(e)
    return environments


class TestExecutionEnvironmentsAPI:
    def test_list_active_only(self, client, admin_user, seeded_environments):
        response = client.get("/api/execution-environments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {e["name"] for e in data}
        assert "Python 3.13 Scientific" in names
        assert "R 4.5 Tidyverse" in names
        assert "Deprecated Env" not in names

    def test_returns_fields(self, client, admin_user, seeded_environments):
        response = client.get("/api/execution-environments")
        assert response.status_code == 200
        env = response.json()[0]
        assert "id" in env
        assert "identifier" in env
        assert "name" in env
        assert "runtime" in env
        assert "description" in env
        assert "status" in env
        assert "image_reference" in env
        assert "created_at" in env
        assert "updated_at" in env

    def test_ordered_by_name(self, client, admin_user, seeded_environments):
        response = client.get("/api/execution-environments")
        data = response.json()
        names = [e["name"] for e in data]
        assert names == sorted(names)
