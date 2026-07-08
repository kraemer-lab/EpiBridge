import uuid

from sqlalchemy.orm import Session

from app.ai import get_ai_provider
from app.ai.context import AIReviewContext
from app.db.session import SessionLocal
from app.models.ai_bundle_review import AIBundleReview, AIBundleReviewStatus
from app.models.analysis_bundle import AnalysisBundle
from app.services.bundle_store import get_bundle_store


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
    except Exception:
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
            return

        provider = get_ai_provider()
        if provider is None:
            review.status = AIBundleReviewStatus.UNAVAILABLE
            db.commit()
            return

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
        else:
            review.summary = result.summary
            review.assessment = result.assessment
            review.assessment_confidence = result.assessment_confidence
            review.reviewer_notes = result.reviewer_notes
            review.status = AIBundleReviewStatus.COMPLETED

        db.commit()
    except Exception:
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
            db.rollback()
    finally:
        db.close()


def request_and_perform_review(bundle_id: uuid.UUID) -> None:
    """Fire-and-forget: create or reset the review record, then run the
    review.  Errors never propagate — the platform continues normally
    whether the AI review succeeds, fails, or is unavailable."""
    try:
        request_review(bundle_id)
        perform_review(bundle_id)
    except Exception:
        pass


def get_review(db: Session, bundle_id: uuid.UUID) -> AIBundleReview | None:
    return (
        db.query(AIBundleReview).filter(AIBundleReview.bundle_id == bundle_id).first()
    )
