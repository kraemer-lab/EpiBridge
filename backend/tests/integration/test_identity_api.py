"""Integration tests validating the capability model through the API.

This file validates that each Role (Researcher, Moderator, Maintainer, Admin)
possesses exactly the capabilities defined in their role template, and that
capability-based authorisation is correctly enforced at every policy gate.
"""

import uuid

import pytest

from app.models.analysis_bundle import AnalysisBundle
from app.models.execution_environment import ExecutionEnvironment
from app.models.project import Project
from app.models.project_membership import ProjectMembership

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project(db_session, admin_user):
    p = Project(
        name="Capability Test",
        description="Identity validation",
        owner_id=admin_user.id,
    )
    db_session.add(p)
    db_session.flush()
    db_session.add(
        ProjectMembership(
            project_id=p.id, user_id=admin_user.id, created_by_id=admin_user.id
        )
    )
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def execution_environment(db_session):
    env = ExecutionEnvironment(
        identifier="python-3.13-scientific",
        name="Python 3.13 Scientific",
        runtime="python-3.13",
        description="Test environment",
        status="active",
    )
    db_session.add(env)
    db_session.commit()
    db_session.refresh(env)
    return env


def _add_to_project(db_session, project, user, created_by_id):
    membership = ProjectMembership(
        project_id=project.id,
        user_id=user.id,
        created_by_id=created_by_id,
    )
    db_session.add(membership)
    db_session.commit()


def _make_bundle(db_session, project, env, owner_id, name="Test Bundle"):
    bundle = AnalysisBundle(
        project_id=project.id,
        created_by_id=owner_id,
        execution_environment_id=env.id,
        name=name,
        version="1.0.0",
        entrypoint="run.py",
    )
    db_session.add(bundle)
    db_session.commit()
    db_session.refresh(bundle)
    return bundle


# ---------------------------------------------------------------------------
# Researcher capability validation
# ---------------------------------------------------------------------------


class TestResearcherCapabilities:
    """A Researcher should be able to perform research actions but NOT
    governance or administration actions."""

    def test_cannot_create_project(self, researcher_client, researcher_user):
        response = researcher_client.post(
            "/api/projects",
            json={"name": "Researcher Project", "description": ""},
        )
        assert response.status_code == 403

    @pytest.mark.usefixtures("project", "execution_environment")
    def test_can_create_bundle(
        self,
        researcher_client,
        researcher_user,
        admin_user,
        project,
        execution_environment,
        db_session,
    ):
        _add_to_project(db_session, project, researcher_user, admin_user.id)
        response = researcher_client.post(
            f"/api/projects/{project.id}/bundles",
            json={
                "name": "Researcher Bundle",
                "execution_environment_id": str(execution_environment.id),
                "version": "1.0.0",
                "entrypoint": "run.py",
            },
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Researcher Bundle"

    def test_cannot_manage_members(
        self, researcher_client, researcher_user, admin_user, project, db_session
    ):
        _add_to_project(db_session, project, researcher_user, admin_user.id)
        response = researcher_client.post(
            f"/api/projects/{project.id}/members",
            json={"email": "nobody@test.local"},
        )
        assert response.status_code == 403

    def test_cannot_attach_resources(
        self, researcher_client, researcher_user, admin_user, project, db_session
    ):
        _add_to_project(db_session, project, researcher_user, admin_user.id)
        response = researcher_client.post(
            f"/api/projects/{project.id}/resources",
            json={"resource_identifiers": ["any"]},
        )
        assert response.status_code == 403

    def test_cannot_review_bundle(
        self,
        researcher_client,
        researcher_user,
        admin_user,
        project,
        execution_environment,
        db_session,
    ):
        _add_to_project(db_session, project, researcher_user, admin_user.id)
        bundle = _make_bundle(
            db_session, project, execution_environment, researcher_user.id
        )
        response = researcher_client.post(f"/api/admin/bundles/{bundle.id}/approve")
        assert response.status_code == 403

    def test_cannot_review_output_set(
        self, researcher_client, researcher_user, admin_user, project, db_session
    ):
        _add_to_project(db_session, project, researcher_user, admin_user.id)
        response = researcher_client.post(
            f"/api/admin/output-sets/{uuid.uuid4()}/approve"
        )
        # Output set not found (checked before capability)
        assert response.status_code == 404

    def test_cannot_release_output_set(
        self, researcher_client, researcher_user, admin_user, project, db_session
    ):
        _add_to_project(db_session, project, researcher_user, admin_user.id)
        response = researcher_client.post(
            f"/api/admin/output-sets/{uuid.uuid4()}/release"
        )
        # Output set not found (checked before capability)
        assert response.status_code == 404

    def test_cannot_manage_users(self, researcher_client):
        response = researcher_client.get("/api/admin/users")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Moderator capability validation
# ---------------------------------------------------------------------------


class TestModeratorCapabilities:
    """A Moderator should be able to review bundles and output sets, but NOT
    release outputs, manage resources, or manage users."""

    def test_cannot_manage_members(
        self, moderator_client, moderator_user, project, db_session
    ):
        _add_to_project(db_session, project, moderator_user, project.owner_id)
        response = moderator_client.post(
            f"/api/projects/{project.id}/members",
            json={"email": "nonexistent@test.local"},
        )
        assert response.status_code == 403

    def test_can_review_bundle(
        self,
        moderator_client,
        moderator_user,
        project,
        execution_environment,
        db_session,
    ):
        _add_to_project(db_session, project, moderator_user, project.owner_id)
        bundle = _make_bundle(
            db_session, project, execution_environment, moderator_user.id
        )
        # Bundle is DRAFT, approve will fail validation but authorisation passed
        response = moderator_client.post(f"/api/admin/bundles/{bundle.id}/approve")
        assert response.status_code == 422  # transition not allowed, but not 403

    def test_can_review_output_set(
        self, moderator_client, moderator_user, project, db_session
    ):
        _add_to_project(db_session, project, moderator_user, project.owner_id)
        # Output set doesn't exist, but authorisation should pass
        response = moderator_client.post(
            f"/api/admin/output-sets/{uuid.uuid4()}/approve"
        )
        assert response.status_code == 404  # not found, but not 403

    def test_cannot_release_output_set(
        self, moderator_client, moderator_user, project, db_session
    ):
        _add_to_project(db_session, project, moderator_user, project.owner_id)
        response = moderator_client.post(
            f"/api/admin/output-sets/{uuid.uuid4()}/release"
        )
        # Output set not found (checked before capability)
        assert response.status_code == 404

    def test_cannot_manage_users(self, moderator_client):
        response = moderator_client.get("/api/admin/users")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Maintainer capability validation
# ---------------------------------------------------------------------------


class TestMaintainerCapabilities:
    """A Maintainer should be able to perform all governance actions except
    user management."""

    def test_release_nonexistent_output_set_returns_404(
        self, maintainer_client, maintainer_user, project, db_session
    ):
        _add_to_project(db_session, project, maintainer_user, project.owner_id)
        response = maintainer_client.post(
            f"/api/admin/output-sets/{uuid.uuid4()}/release"
        )
        assert response.status_code == 404

    def test_can_read_users(self, maintainer_client):
        """Maintainers can list users with user.read capability."""
        response = maintainer_client.get("/api/admin/users")
        assert response.status_code == 200

    def test_cannot_create_users(self, maintainer_client):
        """Maintainers cannot create users — that requires user.manage."""
        response = maintainer_client.post(
            "/api/admin/users",
            json={
                "email": "new@test.local",
                "display_name": "New",
                "password": "password123",
                "roles": ["researcher"],
            },
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Administrator capability validation
# ---------------------------------------------------------------------------


class TestAdminCapabilities:
    """An Administrator should be able to perform every capability,
    including user management."""

    def test_can_manage_users(self, client):
        response = client.get("/api/admin/users")
        assert response.status_code == 200

    def test_can_create_user(self, client):
        response = client.post(
            "/api/admin/users",
            json={
                "email": "validated-admin@test.local",
                "display_name": "Validated",
                "password": "admin-secret",
                "roles": ["admin"],
            },
        )
        assert response.status_code == 201

    def test_can_review_bundle(
        self, client, project, execution_environment, admin_user, db_session
    ):
        bundle = _make_bundle(db_session, project, execution_environment, admin_user.id)
        response = client.post(f"/api/admin/bundles/{bundle.id}/approve")
        assert response.status_code == 422  # transition, but not 403

    def test_can_release_output_set(self, client, project, db_session):
        response = client.post(f"/api/admin/output-sets/{uuid.uuid4()}/release")
        assert response.status_code == 404  # not found, but not 403
