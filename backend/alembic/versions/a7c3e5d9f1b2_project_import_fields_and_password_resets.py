"""project import fields, unique project names, password reset tokens

Revision ID: a7c3e5d9f1b2
Revises: 0df6727ad9cf
Create Date: 2026-09-02 12:00:00

Adds the three columns the team's Weekly_Update.xlsx tracks that the model
did not (assigned_by, assigned_on, remarks), enforces case-insensitive
uniqueness of project names (deduplicating any existing clashes first), and
creates the table behind the forgot-password flow.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c3e5d9f1b2"
down_revision: Union[str, None] = "0df6727ad9cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dedupe_project_names(conn) -> None:
    rows = conn.execute(sa.text("SELECT id, name FROM projects ORDER BY id")).fetchall()
    seen: dict[str, int] = {}
    for pid, name in rows:
        key = (name or "").strip().lower()
        if key in seen:
            seen[key] += 1
            conn.execute(
                sa.text("UPDATE projects SET name = :n WHERE id = :id"),
                {"n": f"{name} ({seen[key]})", "id": pid},
            )
        else:
            seen[key] = 1


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("assigned_by", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("assigned_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("remarks", sa.Text(), nullable=True))

    _dedupe_project_names(op.get_bind())
    op.create_index("ux_projects_name_lower", "projects", [sa.text("lower(name)")], unique=True)

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ux_projects_name_lower", table_name="projects")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("remarks")
        batch.drop_column("assigned_on")
        batch.drop_column("assigned_by")
