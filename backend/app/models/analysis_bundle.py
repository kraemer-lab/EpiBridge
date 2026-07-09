import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ai_bundle_review import AIBundleReview
    from app.models.data_resource import DataResource
    from app.models.execution_environment import ExecutionEnvironment
    from app.models.execution_image import ExecutionImage
    from app.models.project import Project
    from app.models.user import User


class AnalysisBundleStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED_FOR_EXECUTION = "approved_for_execution"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class AnalysisBundleBuildStatus(str, enum.Enum):
    ENVIRONMENT_NOT_BUILT = "environment_not_built"
    ENVIRONMENT_BUILDING = "environment_building"
    ENVIRONMENT_READY = "environment_ready"
    ENVIRONMENT_BUILD_FAILED = "environment_build_failed"


class BuildStrategy(str, enum.Enum):
    INSTITUTIONAL = "institutional"
    CUSTOM = "custom"


class AnalysisBundle(Base):
    __tablename__ = "analysis_bundles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    execution_environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_environments.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[AnalysisBundleStatus] = mapped_column(
        String(64), nullable=False, default=AnalysisBundleStatus.DRAFT
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    entrypoint: Mapped[str] = mapped_column(String(255), nullable=False)
    interpreter: Mapped[str] = mapped_column(
        String(20), nullable=False, default="python"
    )
    arguments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outputs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    build_strategy: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BuildStrategy.INSTITUTIONAL
    )
    # NOTE:
    # This field mirrors the BuildRequest lifecycle for historical reasons.
    # Environment preparation is owned by BuildRequest, not AnalysisBundle.
    # This field is retained for backwards compatibility and is expected
    # to be removed in a future governance refactor.
    build_status: Mapped[AnalysisBundleBuildStatus] = mapped_column(
        String(64),
        nullable=False,
        default=AnalysisBundleBuildStatus.ENVIRONMENT_NOT_BUILT,
    )
    build_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    execution_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("execution_images.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(backref="analysis_bundles")
    created_by: Mapped["User"] = relationship(backref="created_bundles")
    execution_environment: Mapped["ExecutionEnvironment"] = relationship()
    execution_image: Mapped["ExecutionImage | None"] = relationship()

    data_resources: Mapped[list["DataResource"]] = relationship(
        secondary="analysis_bundle_data_resources",
    )

    ai_review: Mapped["AIBundleReview | None"] = relationship(
        back_populates="bundle", uselist=False
    )


class AnalysisBundleDataResource(Base):
    __tablename__ = "analysis_bundle_data_resources"

    analysis_bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_bundles.id"), primary_key=True
    )
    data_resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_resources.id"), primary_key=True
    )
