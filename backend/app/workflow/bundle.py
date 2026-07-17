import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.analysis_bundle import AnalysisBundle, AnalysisBundleStatus
from app.services.environment_builder_service import ensure_build_request

logger = logging.getLogger("workflow.bundle")


def submit_bundle(
    db: Session,
    bundle: AnalysisBundle,
    submitted_by_id: uuid.UUID | None = None,
) -> AnalysisBundle:
    if bundle.status != AnalysisBundleStatus.DRAFT:
        raise ValueError(f"Cannot submit bundle in state: {bundle.status.value}")
    bundle.status = AnalysisBundleStatus.SUBMITTED
    bundle.submitted_by_id = submitted_by_id
    bundle.submitted_at = datetime.now(timezone.utc)
    return bundle


def approve_bundle(db: Session, bundle: AnalysisBundle) -> AnalysisBundle:
    if bundle.status != AnalysisBundleStatus.SUBMITTED:
        raise ValueError(f"Cannot approve bundle in state: {bundle.status.value}")
    bundle.status = AnalysisBundleStatus.APPROVED_FOR_EXECUTION
    if ensure_build_request(db, bundle) is None:
        logger.info("Bundle %s approved without build request", bundle.id)
    return bundle


def reject_bundle(
    db: Session,
    bundle: AnalysisBundle,
    *,
    reason: str,
    rejected_by_id: uuid.UUID | None = None,
) -> AnalysisBundle:
    if bundle.status != AnalysisBundleStatus.SUBMITTED:
        raise ValueError(f"Cannot reject bundle in state: {bundle.status.value}")
    if not reason or not reason.strip():
        raise ValueError("Rejection reason is required")
    bundle.status = AnalysisBundleStatus.REJECTED
    bundle.rejection_reason = reason.strip()
    bundle.rejected_by_id = rejected_by_id
    bundle.rejected_at = datetime.now(timezone.utc)
    return bundle


def supersede_bundle(db: Session, bundle: AnalysisBundle) -> AnalysisBundle:
    if bundle.status != AnalysisBundleStatus.APPROVED_FOR_EXECUTION:
        raise ValueError(f"Cannot supersede bundle in state: {bundle.status.value}")
    bundle.status = AnalysisBundleStatus.SUPERSEDED
    return bundle
