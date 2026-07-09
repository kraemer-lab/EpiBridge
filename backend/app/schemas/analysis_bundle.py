import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field

from app.models.analysis_bundle import AnalysisBundleBuildStatus, AnalysisBundleStatus
from app.schemas.ai_bundle_review import AIBundleReviewRead
from app.schemas.execution_environment import _display_name


class Interpreter(str, enum.Enum):
    PYTHON = "python"
    SHELL = "shell"
    R = "r"

    @property
    def executable(self) -> str:
        return {"python": "python", "shell": "bash", "r": "Rscript"}[self.value]

    @property
    def label(self) -> str:
        return {"python": "Python", "shell": "Shell", "r": "R"}[self.value]


class AnalysisBundleCreate(BaseModel):
    # NOTE: lifecycle state is owned by the server, not supplied by clients.
    name: str
    execution_environment_id: uuid.UUID
    version: str
    entrypoint: str
    interpreter: Interpreter = Interpreter.PYTHON
    arguments: str = ""
    source_path: str = ""
    description: str = ""
    resource_identifiers: list[str] = []
    outputs: list[str] = []
    parameters: dict = {}
    build_strategy: str = "institutional"


class AnalysisBundleRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by_id: uuid.UUID
    execution_environment_id: uuid.UUID
    name: str
    source_path: str
    status: AnalysisBundleStatus
    runtime: str
    version: str
    entrypoint: str
    interpreter: str = "python"
    arguments: str = ""
    description: str
    build_strategy: str = "institutional"
    build_status: AnalysisBundleBuildStatus = (
        AnalysisBundleBuildStatus.ENVIRONMENT_NOT_BUILT
    )
    build_error: str = ""
    build_log: str = ""
    resource_identifiers: list[str] = []
    outputs: list[str] = []
    parameters: dict = {}
    created_at: datetime
    updated_at: datetime
    ai_review: AIBundleReviewRead | None = None

    @computed_field
    @property
    def display_runtime(self) -> str:
        return _display_name(self.runtime)

    model_config = {"from_attributes": True}


class AnalysisBundleUpdate(BaseModel):
    name: str | None = None
    execution_environment_id: uuid.UUID | None = None
    version: str | None = None
    entrypoint: str | None = None
    interpreter: Interpreter | None = None
    arguments: str | None = None
    source_path: str | None = None
    description: str | None = None
    resource_identifiers: list[str] | None = None
    outputs: list[str] | None = None
    parameters: dict | None = None
    build_strategy: str | None = None
