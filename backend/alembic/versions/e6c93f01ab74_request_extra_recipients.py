"""recipients the requestor chose when filing

Revision ID: e6c93f01ab74
Revises: d5a17b3e9c42
Create Date: 2026-09-09

A requestor knows better than the app who else in their vertical needs to see
a request go in, come back approved and land delivered. These two columns hold
that choice once, so it applies to all three emails rather than being retyped.

Both are plain JSON lists of addresses. Nullable, so every existing request
carries on with no extra recipients.
"""
from alembic import op
import sqlalchemy as sa

revision = "e6c93f01ab74"
down_revision = "d5a17b3e9c42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_requests", sa.Column("extra_to", sa.Text(), nullable=True))
    op.add_column("service_requests", sa.Column("extra_cc", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("service_requests", "extra_cc")
    op.drop_column("service_requests", "extra_to")
