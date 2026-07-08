import uuid
from unittest.mock import MagicMock

import pytest

from app.models.audit_event import AuditEvent, AuditEventType
from app.services.audit_service import create_audit_event


class TestCreateAuditEvent:
    def test_creates_event_with_all_fields(self):
        db = MagicMock()
        actor_id = uuid.uuid4()
        project_id = uuid.uuid4()
        resource_id = uuid.uuid4()

        event = create_audit_event(
            db,
            event_type=AuditEventType.BUNDLE_APPROVED,
            actor_id=actor_id,
            project_id=project_id,
            resource_type="analysis_bundle",
            resource_id=resource_id,
            metadata={"bundle_name": "Survival Analysis"},
        )

        assert isinstance(event, AuditEvent)
        assert event.event_type == "bundle.approved"
        assert event.actor_id == actor_id
        assert event.project_id == project_id
        assert event.resource_type == "analysis_bundle"
        assert event.resource_id == resource_id
        assert event.event_metadata == {"bundle_name": "Survival Analysis"}
        db.add.assert_called_once_with(event)

    def test_accepts_string_event_type(self):
        db = MagicMock()
        resource_id = uuid.uuid4()

        event = create_audit_event(
            db,
            event_type="project.created",
            actor_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            resource_type="project",
            resource_id=resource_id,
        )

        assert event.event_type == "project.created"

    def test_invalid_string_event_type_raises(self):
        db = MagicMock()
        with pytest.raises(ValueError, match="not a valid AuditEventType"):
            create_audit_event(
                db,
                event_type="invalid.event",
                actor_id=uuid.uuid4(),
                resource_type="project",
                resource_id=uuid.uuid4(),
            )

    def test_defaults_metadata_to_empty_dict(self):
        db = MagicMock()
        resource_id = uuid.uuid4()

        event = create_audit_event(
            db,
            event_type=AuditEventType.EXECUTION_COMPLETED,
            actor_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            resource_type="execution_request",
            resource_id=resource_id,
        )

        assert event.event_metadata == {}

    def test_defaults_metadata_from_none(self):
        db = MagicMock()
        resource_id = uuid.uuid4()

        event = create_audit_event(
            db,
            event_type=AuditEventType.EXECUTION_COMPLETED,
            actor_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            resource_type="execution_request",
            resource_id=resource_id,
            metadata=None,
        )

        assert event.event_metadata == {}

    def test_nullable_project_id(self):
        db = MagicMock()

        event = create_audit_event(
            db,
            event_type=AuditEventType.USER_CREATED,
            actor_id=uuid.uuid4(),
            resource_type="user",
            resource_id=uuid.uuid4(),
        )

        assert event.project_id is None

    def test_does_not_commit(self):
        db = MagicMock()
        create_audit_event(
            db,
            event_type=AuditEventType.BUNDLE_CREATED,
            actor_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            resource_type="analysis_bundle",
            resource_id=uuid.uuid4(),
        )
        db.add.assert_called_once()
        db.commit.assert_not_called()
