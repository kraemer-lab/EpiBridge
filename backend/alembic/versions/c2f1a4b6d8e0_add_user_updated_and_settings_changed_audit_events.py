"""add user.updated and settings.changed audit events

Extends the audit_event_type PostgreSQL ENUM with two new values
that were added to the Python AuditEventType enum but never
migrated to the database.

The affected backend code:
- app/models/audit_event.py (AuditEventType enum)
- app/api/routes/admin.py (create_audit_event calls)

Revision ID: c2f1a4b6d8e0
Revises: d8e7f6c5b4a3
Create Date: 2026-07-17
"""

from alembic import op

revision = "c2f1a4b6d8e0"
down_revision = "d8e7f6c5b4a3"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'user.updated'")
    op.execute("ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'settings.changed'")


def downgrade():
    pass
