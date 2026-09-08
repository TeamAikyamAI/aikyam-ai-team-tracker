"""half-finished guided assistant flows

Revision ID: c4f2a91d6e08
Revises: b8e1d7c4a920
Create Date: 2026-09-07

One table, no changes to anything existing. Rows are short-lived: the
assistant deletes each one as soon as its flow is saved or cancelled.
"""
from alembic import op
import sqlalchemy as sa

revision = "c4f2a91d6e08"
down_revision = "b8e1d7c4a920"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False, server_default="new_project"),
        sa.Column("step", sa.String(length=40), nullable=False),
        sa.Column("data", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_chat_draft_session"),
    )
    op.create_index("ix_chat_drafts_session_id", "chat_drafts", ["session_id"])
    op.create_index("ix_chat_drafts_user_id", "chat_drafts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_drafts_user_id", table_name="chat_drafts")
    op.drop_index("ix_chat_drafts_session_id", table_name="chat_drafts")
    op.drop_table("chat_drafts")
