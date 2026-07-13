"""Add validation_setup_command to execution_environments

Revision ID: 8a9e8f3c7b63
Revises: 7a9e8f3c7b62
Create Date: 2026-07-13 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "8a9e8f3c7b63"
down_revision: Union[str, None] = "7a9e8f3c7b62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "execution_environments",
        sa.Column("validation_setup_command", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("execution_environments", "validation_setup_command")
