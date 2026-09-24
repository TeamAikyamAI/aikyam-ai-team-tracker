"""the API key register

Revision ID: f1b58d27c093
Revises: e6c93f01ab74
Create Date: 2026-09-10

A register of which provider's key each project uses, what for, whose account
it sits on and when it lapses - the team's Api_Key.xlsx, moved into the tool so
it can warn before a key expires instead of being noticed after production
breaks.

Deliberately no column for the secret itself. This records that a key exists,
not what it is.

Seeds the four providers already in use so the first screen is not empty; they
are editable in the Admin panel like verticals and statuses.
"""
from alembic import op
import sqlalchemy as sa

revision = "f1b58d27c093"
down_revision = "e6c93f01ab74"
branch_labels = None
depends_on = None

_SEED = ["Gemini", "Groq", "Azure", "Deep-infra"]


def upgrade() -> None:
    providers = op.create_table(
        "api_providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.bulk_insert(
        providers,
        [{"name": name, "is_active": True, "sort_order": i} for i, name in enumerate(_SEED, start=1)],
    )

    op.create_table(
        "api_key_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("project_label", sa.String(length=200), nullable=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("api_providers.id"), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("account_email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_key_entries_expires_on", "api_key_entries", ["expires_on"])


def downgrade() -> None:
    op.drop_index("ix_api_key_entries_expires_on", table_name="api_key_entries")
    op.drop_table("api_key_entries")
    op.drop_table("api_providers")
