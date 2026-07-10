import uuid

import pytest

from app.models.audit_event import AuditEvent
from app.models.data_resource import DataResource
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.terms_acceptance import TermsAcceptance
from app.models.terms_of_service import TermsOfService


@pytest.fixture
def data_resource(db_session):
    resource = DataResource(
        identifier="test-terms-resource",
        name="Terms Test Resource",
        alias="terms_test_resource",
        provider_type="csv",
        endpoint={"path": "data.csv"},
        version="1.0.0",
        status="active",
    )
    db_session.add(resource)
    db_session.commit()
    db_session.refresh(resource)
    return resource


class TestAdminPublishPlatformTerms:
    def test_publishes_platform_terms(self, client, admin_user):
        body = {
            "version": "1.0.0",
            "title": "Platform Terms",
            "content": "Terms content.",
        }
        response = client.post("/api/admin/terms/platform", json=body)
        assert response.status_code == 201
        data = response.json()
        assert data["terms_type"] == "platform"
        assert data["version"] == "1.0.0"
        assert data["title"] == "Platform Terms"

    def test_auto_accepts_for_admin(self, client, admin_user, db_session):
        client.post(
            "/api/admin/terms/platform",
            json={"version": "1.0.0", "title": "T", "content": "C"},
        )
        terms = db_session.query(TermsOfService).first()
        assert terms is not None
        acceptance = (
            db_session.query(TermsAcceptance)
            .filter(
                TermsAcceptance.user_id == admin_user.id,
                TermsAcceptance.terms_of_service_id == terms.id,
            )
            .first()
        )
        assert acceptance is not None

    def test_requires_terms_manage_capability(self, db_session, researcher_client):
        response = researcher_client.post(
            "/api/admin/terms/platform",
            json={"version": "1.0.0", "title": "T", "content": "C"},
        )
        assert response.status_code == 403

    def test_creates_audit_event(self, client, admin_user, db_session):
        client.post(
            "/api/admin/terms/platform",
            json={"version": "1.0.0", "title": "T", "content": "C"},
        )
        event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.event_type == "platform_terms.published")
            .first()
        )
        assert event is not None
        assert event.actor_id == admin_user.id


class TestAdminPublishResourceTerms:
    def test_publishes_resource_terms(self, client, admin_user, data_resource):
        response = client.post(
            f"/api/admin/resources/{data_resource.id}/terms/publish",
            json={"version": "1.0.0", "title": "Resource Terms", "content": "Content."},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["terms_type"] == "data_resource"
        assert data["data_resource_id"] == str(data_resource.id)

    def test_raises_404_for_missing_resource(self, client, admin_user):
        response = client.post(
            f"/api/admin/resources/{uuid.uuid4()}/terms/publish",
            json={"version": "1.0.0", "title": "T", "content": "C"},
        )
        assert response.status_code == 404

    def test_requires_terms_manage(self, db_session, researcher_client, data_resource):
        response = researcher_client.post(
            f"/api/admin/resources/{data_resource.id}/terms/publish",
            json={"version": "1.0.0", "title": "T", "content": "C"},
        )
        assert response.status_code == 403

    def test_creates_dataset_audit_event(
        self, client, admin_user, db_session, data_resource
    ):
        client.post(
            f"/api/admin/resources/{data_resource.id}/terms/publish",
            json={"version": "1.0.0", "title": "T", "content": "C"},
        )
        event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.event_type == "dataset_terms.published")
            .first()
        )
        assert event is not None


class TestAcceptPlatformTerms:
    def test_accepts_platform_terms(self, client, admin_user, db_session):
        terms = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        response = client.post("/api/terms/platform/accept")
        assert response.status_code == 200
        assert response.json() == {"status": "accepted"}

    def test_creates_acceptance_audit_event(self, client, admin_user, db_session):
        terms = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        client.post("/api/terms/platform/accept")
        event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.event_type == "platform_terms.accepted")
            .first()
        )
        assert event is not None

    def test_idempotent(self, client, admin_user, db_session):
        terms = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        client.post("/api/terms/platform/accept")
        response = client.post("/api/terms/platform/accept")
        assert response.status_code == 200

    def test_returns_404_when_no_terms(self, client):
        response = client.post("/api/terms/platform/accept")
        assert response.status_code == 404

    def test_returns_terms_of_service(self, client, admin_user, db_session):
        terms = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="Platform Terms v1",
            content="Terms content here.",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        response = client.get("/api/terms/platform/current")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0.0"
        assert data["title"] == "Platform Terms v1"
        assert data["content"] == "Terms content here."


class TestAcceptResourceTerms:
    def test_accepts_resource_terms(
        self, client, admin_user, data_resource, db_session
    ):
        terms = TermsOfService(
            terms_type="data_resource",
            data_resource_id=data_resource.id,
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()
        db_session.refresh(terms)

        response = client.post(f"/api/terms/resources/{data_resource.id}/accept")
        assert response.status_code == 200
        assert response.json() == {"status": "accepted"}

    def test_returns_404_for_missing_resource_terms(self, client):
        response = client.post(f"/api/terms/resources/{uuid.uuid4()}/accept")
        assert response.status_code == 404


class TestTermsStatus:
    def test_status_when_no_terms(self, client):
        response = client.get("/api/terms/status")
        assert response.status_code == 200
        data = response.json()
        assert data["platform"]["has_terms"] is False
        assert data["dataset_terms"] == []

    def test_status_with_platform_terms_unaccepted(
        self, client, admin_user, db_session
    ):
        terms = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        response = client.get("/api/terms/status")
        data = response.json()
        assert data["platform"]["has_terms"] is True
        assert data["platform"]["accepted"] is False

    def test_status_with_platform_terms_accepted(self, client, admin_user, db_session):
        terms = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        acceptance = TermsAcceptance(
            user_id=admin_user.id,
            terms_of_service_id=terms.id,
        )
        db_session.add(acceptance)
        db_session.commit()

        response = client.get("/api/terms/status")
        data = response.json()
        assert data["platform"]["accepted"] is True


class TestMeEndpoint:
    def test_me_no_terms(self, client):
        response = client.get("/api/me")
        assert response.status_code == 200
        data = response.json()
        assert data["needs_platform_terms_acceptance"] is False

    def test_me_needs_acceptance(self, client, admin_user, db_session):
        terms = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        response = client.get("/api/me")
        data = response.json()
        assert data["needs_platform_terms_acceptance"] is True

    def test_me_accepted(self, client, admin_user, db_session):
        terms = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        acceptance = TermsAcceptance(
            user_id=admin_user.id,
            terms_of_service_id=terms.id,
        )
        db_session.add(acceptance)
        db_session.commit()

        response = client.get("/api/me")
        data = response.json()
        assert data["needs_platform_terms_acceptance"] is False


class TestPlatformEnforcement:
    def test_allows_access_when_no_terms_published(self, client):
        response = client.get("/api/admin/resources")
        assert response.status_code == 200

    def test_allows_access_when_terms_accepted(self, client, admin_user, db_session):
        terms = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        acceptance = TermsAcceptance(
            user_id=admin_user.id,
            terms_of_service_id=terms.id,
        )
        db_session.add(acceptance)
        db_session.commit()

        response = client.get("/api/admin/resources")
        assert response.status_code == 200

    def test_unauthenticated_still_blocked(self, anon_client):
        response = anon_client.get("/api/projects")
        assert response.status_code == 401


class TestVersionSupersession:
    def test_accepting_old_version_not_enough(self, client, admin_user, db_session):
        v1 = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="v1",
            content="First version.",
            published_by_id=admin_user.id,
        )
        db_session.add(v1)
        db_session.commit()

        v2 = TermsOfService(
            terms_type="platform",
            version="2.0.0",
            title="v2",
            content="Second version.",
            published_by_id=admin_user.id,
        )
        db_session.add(v2)
        db_session.commit()

        acceptance = TermsAcceptance(
            user_id=admin_user.id,
            terms_of_service_id=v1.id,
        )
        db_session.add(acceptance)
        db_session.commit()

        response = client.get("/api/admin/resources")
        assert response.status_code == 403

    def test_accepting_latest_version_works(self, client, admin_user, db_session):
        v1 = TermsOfService(
            terms_type="platform",
            version="1.0.0",
            title="v1",
            content="First version.",
            published_by_id=admin_user.id,
        )
        db_session.add(v1)
        db_session.commit()

        v2 = TermsOfService(
            terms_type="platform",
            version="2.0.0",
            title="v2",
            content="Second version.",
            published_by_id=admin_user.id,
        )
        db_session.add(v2)
        db_session.commit()

        acceptance = TermsAcceptance(
            user_id=admin_user.id,
            terms_of_service_id=v2.id,
        )
        db_session.add(acceptance)
        db_session.commit()

        response = client.get("/api/admin/resources")
        assert response.status_code == 200


class TestResourceAttachmentEnforcement:
    def test_blocked_without_resource_terms_acceptance(
        self, client, admin_user, data_resource, db_session
    ):
        terms = TermsOfService(
            terms_type="data_resource",
            data_resource_id=data_resource.id,
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        project = Project(name="Test Project", owner_id=admin_user.id)
        db_session.add(project)
        db_session.commit()
        membership = ProjectMembership(
            project_id=project.id,
            user_id=admin_user.id,
            created_by_id=admin_user.id,
        )
        db_session.add(membership)
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/resources",
            json={"resource_identifiers": [data_resource.identifier]},
        )
        assert response.status_code == 403
        assert "Terms not accepted" in response.json()["detail"]

    def test_allowed_after_acceptance(
        self, client, admin_user, data_resource, db_session
    ):
        terms = TermsOfService(
            terms_type="data_resource",
            data_resource_id=data_resource.id,
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        acceptance = TermsAcceptance(
            user_id=admin_user.id,
            terms_of_service_id=terms.id,
        )
        db_session.add(acceptance)
        db_session.commit()

        project = Project(name="Test Project", owner_id=admin_user.id)
        db_session.add(project)
        db_session.commit()
        membership = ProjectMembership(
            project_id=project.id,
            user_id=admin_user.id,
            created_by_id=admin_user.id,
        )
        db_session.add(membership)
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/resources",
            json={"resource_identifiers": [data_resource.identifier]},
        )
        assert response.status_code == 200


class TestBundleSubmissionEnforcement:
    def test_blocked_without_resource_terms_acceptance(
        self, client, admin_user, data_resource, db_session
    ):
        terms = TermsOfService(
            terms_type="data_resource",
            data_resource_id=data_resource.id,
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        project = Project(name="Test Project", owner_id=admin_user.id)
        db_session.add(project)
        db_session.commit()
        membership = ProjectMembership(
            project_id=project.id,
            user_id=admin_user.id,
            created_by_id=admin_user.id,
        )
        db_session.add(membership)
        db_session.commit()

        from app.models.execution_environment import ExecutionEnvironment

        env = ExecutionEnvironment(
            identifier="test-env",
            name="Test Env",
            runtime="python-3.13",
            status="active",
        )
        db_session.add(env)
        db_session.commit()

        from app.models.analysis_bundle import (
            AnalysisBundle,
            AnalysisBundleDataResource,
            AnalysisBundleStatus,
        )

        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=admin_user.id,
            execution_environment_id=env.id,
            name="Test Bundle",
            source_path="test",
            status=AnalysisBundleStatus.DRAFT.value,
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(bundle)
        db_session.flush()

        link = AnalysisBundleDataResource(
            analysis_bundle_id=bundle.id,
            data_resource_id=data_resource.id,
        )
        db_session.add(link)
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/bundles/{bundle.id}/submit",
        )
        assert response.status_code == 403
        assert "Terms not accepted" in response.json()["detail"]

    def test_allowed_after_acceptance(
        self, client, admin_user, data_resource, db_session
    ):
        terms = TermsOfService(
            terms_type="data_resource",
            data_resource_id=data_resource.id,
            version="1.0.0",
            title="T",
            content="C",
            published_by_id=admin_user.id,
        )
        db_session.add(terms)
        db_session.commit()

        acceptance = TermsAcceptance(
            user_id=admin_user.id,
            terms_of_service_id=terms.id,
        )
        db_session.add(acceptance)
        db_session.commit()

        project = Project(name="Test Project", owner_id=admin_user.id)
        db_session.add(project)
        db_session.commit()
        membership = ProjectMembership(
            project_id=project.id,
            user_id=admin_user.id,
            created_by_id=admin_user.id,
        )
        db_session.add(membership)
        db_session.commit()

        from app.models.execution_environment import ExecutionEnvironment

        env = ExecutionEnvironment(
            identifier="test-env",
            name="Test Env",
            runtime="python-3.13",
            status="active",
        )
        db_session.add(env)
        db_session.commit()

        from app.models.analysis_bundle import (
            AnalysisBundle,
            AnalysisBundleDataResource,
            AnalysisBundleStatus,
        )

        bundle = AnalysisBundle(
            project_id=project.id,
            created_by_id=admin_user.id,
            execution_environment_id=env.id,
            name="Test Bundle",
            source_path="test",
            status=AnalysisBundleStatus.DRAFT.value,
            version="1.0.0",
            entrypoint="run.py",
        )
        db_session.add(bundle)
        db_session.flush()

        link = AnalysisBundleDataResource(
            analysis_bundle_id=bundle.id,
            data_resource_id=data_resource.id,
        )
        db_session.add(link)
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/bundles/{bundle.id}/submit",
        )
        assert response.status_code == 200


class TestTermsAuditEvents:
    def test_all_terms_event_types_recorded(
        self, client, admin_user, data_resource, db_session
    ):
        client.post(
            "/api/admin/terms/platform",
            json={"version": "1.0.0", "title": "PT", "content": "C"},
        )

        client.post(
            f"/api/admin/resources/{data_resource.id}/terms/publish",
            json={"version": "1.0.0", "title": "DT", "content": "C"},
        )

        events = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.resource_type == "terms_of_service")
            .order_by(AuditEvent.occurred_at)
            .all()
        )

        event_types = [e.event_type for e in events]
        assert "platform_terms.published" in event_types
        assert "platform_terms.accepted" in event_types
        assert "dataset_terms.published" in event_types
        assert "dataset_terms.accepted" in event_types
        assert len(event_types) == 4
