import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.ai_bundle_review import AIBundleReviewStatus


class AIBundleReviewRead(BaseModel):
    id: uuid.UUID
    bundle_id: uuid.UUID
    status: AIBundleReviewStatus
    summary: str | None = None
    assessment: str | None = None
    assessment_confidence: str | None = None
    reviewer_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
