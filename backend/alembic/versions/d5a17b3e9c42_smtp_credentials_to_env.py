"""clear the corrupted SMTP password

Revision ID: d5a17b3e9c42
Revises: c4f2a91d6e08
Create Date: 2026-09-08

The Settings form once carried its own mask back on an unrelated save, so the
literal string "******" was stored as the SMTP password. Every outgoing email
then failed with "credentials were incorrect" and nothing said why.

The code now ignores a value made only of mask characters, so it cannot happen
again. This removes the value that is already wrong, which is not a real
password and can only keep mail broken. The next save from
Admin > Settings > Email puts a working one back.

Only the password row goes. The username and From name are real values worth
keeping.
"""
from alembic import op
import sqlalchemy as sa

revision = "d5a17b3e9c42"
down_revision = "c4f2a91d6e08"
branch_labels = None
depends_on = None

# Mask characters: asterisk, bullet, black circle, middle dot.
_MASK = "*•●· "


def upgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        sa.text("SELECT value FROM app_settings WHERE key = 'smtp_password'")
    ).fetchone()
    if row and row[0] and set(row[0].strip()) <= set(_MASK):
        conn.execute(sa.text("DELETE FROM app_settings WHERE key = 'smtp_password'"))


def downgrade() -> None:
    # Nothing to restore - the deleted value was a mask, not a credential.
    pass
