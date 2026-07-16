"""add_ai_output_set_reviews

Adds the ai_output_set_reviews table for AI-assisted
information governance review of execution output sets.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "3a1b2c3d4e5f"
down_revision: Union[str, None] = "9a8b7c6d5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_output_set_reviews",
        sa.Column("id", postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column("output_set_id", postgresql.UUID(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="pending"),
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
        "ix_ai_output_set_reviews_output_set_id",
        "ai_output_set_reviews",
        ["output_set_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_output_set_reviews_output_set_id")
    op.drop_table("ai_output_set_reviews")
