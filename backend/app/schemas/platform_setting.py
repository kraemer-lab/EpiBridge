from pydantic import BaseModel

from app.models.platform_setting import SettingKey


class PlatformSettingRead(BaseModel):
    key: SettingKey
    value: str


class PlatformSettingUpdate(BaseModel):
    value: str
