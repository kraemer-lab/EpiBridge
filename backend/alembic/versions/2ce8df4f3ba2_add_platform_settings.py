"""add_platform_settings

Adds the platform_settings table for institution-wide configuration.
First consumer: AI_REVIEW_ENABLED toggle.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "2ce8df4f3ba2"
down_revision: Union[str, None] = "initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(100), nullable=False, primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("platform_settings")
