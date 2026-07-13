"""Add user_roles table for multi-role support

Revision ID: 7a9e8f3c7b62
Revises: 6a9e8f3c7b61
Create Date: 2026-07-13 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "7a9e8f3c7b62"
down_revision: Union[str, None] = "6a9e8f3c7b61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_roles join table
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )

    # Populate user_roles from existing users.role ENUM values
    # Maps each user's single role to the corresponding role record
    op.execute(
        text(
            "INSERT INTO user_roles (user_id, role_id) "
            "SELECT u.id, r.id "
            "FROM users u "
            "JOIN roles r ON r.name = u.role::text "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM user_roles ur "
            "  WHERE ur.user_id = u.id AND ur.role_id = r.id"
            ")"
        )
    )


def downgrade() -> None:
    op.drop_table("user_roles")
