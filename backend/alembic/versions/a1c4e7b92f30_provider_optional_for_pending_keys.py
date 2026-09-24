"""a key can be pending before its provider is decided

Revision ID: a1c4e7b92f30
Revises: f1b58d27c093
Create Date: 2026-09-11

The team's own sheet already records rows where the provider column reads
"Pending" - the work is planned, the key is not yet taken out, and which
vendor it will come from has not been settled. Forcing a provider on those
rows would mean either inventing one or leaving the row out of the register
entirely, and the row is exactly the kind the register exists to remember.

So the provider becomes optional, and the status field carries the meaning:
"pending" is allowed to have no provider, "active" and "revoked" are not.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1c4e7b92f30"
down_revision = "f1b58d27c093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("api_key_entries", "provider_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # Rows with no provider cannot survive the column becoming required again,
    # and silently deleting a team's records is not a downgrade - so mark them
    # for a human rather than guessing.
    op.execute(
        "UPDATE api_key_entries SET status = 'revoked' "
        "WHERE provider_id IS NULL AND status <> 'revoked'"
    )
    op.execute("DELETE FROM api_key_entries WHERE provider_id IS NULL")
    op.alter_column("api_key_entries", "provider_id", existing_type=sa.Integer(), nullable=False)
