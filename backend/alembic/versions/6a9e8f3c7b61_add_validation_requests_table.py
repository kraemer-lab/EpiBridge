"""Add validation_requests table

Revision ID: 6a9e8f3c7b61
Revises: 5a9e8f3c7b60
Create Date: 2026-07-11 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "6a9e8f3c7b61"
down_revision: Union[str, None] = "5a9e8f3c7b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "validation_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "analysis_bundle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_bundles.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3600"),
        ),
        sa.Column(
            "parameter_overrides",
            postgresql.JSON,
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "status",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("log", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "output_files",
            postgresql.JSON,
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "bundle_content_hash",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "requested_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_validation_requests_project_id",
        "validation_requests",
        ["project_id"],
    )
    op.create_index(
        "ix_validation_requests_bundle_id",
        "validation_requests",
        ["analysis_bundle_id"],
    )
    op.create_index(
        "ix_validation_requests_status",
        "validation_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_validation_requests_status", table_name="validation_requests")
    op.drop_index("ix_validation_requests_bundle_id", table_name="validation_requests")
    op.drop_index("ix_validation_requests_project_id", table_name="validation_requests")
    op.drop_table("validation_requests")
