"""Add definition_path to execution_environments

Revision ID: 2a9e8f3c7b5d
Revises: 1d73975c664f
Create Date: 2026-07-09 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "2a9e8f3c7b5d"
down_revision: Union[str, None] = "1d73975c664f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "execution_environments",
        sa.Column(
            "definition_path",
            sa.String(length=255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("execution_environments", "definition_path")
