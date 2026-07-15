"""add_submission_provenance

Adds submitted_by_id and submitted_at columns to analysis_bundles
for explicit submission lifecycle provenance.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "94e35933519f"
down_revision: Union[str, None] = "2ce8df4f3ba2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_bundles",
        sa.Column(
            "submitted_by_id",
            sa.UUID(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "analysis_bundles",
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("analysis_bundles", "submitted_at")
    op.drop_column("analysis_bundles", "submitted_by_id")
