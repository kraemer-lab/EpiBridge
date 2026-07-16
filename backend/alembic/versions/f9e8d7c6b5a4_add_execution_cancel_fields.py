"""Add execution cancel fields

Adds cancelled_by_id, cancelled_at, and cancellation_reason columns
to execution_requests for explicit cancellation lifecycle provenance.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "f9e8d7c6b5a4"
down_revision: Union[str, None] = "3a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "execution_requests",
        sa.Column(
            "cancelled_by_id",
            sa.UUID(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "execution_requests",
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "execution_requests",
        sa.Column(
            "cancellation_reason",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("execution_requests", "cancellation_reason")
    op.drop_column("execution_requests", "cancelled_at")
    op.drop_column("execution_requests", "cancelled_by_id")
