"""Make execution_environment_id nullable for draft bundles

Revision ID: 5a9e8f3c7b60
Revises: 4a9e8f3c7b5f
Create Date: 2026-07-11 11:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "5a9e8f3c7b60"
down_revision: Union[str, None] = "4a9e8f3c7b5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "analysis_bundles",
        "execution_environment_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "analysis_bundles",
        "execution_environment_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
