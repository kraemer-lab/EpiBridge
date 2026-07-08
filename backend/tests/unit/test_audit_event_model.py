import uuid

from app.models.audit_event import AuditEvent, AuditEventType


class TestAuditEventType:
    def test_values(self):
        assert AuditEventType.PROJECT_CREATED.value == "project.created"
        assert AuditEventType.PROJECT_MEMBER_ADDED.value == "project.member.added"
        assert AuditEventType.PROJECT_MEMBER_REMOVED.value == "project.member.removed"
        assert (
            AuditEventType.PROJECT_RESOURCE_ALLOCATED.value
            == "project.resource.allocated"
        )
        assert (
            AuditEventType.PROJECT_RESOURCE_DEALLOCATED.value
            == "project.resource.deallocated"
        )

        assert AuditEventType.BUNDLE_CREATED.value == "bundle.created"
        assert AuditEventType.BUNDLE_SUBMITTED.value == "bundle.submitted"
        assert AuditEventType.BUNDLE_APPROVED.value == "bundle.approved"
        assert AuditEventType.BUNDLE_REJECTED.value == "bundle.rejected"
        assert AuditEventType.BUNDLE_SUPERSEDED.value == "bundle.superseded"

        assert AuditEventType.EXECUTION_REQUESTED.value == "execution.requested"
        assert AuditEventType.EXECUTION_STARTED.value == "execution.started"
        assert AuditEventType.EXECUTION_COMPLETED.value == "execution.completed"
        assert AuditEventType.EXECUTION_FAILED.value == "execution.failed"
        assert AuditEventType.EXECUTION_CANCELLED.value == "execution.cancelled"

        assert AuditEventType.OUTPUT_SET_CREATED.value == "output_set.created"
        assert AuditEventType.OUTPUT_SET_APPROVED.value == "output_set.approved"
        assert AuditEventType.OUTPUT_SET_REJECTED.value == "output_set.rejected"
        assert AuditEventType.OUTPUT_SET_RELEASED.value == "output_set.released"

        assert AuditEventType.USER_CREATED.value == "user.created"

    def test_from_string(self):
        assert AuditEventType("project.created") == AuditEventType.PROJECT_CREATED
        assert (
            AuditEventType("execution.completed") == AuditEventType.EXECUTION_COMPLETED
        )

    def test_unique_values(self):
        values = [e.value for e in AuditEventType]
        assert len(values) == len(set(values))


class TestAuditEventModel:
    def test_create_event(self):
        actor_id = uuid.uuid4()
        project_id = uuid.uuid4()
        resource_id = uuid.uuid4()

        event = AuditEvent(
            event_type=AuditEventType.BUNDLE_SUBMITTED.value,
            actor_id=actor_id,
            project_id=project_id,
            resource_type="analysis_bundle",
            resource_id=resource_id,
            event_metadata={"bundle_name": "Test Analysis"},
        )

        assert event.event_type == "bundle.submitted"
        assert event.actor_id == actor_id
        assert event.project_id == project_id
        assert event.resource_type == "analysis_bundle"
        assert event.resource_id == resource_id
        assert event.event_metadata == {"bundle_name": "Test Analysis"}

    def test_nullable_project_id(self):
        event = AuditEvent(
            event_type=AuditEventType.USER_CREATED.value,
            actor_id=uuid.uuid4(),
            resource_type="user",
            resource_id=uuid.uuid4(),
        )
        assert event.project_id is None

    def test_accepts_event_metadata(self):
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_COMPLETED.value,
            actor_id=uuid.uuid4(),
            resource_type="execution_request",
            resource_id=uuid.uuid4(),
            event_metadata={"duration_seconds": 42},
        )
        assert event.event_metadata == {"duration_seconds": 42}
