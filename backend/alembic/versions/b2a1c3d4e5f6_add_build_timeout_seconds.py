"""Add build timeout_seconds

Adds timeout_seconds column to build_requests for bounded
execution time on Docker build operations.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b2a1c3d4e5f6"
down_revision: Union[str, None] = "f9e8d7c6b5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "build_requests",
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3600"),
        ),
    )


def downgrade() -> None:
    op.drop_column("build_requests", "timeout_seconds")
