import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field


def _display_name(runtime: str) -> str:
    lang, *rest = runtime.split("-")
    version_parts = []
    for part in rest:
        if part and part[0].isdigit():
            version_parts.append(part)
        else:
            break
    lang_map = {"python": "Python", "r": "R", "conda": "Conda"}
    label = lang_map.get(lang, lang.capitalize())
    version = ".".join(version_parts) if version_parts else ""
    return f"{label} {version}".strip()


class ExecutionEnvironmentRead(BaseModel):
    id: uuid.UUID
    identifier: str
    name: str
    runtime: str
    description: str
    status: str
    image_reference: str
    definition_path: str | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def display_name(self) -> str:
        return _display_name(self.runtime)

    model_config = {"from_attributes": True}
