import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.ai_output_set_review import AIOutputSetReviewStatus


class AIOutputSetReviewRead(BaseModel):
    id: uuid.UUID
    output_set_id: uuid.UUID
    status: AIOutputSetReviewStatus
    summary: str | None = None
    assessment: str | None = None
    assessment_confidence: str | None = None
    reviewer_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
