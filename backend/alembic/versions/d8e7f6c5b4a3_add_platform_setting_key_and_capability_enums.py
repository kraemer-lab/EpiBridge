"""Add platform_setting_key and capability enums

Migrates PlatformSetting.key, CapabilityRecord.name,
RoleCapability.capability_name, and UserCapability.capability_name
from String columns to proper PostgreSQL ENUM types.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d8e7f6c5b4a3"
down_revision: Union[str, None] = "initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CAPABILITY_VALUES = (
    "project.manage",
    "project.members.manage",
    "project.resources.manage",
    "bundle.create",
    "bundle.submit",
    "bundle.review",
    "execution.run",
    "output.review",
    "output.release",
    "environment.manage",
    "data.manage",
    "user.manage",
    "user.read",
    "validation.run",
    "build.customize",
    "governance.self_regulate",
    "terms.manage",
    "settings.manage",
    "execution.cancel",
    "execution.read",
    "audit.read",
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE platform_setting_key AS ENUM ("
        "'ai_review_enabled', "
        "'prevent_self_moderation', "
        "'auto_execute_approved_bundles', "
        "'max_task_duration_seconds'"
        ")"
    )
    op.execute(
        "CREATE TYPE capability AS ENUM ("
        + ", ".join(f"'{v}'" for v in CAPABILITY_VALUES)
        + ")"
    )

    op.execute(
        "ALTER TABLE user_capabilities DROP CONSTRAINT user_capabilities_capability_name_fkey"
    )
    op.execute(
        "ALTER TABLE role_capabilities DROP CONSTRAINT role_capabilities_capability_name_fkey"
    )

    op.alter_column(
        "capabilities",
        "name",
        type_=sa.Enum(*CAPABILITY_VALUES, name="capability"),
        postgresql_using="name::text::capability",
    )
    op.alter_column(
        "role_capabilities",
        "capability_name",
        type_=sa.Enum(*CAPABILITY_VALUES, name="capability"),
        postgresql_using="capability_name::text::capability",
    )
    op.alter_column(
        "user_capabilities",
        "capability_name",
        type_=sa.Enum(*CAPABILITY_VALUES, name="capability"),
        postgresql_using="capability_name::text::capability",
    )
    op.alter_column(
        "platform_settings",
        "key",
        type_=sa.Enum(
            "ai_review_enabled",
            "prevent_self_moderation",
            "auto_execute_approved_bundles",
            "max_task_duration_seconds",
            name="platform_setting_key",
        ),
        postgresql_using="key::text::platform_setting_key",
    )

    op.create_foreign_key(
        "role_capabilities_capability_name_fkey",
        "role_capabilities",
        "capabilities",
        ["capability_name"],
        ["name"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "user_capabilities_capability_name_fkey",
        "user_capabilities",
        "capabilities",
        ["capability_name"],
        ["name"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE user_capabilities DROP CONSTRAINT user_capabilities_capability_name_fkey"
    )
    op.execute(
        "ALTER TABLE role_capabilities DROP CONSTRAINT role_capabilities_capability_name_fkey"
    )

    op.alter_column("user_capabilities", "capability_name", type_=sa.String(100))
    op.alter_column("role_capabilities", "capability_name", type_=sa.String(100))
    op.alter_column("capabilities", "name", type_=sa.String(100))
    op.alter_column("platform_settings", "key", type_=sa.String(100))

    op.create_foreign_key(
        "role_capabilities_capability_name_fkey",
        "role_capabilities",
        "capabilities",
        ["capability_name"],
        ["name"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "user_capabilities_capability_name_fkey",
        "user_capabilities",
        "capabilities",
        ["capability_name"],
        ["name"],
        ondelete="CASCADE",
    )

    op.execute("DROP TYPE IF EXISTS capability")
    op.execute("DROP TYPE IF EXISTS platform_setting_key")
