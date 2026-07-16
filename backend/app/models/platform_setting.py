import enum

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SettingKey(str, enum.Enum):
    AI_REVIEW_ENABLED = "ai_review_enabled"
    PREVENT_SELF_MODERATION = "prevent_self_moderation"
    AUTO_EXECUTE_APPROVED_BUNDLES = "auto_execute_approved_bundles"
    MAX_TASK_DURATION_SECONDS = "max_task_duration_seconds"

    @classmethod
    def all_values(cls) -> set[str]:
        return {c.value for c in cls}


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
