import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models.output_set import OutputSet, OutputSetStatus
from app.workflow.output_set import (
    approve_output_set,
    reject_output_set,
    release_output_set,
)


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def pending_output_set():
    s = MagicMock(spec=OutputSet)
    s.id = uuid.uuid4()
    s.status = OutputSetStatus.PENDING_REVIEW
    s.rejection_reason = None
    s.rejected_by_id = None
    s.rejected_at = None
    return s


@pytest.fixture
def approved_output_set():
    s = MagicMock(spec=OutputSet)
    s.id = uuid.uuid4()
    s.status = OutputSetStatus.APPROVED
    s.release_package_path = None
    s.release_package_size = None
    return s


class TestRejectOutputSet:
    def test_reject_from_pending(self, mock_db, pending_output_set):
        result = reject_output_set(
            mock_db,
            pending_output_set,
            reason="Outputs contain PII",
            rejected_by_id=uuid.uuid4(),
        )
        assert result.status == OutputSetStatus.REJECTED
        assert result.rejection_reason == "Outputs contain PII"
        assert result.rejected_by_id is not None
        assert result.rejected_at is not None

    def test_reject_strips_whitespace(self, mock_db, pending_output_set):
        result = reject_output_set(
            mock_db,
            pending_output_set,
            reason="  Unverifiable results  ",
            rejected_by_id=uuid.uuid4(),
        )
        assert result.rejection_reason == "Unverifiable results"

    def test_reject_reason_required(self, mock_db, pending_output_set):
        with pytest.raises(ValueError, match="Rejection reason is required"):
            reject_output_set(
                mock_db, pending_output_set, reason="", rejected_by_id=uuid.uuid4()
            )

    def test_reject_reason_whitespace_only(self, mock_db, pending_output_set):
        with pytest.raises(ValueError, match="Rejection reason is required"):
            reject_output_set(
                mock_db, pending_output_set, reason="   ", rejected_by_id=uuid.uuid4()
            )

    def test_reject_from_approved_fails(self, mock_db, approved_output_set):
        with pytest.raises(
            ValueError, match="Cannot reject output set in state: approved"
        ):
            reject_output_set(
                mock_db,
                approved_output_set,
                reason="Not right",
                rejected_by_id=uuid.uuid4(),
            )

    def test_reject_sets_provenance(self, mock_db, pending_output_set):
        rejected_by = uuid.uuid4()
        result = reject_output_set(
            mock_db,
            pending_output_set,
            reason="Outputs incomplete",
            rejected_by_id=rejected_by,
        )
        assert result.rejected_by_id == rejected_by
        assert isinstance(result.rejected_at, datetime)


class TestApproveOutputSet:
    def test_approve_from_pending(self, mock_db, pending_output_set):
        result = approve_output_set(mock_db, pending_output_set)
        assert result.status == OutputSetStatus.APPROVED

    def test_approve_from_approved_fails(self, mock_db, approved_output_set):
        with pytest.raises(
            ValueError, match="Cannot approve output set in state: approved"
        ):
            approve_output_set(mock_db, approved_output_set)


class TestReleaseOutputSet:
    @patch("app.workflow.output_set.create_release_package")
    def test_release_from_approved(
        self, mock_create_release_package, mock_db, approved_output_set
    ):
        result = release_output_set(mock_db, approved_output_set)
        assert result.status == OutputSetStatus.RELEASED
        mock_create_release_package.assert_called_once_with(approved_output_set)

    def test_release_from_pending_fails(self, mock_db, pending_output_set):
        with pytest.raises(
            ValueError, match="Cannot release output set in state: pending_review"
        ):
            release_output_set(mock_db, pending_output_set)
