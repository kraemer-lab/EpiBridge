"""Add build_strategy to analysis_bundles

Revision ID: 3a9e8f3c7b5e
Revises: 2a9e8f3c7b5d
Create Date: 2026-07-09 17:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "3a9e8f3c7b5e"
down_revision: Union[str, None] = "2a9e8f3c7b5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_bundles",
        sa.Column(
            "build_strategy",
            sa.String(length=20),
            nullable=False,
            server_default="institutional",
        ),
    )


def downgrade() -> None:
    op.drop_column("analysis_bundles", "build_strategy")
