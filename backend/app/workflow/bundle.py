import logging

from sqlalchemy.orm import Session

from app.models.analysis_bundle import AnalysisBundle, AnalysisBundleStatus
from app.services.environment_builder_service import ensure_build_request

logger = logging.getLogger("workflow.bundle")


def submit_bundle(db: Session, bundle: AnalysisBundle) -> AnalysisBundle:
    if bundle.status != AnalysisBundleStatus.DRAFT.value:
        raise ValueError(f"Cannot submit bundle in state: {bundle.status}")
    bundle.status = AnalysisBundleStatus.SUBMITTED.value
    return bundle


def approve_bundle(db: Session, bundle: AnalysisBundle) -> AnalysisBundle:
    if bundle.status != AnalysisBundleStatus.SUBMITTED.value:
        raise ValueError(f"Cannot approve bundle in state: {bundle.status}")
    bundle.status = AnalysisBundleStatus.APPROVED_FOR_EXECUTION.value
    if ensure_build_request(db, bundle) is None:
        logger.info("Bundle %s approved without build request", bundle.id)
    return bundle


def reject_bundle(db: Session, bundle: AnalysisBundle) -> AnalysisBundle:
    if bundle.status != AnalysisBundleStatus.SUBMITTED.value:
        raise ValueError(f"Cannot reject bundle in state: {bundle.status}")
    bundle.status = AnalysisBundleStatus.REJECTED.value
    return bundle


def supersede_bundle(db: Session, bundle: AnalysisBundle) -> AnalysisBundle:
    if bundle.status != AnalysisBundleStatus.APPROVED_FOR_EXECUTION.value:
        raise ValueError(f"Cannot supersede bundle in state: {bundle.status}")
    bundle.status = AnalysisBundleStatus.SUPERSEDED.value
    return bundle
