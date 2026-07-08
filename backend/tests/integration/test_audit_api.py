"""Integration tests for the audit event query API."""

import uuid

from app.models.audit_event import AuditEvent, AuditEventType
from app.services.audit_service import create_audit_event


def _seed_audit_events(db_session, user_id, project_id):
    events = [
        AuditEvent(
            event_type=AuditEventType.PROJECT_CREATED.value,
            actor_id=user_id,
            project_id=project_id,
            resource_type="project",
            resource_id=project_id,
            event_metadata={"project_name": "Test Project"},
        ),
        AuditEvent(
            event_type=AuditEventType.BUNDLE_SUBMITTED.value,
            actor_id=user_id,
            project_id=project_id,
            resource_type="analysis_bundle",
            resource_id=uuid.uuid4(),
            event_metadata={"bundle_name": "Analysis v1"},
        ),
        AuditEvent(
            event_type=AuditEventType.BUNDLE_APPROVED.value,
            actor_id=user_id,
            project_id=project_id,
            resource_type="analysis_bundle",
            resource_id=uuid.uuid4(),
            event_metadata={"bundle_name": "Analysis v2"},
        ),
    ]
    for e in events:
        db_session.add(e)
    db_session.commit()


class TestAuditEventQuery:
    def test_list_all_events(self, db_session, admin_user, client):
        _seed_audit_events(db_session, admin_user.id, uuid.uuid4())

        response = client.get("/api/admin/audit-events")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_filter_by_event_type(self, db_session, admin_user, client):
        project_id = uuid.uuid4()
        _seed_audit_events(db_session, admin_user.id, project_id)

        response = client.get(
            "/api/admin/audit-events", params={"event_type": "bundle.submitted"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["event_type"] == "bundle.submitted"

    def test_filter_by_project_id(self, db_session, admin_user, client):
        project_a = uuid.uuid4()
        project_b = uuid.uuid4()
        _seed_audit_events(db_session, admin_user.id, project_a)
        _seed_audit_events(db_session, admin_user.id, project_b)

        response = client.get(
            "/api/admin/audit-events", params={"project_id": str(project_a)}
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["project_id"] == str(project_a)

    def test_filter_by_actor(self, db_session, admin_user, client, moderator_user):
        project_id = uuid.uuid4()
        _seed_audit_events(db_session, admin_user.id, project_id)
        _seed_audit_events(db_session, moderator_user.id, project_id)

        response = client.get(
            "/api/admin/audit-events", params={"actor_id": str(admin_user.id)}
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["actor_id"] == str(admin_user.id)

    def test_filter_by_resource(self, db_session, admin_user, client):
        project_id = uuid.uuid4()
        bundle_id = uuid.uuid4()

        db_session.add(
            AuditEvent(
                event_type=AuditEventType.BUNDLE_APPROVED.value,
                actor_id=admin_user.id,
                project_id=project_id,
                resource_type="analysis_bundle",
                resource_id=bundle_id,
            )
        )
        db_session.commit()

        response = client.get(
            "/api/admin/audit-events",
            params={
                "resource_type": "analysis_bundle",
                "resource_id": str(bundle_id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["resource_id"] == str(bundle_id)

    def test_pagination(self, db_session, admin_user, client):
        project_id = uuid.uuid4()
        for i in range(5):
            db_session.add(
                AuditEvent(
                    event_type=AuditEventType.PROJECT_CREATED.value,
                    actor_id=admin_user.id,
                    project_id=project_id,
                    resource_type="project",
                    resource_id=project_id,
                    event_metadata={"project_name": f"Project {i}"},
                )
            )
        db_session.commit()

        response = client.get(
            "/api/admin/audit-events", params={"limit": 2, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_actor_info_returned(self, db_session, admin_user, client):
        project_id = uuid.uuid4()
        create_audit_event(
            db_session,
            event_type=AuditEventType.PROJECT_CREATED,
            actor_id=admin_user.id,
            project_id=project_id,
            resource_type="project",
            resource_id=project_id,
            metadata={"project_name": "Test"},
        )
        db_session.commit()

        response = client.get("/api/admin/audit-events")

        assert response.status_code == 200
        data = response.json()
        item = data["items"][0]
        assert item["actor_id"] == str(admin_user.id)
        assert item["actor_display_name"] == admin_user.display_name
        assert item["actor_email"] == admin_user.email

    def test_unauthenticated_user_rejected(self, anon_client):
        response = anon_client.get("/api/admin/audit-events")
        assert response.status_code == 401

    def test_unauthorised_researcher_rejected(self, db_session, researcher_client):
        response = researcher_client.get("/api/admin/audit-events")
        assert response.status_code == 403
