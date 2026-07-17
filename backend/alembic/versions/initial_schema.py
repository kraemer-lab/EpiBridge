"""initial_schema

Single baseline migration replacing the accumulated development chain.
Includes ORM contract fix: all lifecycle enums use proper PostgreSQL ENUM
types (with lowercase values matching Python enum values) instead of String
columns.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capabilities",
        sa.Column("name", sa.String(100), nullable=False, primary_key=True),
    )
    op.create_table(
        "data_resources",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column("identifier", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("endpoint", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("identifier"),
        sa.UniqueConstraint("alias"),
    )
    op.create_table(
        "execution_environments",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column("identifier", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("runtime", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("image_reference", sa.String(255), nullable=False),
        sa.Column("definition_path", sa.String(255)),
        sa.Column("validation_setup_command", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("identifier"),
    )
    op.create_table(
        "execution_images",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column("execution_environment_id", postgresql.UUID(), nullable=False),
        sa.Column("dependency_hash", sa.String(64), nullable=False),
        sa.Column("image_reference", sa.String(255), nullable=False),
        sa.Column("builder_type", sa.String(50), nullable=False),
        sa.Column("build_log", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "execution_environment_id",
            "dependency_hash",
            name="uq_execution_image_env_hash",
        ),
    )
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(100), nullable=False, primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("RESEARCHER", "MODERATOR", "MAINTAINER", "ADMIN", name="user_role"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "owner_id", postgresql.UUID(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "role_capabilities",
        sa.Column(
            "role_id",
            postgresql.UUID(),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "capability_name",
            sa.String(100),
            sa.ForeignKey("capabilities.name", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(128), nullable=False, primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "terms_of_service",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column("terms_type", sa.String(50), nullable=False),
        sa.Column(
            "data_resource_id", postgresql.UUID(), sa.ForeignKey("data_resources.id")
        ),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "published_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "terms_type", "data_resource_id", "version", name="uq_terms_version"
        ),
    )
    op.create_table(
        "user_capabilities",
        sa.Column(
            "user_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "capability_name",
            sa.String(100),
            sa.ForeignKey("capabilities.name", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
    )
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
    )
    op.create_table(
        "analysis_bundles",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "execution_environment_id",
            postgresql.UUID(),
            sa.ForeignKey("execution_environments.id"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "submitted",
                "approved_for_execution",
                "rejected",
                "superseded",
                name="analysis_bundle_status",
            ),
            nullable=False,
        ),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("entrypoint", sa.String(255), nullable=False),
        sa.Column("interpreter", sa.String(20), nullable=False),
        sa.Column("arguments", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("outputs", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column(
            "build_strategy",
            sa.Enum("institutional", "custom", name="build_strategy"),
            nullable=False,
            server_default=sa.text("'institutional'"),
        ),
        sa.Column(
            "build_status",
            sa.Enum(
                "environment_not_built",
                "environment_building",
                "environment_ready",
                "environment_build_failed",
                name="analysis_bundle_build_status",
            ),
            nullable=False,
        ),
        sa.Column("build_error", sa.Text(), nullable=False),
        sa.Column(
            "execution_image_id",
            postgresql.UUID(),
            sa.ForeignKey("execution_images.id"),
        ),
        sa.Column(
            "submitted_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "rejected_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "event_type",
            sa.Enum(
                "project.created",
                "project.member.added",
                "project.member.removed",
                "project.resource.allocated",
                "project.resource.deallocated",
                "bundle.created",
                "bundle.submitted",
                "bundle.approved",
                "bundle.rejected",
                "bundle.superseded",
                "execution.requested",
                "execution.started",
                "execution.completed",
                "execution.failed",
                "execution.cancelled",
                "output_set.created",
                "output_set.approved",
                "output_set.rejected",
                "output_set.released",
                "user.created",
                "platform_terms.published",
                "dataset_terms.published",
                "platform_terms.accepted",
                "dataset_terms.accepted",
                "validation.completed",
                "validation.failed",
                name="audit_event_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "actor_id", postgresql.UUID(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("project_id", postgresql.UUID(), sa.ForeignKey("projects.id")),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(), nullable=False),
        sa.Column("event_metadata", postgresql.JSONB(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "project_memberships",
        sa.Column(
            "project_id",
            postgresql.UUID(),
            sa.ForeignKey("projects.id"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "project_resource_allocations",
        sa.Column(
            "project_id",
            postgresql.UUID(),
            sa.ForeignKey("projects.id"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "data_resource_id",
            postgresql.UUID(),
            sa.ForeignKey("data_resources.id"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("revoked_by_id", postgresql.UUID(), sa.ForeignKey("users.id")),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "terms_acceptance",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "terms_of_service_id",
            postgresql.UUID(),
            sa.ForeignKey("terms_of_service.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "user_id", "terms_of_service_id", name="uq_user_terms_acceptance"
        ),
    )
    op.create_table(
        "ai_bundle_reviews",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "bundle_id",
            postgresql.UUID(),
            sa.ForeignKey("analysis_bundles.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "completed",
                "failed",
                "unavailable",
                name="ai_bundle_review_status",
            ),
            nullable=False,
        ),
        sa.Column("summary", sa.Text()),
        sa.Column("assessment", sa.Text()),
        sa.Column("assessment_confidence", sa.String(10)),
        sa.Column("reviewer_notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("bundle_id"),
    )
    op.create_table(
        "analysis_bundle_data_resources",
        sa.Column(
            "analysis_bundle_id",
            postgresql.UUID(),
            sa.ForeignKey("analysis_bundles.id"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "data_resource_id",
            postgresql.UUID(),
            sa.ForeignKey("data_resources.id"),
            nullable=False,
            primary_key=True,
        ),
    )
    op.create_table(
        "build_requests",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "execution_environment_id",
            postgresql.UUID(),
            sa.ForeignKey("execution_environments.id"),
            nullable=False,
        ),
        sa.Column(
            "analysis_bundle_id",
            postgresql.UUID(),
            sa.ForeignKey("analysis_bundles.id"),
            nullable=False,
        ),
        sa.Column("dependency_hash", sa.String(64), nullable=False),
        sa.Column("builder_type", sa.String(50), nullable=False),
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3600"),
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "building",
                "completed",
                "failed",
                name="build_request_status",
            ),
            nullable=False,
        ),
        sa.Column(
            "execution_image_id",
            postgresql.UUID(),
            sa.ForeignKey("execution_images.id"),
        ),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("log", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "execution_requests",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "analysis_bundle_id",
            postgresql.UUID(),
            sa.ForeignKey("analysis_bundles.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3600"),
        ),
        sa.Column("parameter_overrides", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                "cancelling",
                "cancelled",
                name="execution_request_status",
            ),
            nullable=False,
        ),
        sa.Column("log", sa.Text(), nullable=False),
        sa.Column(
            "requested_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "cancelled_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "validation_requests",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "analysis_bundle_id",
            postgresql.UUID(),
            sa.ForeignKey("analysis_bundles.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3600"),
        ),
        sa.Column(
            "parameter_overrides",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="validation_request_status",
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("log", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "output_files",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "bundle_content_hash",
            sa.String(64),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "requested_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "output_sets",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "execution_request_id",
            postgresql.UUID(),
            sa.ForeignKey("execution_requests.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending_review",
                "approved",
                "rejected",
                "released",
                name="output_set_status",
            ),
            nullable=False,
        ),
        sa.Column("release_package_path", sa.String(512)),
        sa.Column("release_package_size", sa.Integer()),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "rejected_by_id",
            postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("execution_request_id"),
    )
    op.create_table(
        "outputs",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "output_set_id",
            postgresql.UUID(),
            sa.ForeignKey("output_sets.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "ai_output_set_reviews",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "output_set_id",
            postgresql.UUID(),
            sa.ForeignKey("output_sets.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "completed",
                "failed",
                "unavailable",
                name="ai_output_set_review_status",
            ),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("assessment", sa.Text(), nullable=True),
        sa.Column("assessment_confidence", sa.String(10), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["output_set_id"],
            ["output_sets.id"],
        ),
        sa.UniqueConstraint("output_set_id"),
    )
    op.create_index(
        "ix_terms_of_service_terms_type", "terms_of_service", ["terms_type"]
    )
    op.create_index(
        "ix_terms_of_service_data_resource_id", "terms_of_service", ["data_resource_id"]
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_project_id", "audit_events", ["project_id"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index(
        "ix_audit_events_resource", "audit_events", ["resource_type", "resource_id"]
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index(
        "ix_terms_acceptance_terms_of_service_id",
        "terms_acceptance",
        ["terms_of_service_id"],
    )
    op.create_index("ix_terms_acceptance_user_id", "terms_acceptance", ["user_id"])
    op.create_index(
        "ix_validation_requests_bundle_id",
        "validation_requests",
        ["analysis_bundle_id"],
    )
    op.create_index(
        "ix_validation_requests_project_id", "validation_requests", ["project_id"]
    )
    op.create_index("ix_validation_requests_status", "validation_requests", ["status"])
    op.create_index(
        "ix_ai_output_set_reviews_output_set_id",
        "ai_output_set_reviews",
        ["output_set_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_output_set_reviews_output_set_id",
        table_name="ai_output_set_reviews",
    )
    op.drop_index("ix_validation_requests_status", table_name="validation_requests")
    op.drop_index("ix_validation_requests_bundle_id", table_name="validation_requests")
    op.drop_index("ix_validation_requests_project_id", table_name="validation_requests")
    op.drop_table("ai_output_set_reviews")
    op.drop_table("outputs")
    op.drop_table("output_sets")
    op.drop_table("validation_requests")
    op.drop_table("execution_requests")
    op.drop_table("build_requests")
    op.drop_table("analysis_bundle_data_resources")
    op.drop_table("ai_bundle_reviews")
    op.drop_table("terms_acceptance")
    op.drop_table("project_resource_allocations")
    op.drop_table("project_memberships")
    op.drop_table("audit_events")
    op.drop_table("analysis_bundles")
    op.drop_table("user_roles")
    op.drop_table("user_capabilities")
    op.drop_table("terms_of_service")
    op.drop_table("sessions")
    op.drop_table("role_capabilities")
    op.drop_table("projects")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("platform_settings")
    op.drop_table("execution_images")
    op.drop_table("execution_environments")
    op.drop_table("data_resources")
    op.drop_table("capabilities")

    # Drop custom ENUM types (PostgreSQL-specific)
    op.execute("DROP TYPE IF EXISTS analysis_bundle_status")
    op.execute("DROP TYPE IF EXISTS analysis_bundle_build_status")
    op.execute("DROP TYPE IF EXISTS build_strategy")
    op.execute("DROP TYPE IF EXISTS execution_request_status")
    op.execute("DROP TYPE IF EXISTS output_set_status")
    op.execute("DROP TYPE IF EXISTS build_request_status")
    op.execute("DROP TYPE IF EXISTS validation_request_status")
    op.execute("DROP TYPE IF EXISTS ai_bundle_review_status")
    op.execute("DROP TYPE IF EXISTS ai_output_set_review_status")
    op.execute("DROP TYPE IF EXISTS audit_event_type")
    op.execute("DROP TYPE IF EXISTS user_role")
