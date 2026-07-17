import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.analysis_bundle import AnalysisBundle, AnalysisBundleStatus
from app.workflow.bundle import (
    approve_bundle,
    reject_bundle,
    submit_bundle,
    supersede_bundle,
)


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def draft_bundle():
    b = MagicMock(spec=AnalysisBundle)
    b.id = uuid.uuid4()
    b.status = AnalysisBundleStatus.DRAFT
    b.submitted_by_id = None
    b.submitted_at = None
    b.rejection_reason = None
    b.rejected_by_id = None
    b.rejected_at = None
    return b


@pytest.fixture
def submitted_bundle():
    b = MagicMock(spec=AnalysisBundle)
    b.id = uuid.uuid4()
    b.status = AnalysisBundleStatus.SUBMITTED
    b.submitted_by_id = uuid.uuid4()
    b.submitted_at = datetime.now(timezone.utc)
    b.rejection_reason = None
    b.rejected_by_id = None
    b.rejected_at = None
    return b


@pytest.fixture
def approved_bundle():
    b = MagicMock(spec=AnalysisBundle)
    b.id = uuid.uuid4()
    b.status = AnalysisBundleStatus.APPROVED_FOR_EXECUTION
    b.rejection_reason = None
    b.rejected_by_id = None
    b.rejected_at = None
    return b


class TestRejectBundle:
    def test_reject_from_submitted(self, mock_db, submitted_bundle):
        result = reject_bundle(
            mock_db,
            submitted_bundle,
            reason="Code uses unsafe external libraries",
            rejected_by_id=uuid.uuid4(),
        )
        assert result.status == AnalysisBundleStatus.REJECTED
        assert result.rejection_reason == "Code uses unsafe external libraries"
        assert result.rejected_by_id is not None
        assert result.rejected_at is not None

    def test_reject_strips_whitespace(self, mock_db, submitted_bundle):
        result = reject_bundle(
            mock_db,
            submitted_bundle,
            reason="  Needs better documentation  ",
            rejected_by_id=uuid.uuid4(),
        )
        assert result.rejection_reason == "Needs better documentation"

    def test_reject_reason_required(self, mock_db, submitted_bundle):
        with pytest.raises(ValueError, match="Rejection reason is required"):
            reject_bundle(
                mock_db, submitted_bundle, reason="", rejected_by_id=uuid.uuid4()
            )

    def test_reject_reason_whitespace_only(self, mock_db, submitted_bundle):
        with pytest.raises(ValueError, match="Rejection reason is required"):
            reject_bundle(
                mock_db, submitted_bundle, reason="   ", rejected_by_id=uuid.uuid4()
            )

    def test_reject_from_draft_fails(self, mock_db, draft_bundle):
        with pytest.raises(ValueError, match="Cannot reject bundle in state: draft"):
            reject_bundle(
                mock_db, draft_bundle, reason="Not ready", rejected_by_id=uuid.uuid4()
            )

    def test_reject_from_approved_fails(self, mock_db, approved_bundle):
        with pytest.raises(
            ValueError, match="Cannot reject bundle in state: approved_for_execution"
        ):
            reject_bundle(
                mock_db,
                approved_bundle,
                reason="Not ready",
                rejected_by_id=uuid.uuid4(),
            )

    def test_reject_sets_provenance(self, mock_db, submitted_bundle):
        rejected_by = uuid.uuid4()
        result = reject_bundle(
            mock_db,
            submitted_bundle,
            reason="Missing required outputs",
            rejected_by_id=rejected_by,
        )
        assert result.rejected_by_id == rejected_by
        assert isinstance(result.rejected_at, datetime)


class TestSubmitBundle:
    def test_submit_from_draft(self, mock_db, draft_bundle):
        user_id = uuid.uuid4()
        result = submit_bundle(mock_db, draft_bundle, submitted_by_id=user_id)
        assert result.status == AnalysisBundleStatus.SUBMITTED
        assert result.submitted_by_id == user_id
        assert result.submitted_at is not None

    def test_submit_from_submitted_fails(self, mock_db, submitted_bundle):
        with pytest.raises(
            ValueError, match="Cannot submit bundle in state: submitted"
        ):
            submit_bundle(mock_db, submitted_bundle, submitted_by_id=uuid.uuid4())


class TestApproveBundle:
    def test_approve_from_submitted(self, mock_db, submitted_bundle):
        result = approve_bundle(mock_db, submitted_bundle)
        assert result.status == AnalysisBundleStatus.APPROVED_FOR_EXECUTION

    def test_approve_from_draft_fails(self, mock_db, draft_bundle):
        with pytest.raises(ValueError, match="Cannot approve bundle in state: draft"):
            approve_bundle(mock_db, draft_bundle)


class TestSupersedeBundle:
    def test_supersede_from_approved(self, mock_db, approved_bundle):
        result = supersede_bundle(mock_db, approved_bundle)
        assert result.status == AnalysisBundleStatus.SUPERSEDED

    def test_supersede_from_submitted_fails(self, mock_db, submitted_bundle):
        with pytest.raises(
            ValueError, match="Cannot supersede bundle in state: submitted"
        ):
            supersede_bundle(mock_db, submitted_bundle)
