import logging
import uuid

from sqlalchemy.orm import Session

from app.ai import get_ai_provider
from app.ai.context import AIReviewContext
from app.db.session import SessionLocal
from app.models.ai_bundle_review import AIBundleReview, AIBundleReviewStatus
from app.models.analysis_bundle import AnalysisBundle
from app.models.platform_setting import SettingKey
from app.services.bundle_store import get_bundle_store
from app.services.platform_settings_service import get_setting_bool

logger = logging.getLogger("epibridge.ai.review")


def request_review(bundle_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        review = (
            db.query(AIBundleReview)
            .filter(AIBundleReview.bundle_id == bundle_id)
            .first()
        )
        if review is None:
            bundle = (
                db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
            )
            if bundle is None:
                logger.warning("request_review: bundle %s not found", bundle_id)
                return
            review = AIBundleReview(
                bundle_id=bundle_id, status=AIBundleReviewStatus.PENDING
            )
            db.add(review)
        else:
            review.status = AIBundleReviewStatus.PENDING
            review.summary = None
            review.assessment = None
            review.assessment_confidence = None
            review.reviewer_notes = None
        db.commit()
        logger.info("request_review: bundle %s set to PENDING", bundle_id)
    except Exception:
        logger.exception("request_review: error for bundle %s", bundle_id)
        db.rollback()
    finally:
        db.close()


def perform_review(bundle_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        review = (
            db.query(AIBundleReview)
            .filter(AIBundleReview.bundle_id == bundle_id)
            .first()
        )
        if review is None:
            logger.warning("perform_review: no review record for bundle %s", bundle_id)
            return

        ai_enabled = get_setting_bool(db, SettingKey.AI_REVIEW_ENABLED)
        if not ai_enabled:
            logger.info(
                "perform_review: AI review disabled by policy for bundle %s", bundle_id
            )
            review.status = AIBundleReviewStatus.UNAVAILABLE
            db.commit()
            return

        provider = get_ai_provider()

        bundle = db.query(AnalysisBundle).filter(AnalysisBundle.id == bundle_id).first()
        context = AIReviewContext(
            runtime=(
                bundle.execution_environment.runtime
                if bundle and bundle.execution_environment
                else ""
            ),
            entrypoint=bundle.entrypoint if bundle else "",
            resource_identifiers=(
                sorted(dr.identifier for dr in bundle.data_resources) if bundle else []
            ),
        )

        analysis_dir = get_bundle_store().get_path(bundle_id)
        result = provider.review(analysis_dir, context=context)

        if result.is_unavailable:
            review.status = AIBundleReviewStatus.UNAVAILABLE
            logger.warning(
                "perform_review: provider unavailable for bundle %s: %s",
                bundle_id,
                result.errors,
            )
        else:
            review.summary = result.summary
            review.assessment = result.assessment
            review.assessment_confidence = result.assessment_confidence
            review.reviewer_notes = result.reviewer_notes
            review.status = AIBundleReviewStatus.COMPLETED
            logger.info("perform_review: bundle %s completed", bundle_id)

        db.commit()
    except Exception:
        logger.exception("perform_review: error for bundle %s", bundle_id)
        try:
            review = (
                db.query(AIBundleReview)
                .filter(AIBundleReview.bundle_id == bundle_id)
                .first()
            )
            if review is not None:
                review.status = AIBundleReviewStatus.FAILED
                db.commit()
        except Exception:
            logger.exception(
                "perform_review: failed to set FAILED status for bundle %s", bundle_id
            )
            db.rollback()
    finally:
        db.close()


def request_and_perform_review(bundle_id: uuid.UUID) -> None:
    try:
        request_review(bundle_id)
        perform_review(bundle_id)
    except Exception:
        logger.exception(
            "request_and_perform_review: unhandled error for bundle %s", bundle_id
        )


def get_review(db: Session, bundle_id: uuid.UUID) -> AIBundleReview | None:
    return (
        db.query(AIBundleReview).filter(AIBundleReview.bundle_id == bundle_id).first()
    )
