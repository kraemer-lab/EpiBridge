from fastapi import APIRouter

from app.db.session import SessionLocal
from app.models.platform_setting import SettingKey
from app.services.ai_status_service import check_ai_status
from app.services.platform_settings_service import get_setting_bool

router = APIRouter()


@router.get("/ai/status")
def ai_status():
    status = check_ai_status()
    db = SessionLocal()
    try:
        review_enabled = get_setting_bool(db, SettingKey.AI_REVIEW_ENABLED)
    finally:
        db.close()
    return {
        "ready": status.ready,
        "reason": status.reason,
        "review_enabled": review_enabled,
    }
