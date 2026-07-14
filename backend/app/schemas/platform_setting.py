from pydantic import BaseModel


class PlatformSettingRead(BaseModel):
    key: str
    value: str


class PlatformSettingUpdate(BaseModel):
    value: str
