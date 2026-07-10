import uuid
from unittest.mock import MagicMock

import pytest

from app.models.audit_event import AuditEventType
from app.models.data_resource import DataResource
from app.models.terms_acceptance import TermsAcceptance
from app.models.terms_of_service import TermsOfService
from app.models.user import User
from app.services import terms_service as svc


def _mock_user() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    return user


def _mock_terms(**kwargs) -> MagicMock:
    terms = MagicMock(spec=TermsOfService)
    terms.id = kwargs.get("id", uuid.uuid4())
    terms.terms_type = kwargs.get("terms_type", "platform")
    terms.data_resource_id = kwargs.get("data_resource_id", None)
    terms.version = kwargs.get("version", "1.0.0")
    terms.title = kwargs.get("title", "Test Terms")
    terms.content = kwargs.get("content", "Test content.")
    terms.published_by_id = kwargs.get("published_by_id", uuid.uuid4())
    terms.published_at = None
    return terms


class TestPublishPlatformTerms:
    def test_creates_terms_of_service_record(self):
        db = MagicMock()
        admin = _mock_user()
        db.query.return_value.filter.return_value.first.return_value = None

        result = svc.publish_platform_terms(
            db,
            published_by=admin,
            title="Platform Terms",
            content="Terms content.",
            version="1.0.0",
        )

        assert isinstance(result, TermsOfService)
        assert result.terms_type == "platform"
        assert result.version == "1.0.0"
        assert result.title == "Platform Terms"
        assert result.content == "Terms content."
        assert result.published_by_id == admin.id

    def test_adds_terms_to_session(self):
        db = MagicMock()
        admin = _mock_user()
        db.query.return_value.filter.return_value.first.return_value = None

        svc.publish_platform_terms(
            db, published_by=admin, title="T", content="C", version="1.0.0"
        )

        terms_added = any(
            isinstance(call_args[0][0], TermsOfService)
            for call_args in db.add.call_args_list
        )
        assert terms_added, "No TermsOfService was added to the session"

    def test_creates_acceptance_for_admin(self):
        db = MagicMock()
        admin = _mock_user()
        db.query.return_value.filter.return_value.first.return_value = None

        svc.publish_platform_terms(
            db, published_by=admin, title="T", content="C", version="1.0.0"
        )

        acceptance_added = any(
            isinstance(call_args[0][0], TermsAcceptance)
            for call_args in db.add.call_args_list
        )
        assert acceptance_added, "Admin should have an acceptance record created"

    def test_creates_publish_audit_event(self):
        db = MagicMock()
        admin = _mock_user()
        db.query.return_value.filter.return_value.first.return_value = None

        svc.publish_platform_terms(
            db, published_by=admin, title="T", content="C", version="1.0.0"
        )

        audit_events = [
            call_args[0][0]
            for call_args in db.add.call_args_list
            if call_args[0][0].__class__.__name__ == "AuditEvent"
        ]
        assert len(audit_events) == 2
        event_types = {e.event_type for e in audit_events}
        assert AuditEventType.PLATFORM_TERMS_PUBLISHED.value in event_types
        assert AuditEventType.PLATFORM_TERMS_ACCEPTED.value in event_types

    def test_commits_transaction(self):
        db = MagicMock()
        admin = _mock_user()
        db.query.return_value.filter.return_value.first.return_value = None

        svc.publish_platform_terms(
            db, published_by=admin, title="T", content="C", version="1.0.0"
        )

        db.commit.assert_called_once()
        db.flush.assert_called()


class TestPublishResourceTerms:
    def test_creates_terms_of_service_record(self):
        db = MagicMock()
        admin = _mock_user()
        resource_id = uuid.uuid4()

        mock_resource = MagicMock(spec=DataResource)
        mock_resource.id = resource_id
        db.query.return_value.filter.return_value.first.side_effect = [
            mock_resource,
            None,
        ]

        result = svc.publish_resource_terms(
            db,
            published_by=admin,
            data_resource_id=resource_id,
            title="Dataset Terms",
            content="Dataset content.",
            version="2.0.0",
        )

        assert isinstance(result, TermsOfService)
        assert result.terms_type == "data_resource"
        assert result.data_resource_id == resource_id
        assert result.version == "2.0.0"
        assert result.published_by_id == admin.id

    def test_raises_for_missing_data_resource(self):
        db = MagicMock()
        admin = _mock_user()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Data resource not found"):
            svc.publish_resource_terms(
                db,
                published_by=admin,
                data_resource_id=uuid.uuid4(),
                title="T",
                content="C",
                version="1.0.0",
            )

    def test_creates_dataset_audit_event(self):
        db = MagicMock()
        admin = _mock_user()
        resource_id = uuid.uuid4()

        mock_resource = MagicMock(spec=DataResource)
        mock_resource.id = resource_id
        db.query.return_value.filter.return_value.first.side_effect = [
            mock_resource,
            None,
        ]

        svc.publish_resource_terms(
            db,
            published_by=admin,
            data_resource_id=resource_id,
            title="T",
            content="C",
            version="1.0.0",
        )

        audit_events = [
            call_args[0][0]
            for call_args in db.add.call_args_list
            if call_args[0][0].__class__.__name__ == "AuditEvent"
        ]
        event_types = {e.event_type for e in audit_events}
        assert AuditEventType.DATASET_TERMS_PUBLISHED.value in event_types
        assert AuditEventType.DATASET_TERMS_ACCEPTED.value in event_types

    def test_commits_transaction(self):
        db = MagicMock()
        admin = _mock_user()
        resource_id = uuid.uuid4()

        mock_resource = MagicMock(spec=DataResource)
        mock_resource.id = resource_id
        db.query.return_value.filter.return_value.first.side_effect = [
            mock_resource,
            None,
        ]

        svc.publish_resource_terms(
            db,
            published_by=admin,
            data_resource_id=resource_id,
            title="T",
            content="C",
            version="1.0.0",
        )

        db.commit.assert_called_once()


class TestAcceptTerms:
    def test_creates_acceptance_record(self):
        db = MagicMock()
        user = _mock_user()
        terms = _mock_terms()
        db.query.return_value.filter.return_value.first.return_value = None

        result = svc.accept_terms(db, user=user, terms_of_service=terms)

        assert isinstance(result, TermsAcceptance)
        assert result.user_id == user.id
        assert result.terms_of_service_id == terms.id

    def test_idempotent_returns_existing(self):
        db = MagicMock()
        user = _mock_user()
        terms = _mock_terms()

        existing = MagicMock(spec=TermsAcceptance)
        existing.user_id = user.id
        existing.terms_of_service_id = terms.id
        db.query.return_value.filter.return_value.first.return_value = existing

        result = svc.accept_terms(db, user=user, terms_of_service=terms)

        assert result is existing
        db.add.assert_not_called()

    def test_creates_acceptance_audit_event(self):
        db = MagicMock()
        user = _mock_user()
        terms = _mock_terms()
        db.query.return_value.filter.return_value.first.return_value = None

        svc.accept_terms(db, user=user, terms_of_service=terms)

        audit_events = [
            call_args[0][0]
            for call_args in db.add.call_args_list
            if call_args[0][0].__class__.__name__ == "AuditEvent"
        ]
        assert len(audit_events) == 1
        assert audit_events[0].actor_id == user.id
        assert audit_events[0].resource_id == terms.id

    def test_platform_terms_uses_platform_accepted_event(self):
        db = MagicMock()
        user = _mock_user()
        terms = _mock_terms(terms_type="platform")
        db.query.return_value.filter.return_value.first.return_value = None

        svc.accept_terms(db, user=user, terms_of_service=terms)

        audit_events = [
            call_args[0][0]
            for call_args in db.add.call_args_list
            if call_args[0][0].__class__.__name__ == "AuditEvent"
        ]
        assert audit_events[0].event_type == "platform_terms.accepted"

    def test_dataset_terms_uses_dataset_accepted_event(self):
        db = MagicMock()
        user = _mock_user()
        terms = _mock_terms(
            terms_type="data_resource",
            data_resource_id=uuid.uuid4(),
        )
        db.query.return_value.filter.return_value.first.return_value = None

        svc.accept_terms(db, user=user, terms_of_service=terms)

        audit_events = [
            call_args[0][0]
            for call_args in db.add.call_args_list
            if call_args[0][0].__class__.__name__ == "AuditEvent"
        ]
        assert audit_events[0].event_type == "dataset_terms.accepted"

    def test_does_not_commit(self):
        db = MagicMock()
        user = _mock_user()
        terms = _mock_terms()
        db.query.return_value.filter.return_value.first.return_value = None

        svc.accept_terms(db, user=user, terms_of_service=terms)

        db.commit.assert_not_called()


class TestGetCurrentPlatformTerms:
    def _mock_query_first(self, db, value):
        q = db.query.return_value.filter.return_value.order_by.return_value
        q.first.return_value = value

    def test_returns_latest_when_terms_exist(self):
        db = MagicMock()
        expected = _mock_terms(version="2.0.0")
        self._mock_query_first(db, expected)

        result = svc.get_current_platform_terms(db)

        assert result is expected
        assert result.version == "2.0.0"

    def test_returns_none_when_no_terms(self):
        db = MagicMock()
        self._mock_query_first(db, None)

        result = svc.get_current_platform_terms(db)

        assert result is None

    def test_queries_platform_terms_only(self):
        db = MagicMock()
        self._mock_query_first(db, _mock_terms())

        svc.get_current_platform_terms(db)

        filter_args = db.query.return_value.filter.call_args
        assert filter_args is not None


class TestGetCurrentResourceTerms:
    def _mock_query_first(self, db, value):
        q = db.query.return_value.filter.return_value.order_by.return_value
        q.first.return_value = value

    def test_returns_latest_for_resource(self):
        db = MagicMock()
        resource_id = uuid.uuid4()
        expected = _mock_terms(
            terms_type="data_resource",
            data_resource_id=resource_id,
        )
        self._mock_query_first(db, expected)

        result = svc.get_current_resource_terms(db, resource_id)

        assert result is expected

    def test_returns_none_when_resource_has_no_terms(self):
        db = MagicMock()
        self._mock_query_first(db, None)

        result = svc.get_current_resource_terms(db, uuid.uuid4())

        assert result is None


class TestHasAcceptedLatest:
    def test_returns_true_when_accepted(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = MagicMock(
            spec=TermsAcceptance
        )

        result = svc.has_accepted_latest(
            db, user_id=uuid.uuid4(), terms_of_service_id=uuid.uuid4()
        )

        assert result is True

    def test_returns_false_when_not_accepted(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = svc.has_accepted_latest(
            db, user_id=uuid.uuid4(), terms_of_service_id=uuid.uuid4()
        )

        assert result is False


class TestGetAcceptanceStatus:
    def _ordered_first(self, db, value):
        q = db.query.return_value.filter.return_value.order_by.return_value
        q.first.return_value = value

    def _distinct_all(self, db, rows):
        q = db.query.return_value.filter.return_value.distinct.return_value
        q.all.return_value = rows

    def test_returns_platform_status_when_no_terms(self):
        db = MagicMock()
        user_id = uuid.uuid4()

        self._ordered_first(db, None)
        self._distinct_all(db, [])

        status = svc.get_acceptance_status(db, user_id)

        assert status["platform"]["has_terms"] is False
        assert status["platform"]["version"] is None
        assert status["platform"]["accepted"] is False
        assert status["dataset_terms"] == []

    def test_returns_platform_status_when_not_accepted(self):
        db = MagicMock()
        user_id = uuid.uuid4()
        platform_terms = _mock_terms(terms_type="platform", version="1.0.0")

        self._ordered_first(db, platform_terms)
        db.query.return_value.filter.return_value.first.return_value = None
        self._distinct_all(db, [])

        status = svc.get_acceptance_status(db, user_id)

        assert status["platform"]["has_terms"] is True
        assert status["platform"]["version"] == "1.0.0"
        assert status["platform"]["accepted"] is False

    def test_returns_platform_status_when_accepted(self):
        db = MagicMock()
        user_id = uuid.uuid4()
        platform_terms = _mock_terms(terms_type="platform", version="1.0.0")

        self._ordered_first(db, platform_terms)
        db.query.return_value.filter.return_value.first.return_value = MagicMock(
            spec=TermsAcceptance
        )
        self._distinct_all(db, [])

        status = svc.get_acceptance_status(db, user_id)

        assert status["platform"]["has_terms"] is True
        assert status["platform"]["version"] == "1.0.0"
        assert status["platform"]["accepted"] is True

    def test_includes_dataset_terms(self):
        db = MagicMock()
        user_id = uuid.uuid4()
        resource_id = uuid.uuid4()
        resource_terms = _mock_terms(
            terms_type="data_resource",
            data_resource_id=resource_id,
            version="1.0.0",
            title="Resource Terms",
        )

        q = db.query.return_value.filter.return_value.order_by.return_value
        q.first.side_effect = [None, resource_terms]
        db.query.return_value.filter.return_value.first.return_value = None
        self._distinct_all(db, [(resource_id,)])

        status = svc.get_acceptance_status(db, user_id)

        assert len(status["dataset_terms"]) == 1
        entry = status["dataset_terms"][0]
        assert entry["resource_id"] == str(resource_id)
        assert entry["version"] == "1.0.0"
        assert entry["accepted"] is False
