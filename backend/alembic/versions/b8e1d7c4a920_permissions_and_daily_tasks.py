"""role permissions grid and daily to-do tasks

Revision ID: b8e1d7c4a920
Revises: a7c3e5d9f1b2
Create Date: 2026-09-04

Adds two independent tables. Neither touches existing data, so this migration
is safe to run on a live database and reversible without loss of anything the
app had before it.
"""
from alembic import op
import sqlalchemy as sa

revision = "b8e1d7c4a920"
down_revision = "a7c3e5d9f1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("feature", sa.String(length=50), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role", "feature", name="uq_role_permission"),
    )
    op.create_index("ix_role_permissions_role", "role_permissions", ["role"])
    op.create_index("ix_role_permissions_feature", "role_permissions", ["feature"])

    op.create_table(
        "daily_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("task_date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_on", sa.Date(), nullable=True),
        sa.Column("parked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_tasks_user_id", "daily_tasks", ["user_id"])
    op.create_index("ix_daily_tasks_task_date", "daily_tasks", ["task_date"])
    op.create_index("ix_daily_tasks_user_task_date", "daily_tasks", ["user_id", "task_date"])
    op.create_index("ix_daily_tasks_user_completed_on", "daily_tasks", ["user_id", "completed_on"])


def downgrade() -> None:
    op.drop_index("ix_daily_tasks_user_completed_on", table_name="daily_tasks")
    op.drop_index("ix_daily_tasks_user_task_date", table_name="daily_tasks")
    op.drop_index("ix_daily_tasks_task_date", table_name="daily_tasks")
    op.drop_index("ix_daily_tasks_user_id", table_name="daily_tasks")
    op.drop_table("daily_tasks")

    op.drop_index("ix_role_permissions_feature", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role", table_name="role_permissions")
    op.drop_table("role_permissions")
