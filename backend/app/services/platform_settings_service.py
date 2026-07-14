import logging

from sqlalchemy.orm import Session

from app.models.platform_setting import PlatformSetting, SettingKey

logger = logging.getLogger("epibridge.platform_settings")


def get_setting(db: Session, key: SettingKey) -> str | None:
    row = db.query(PlatformSetting).filter(PlatformSetting.key == key.value).first()
    return row.value if row is not None else None


def get_setting_bool(db: Session, key: SettingKey) -> bool:
    value = get_setting(db, key)
    return value == "true"


def set_setting(db: Session, key: SettingKey, value: str) -> PlatformSetting:
    row = db.query(PlatformSetting).filter(PlatformSetting.key == key.value).first()
    if row is None:
        row = PlatformSetting(key=key.value, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()
    db.refresh(row)
    logger.info("Setting %s = %s", key.value, value)
    return row


def get_all_settings(db: Session) -> dict[str, str]:
    rows = db.query(PlatformSetting).all()
    return {row.key: row.value for row in rows}
