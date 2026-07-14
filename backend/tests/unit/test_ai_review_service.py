import uuid
from unittest.mock import MagicMock, patch

from app.models.ai_bundle_review import AIBundleReview
from app.models.analysis_bundle import AnalysisBundle
from app.services.ai_review_service import get_review, perform_review, request_review


class TestRequestReview:
    def test_creates_pending_review(self):
        bundle_id = uuid.uuid4()
        mock_bundle = MagicMock(spec=AnalysisBundle)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,
            mock_bundle,
        ]

        with patch("app.services.ai_review_service.SessionLocal", return_value=mock_db):
            request_review(bundle_id)

        mock_db.add.assert_called_once()
        review = mock_db.add.call_args[0][0]
        assert isinstance(review, AIBundleReview)
        assert review.bundle_id == bundle_id
        assert review.status == "pending"
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    def test_resets_existing_review(self):
        bundle_id = uuid.uuid4()
        existing = AIBundleReview(
            bundle_id=bundle_id,
            status="completed",
            summary="Old summary",
            assessment="Old assessment",
            assessment_confidence="High",
            reviewer_notes="Old notes",
        )

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        with patch("app.services.ai_review_service.SessionLocal", return_value=mock_db):
            request_review(bundle_id)

        mock_db.add.assert_not_called()
        assert existing.status == "pending"
        assert existing.summary is None
        assert existing.assessment is None
        assert existing.assessment_confidence is None
        assert existing.reviewer_notes is None
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    def test_handles_missing_bundle_gracefully(self):
        bundle_id = uuid.uuid4()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [None, None]

        with patch("app.services.ai_review_service.SessionLocal", return_value=mock_db):
            request_review(bundle_id)

        mock_db.add.assert_not_called()
        mock_db.close.assert_called_once()

    def test_rollback_on_error(self):
        bundle_id = uuid.uuid4()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = Exception(
            "db error"
        )

        with patch("app.services.ai_review_service.SessionLocal", return_value=mock_db):
            request_review(bundle_id)

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()


class TestPerformReview:
    def _mock_bundle(self):
        b = MagicMock()
        b.entrypoint = "run.py"
        b.execution_environment = MagicMock()
        b.execution_environment.runtime = "python-3.13"
        b.data_resources = []
        return b

    def test_completed_status_on_success(self):
        bundle_id = uuid.uuid4()
        review = AIBundleReview(bundle_id=bundle_id, status="pending")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            review,
            self._mock_bundle(),
        ]

        mock_provider = MagicMock()
        mock_provider.review.return_value.summary = "Test summary"
        mock_provider.review.return_value.assessment = "Appears appropriate"
        mock_provider.review.return_value.assessment_confidence = "High"
        mock_provider.review.return_value.reviewer_notes = "None detected."
        mock_provider.review.return_value.is_unavailable = False

        patchers = [
            patch("app.services.ai_review_service.SessionLocal", return_value=mock_db),
            patch(
                "app.services.ai_review_service.get_ai_provider",
                return_value=mock_provider,
            ),
            patch("app.services.ai_review_service.get_bundle_store"),
            patch(
                "app.services.ai_review_service.get_setting_bool",
                return_value=True,
            ),
        ]
        for p in patchers:
            p.start()

        perform_review(bundle_id)

        for p in patchers:
            p.stop()

        assert review.status == "completed"
        assert review.summary == "Test summary"
        assert review.assessment == "Appears appropriate"
        assert review.assessment_confidence == "High"
        assert review.reviewer_notes == "None detected."
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    def test_unavailable_when_provider_returns_unavailable(self):
        bundle_id = uuid.uuid4()
        review = AIBundleReview(bundle_id=bundle_id, status="pending")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            review,
            self._mock_bundle(),
        ]

        mock_provider = MagicMock()
        mock_provider.review.return_value.is_unavailable = True
        mock_provider.review.return_value.errors = ["AI provider unreachable"]

        patchers = [
            patch("app.services.ai_review_service.SessionLocal", return_value=mock_db),
            patch(
                "app.services.ai_review_service.get_ai_provider",
                return_value=mock_provider,
            ),
            patch("app.services.ai_review_service.get_bundle_store"),
            patch(
                "app.services.ai_review_service.get_setting_bool",
                return_value=True,
            ),
        ]
        for p in patchers:
            p.start()

        perform_review(bundle_id)

        for p in patchers:
            p.stop()

        assert review.status == "unavailable"
        assert review.summary is None
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    def test_unavailable_when_review_disabled(self):
        bundle_id = uuid.uuid4()
        review = AIBundleReview(bundle_id=bundle_id, status="pending")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = review

        with (
            patch("app.services.ai_review_service.SessionLocal", return_value=mock_db),
            patch(
                "app.services.ai_review_service.get_setting_bool",
                return_value=False,
            ),
        ):
            perform_review(bundle_id)

        assert review.status == "unavailable"
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    def test_failed_on_exception(self):
        bundle_id = uuid.uuid4()
        review = AIBundleReview(bundle_id=bundle_id, status="pending")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            review,
            review,
        ]

        with (
            patch("app.services.ai_review_service.SessionLocal", return_value=mock_db),
            patch(
                "app.services.ai_review_service.get_ai_provider",
                side_effect=Exception("boom"),
            ),
            patch(
                "app.services.ai_review_service.get_setting_bool",
                return_value=True,
            ),
        ):
            perform_review(bundle_id)

        assert review.status == "failed"
        mock_db.close.assert_called_once()

    def test_handles_missing_review(self):
        bundle_id = uuid.uuid4()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.ai_review_service.SessionLocal", return_value=mock_db):
            perform_review(bundle_id)

        mock_db.commit.assert_not_called()
        mock_db.close.assert_called_once()


class TestGetReview:
    def test_returns_review(self):
        bundle_id = uuid.uuid4()
        review = AIBundleReview(bundle_id=bundle_id, status="completed")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = review

        result = get_review(mock_db, bundle_id)
        assert result is review

    def test_returns_none_when_not_found(self):
        bundle_id = uuid.uuid4()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_review(mock_db, bundle_id)
        assert result is None
