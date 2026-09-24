"""Expiry arithmetic for the API key register.

Kept in one place because three screens have to agree on it: the register's own
colour coding, the dashboard card, and the Monday digest. "Expired" is never a
stored status - it is always derived from the date, so a row cannot claim to be
active on a date that has already passed.
"""
from datetime import date

from sqlalchemy.orm import Session, selectinload

from app.models.api_key import ApiKeyEntry

# How far ahead a key counts as "expiring soon". Long enough that a renewal
# with a vendor or a purchase approval still has room to happen.
EXPIRY_WINDOW_DAYS = 30


def describe_expiry(expires_on: date | None, status: str, today: date) -> tuple[int | None, str]:
    """Days left and a state: none | ok | soon | expired.

    A revoked key is nobody's problem any more, so it never raises a warning
    however old its date is.
    """
    if status == "revoked":
        return (None if expires_on is None else (expires_on - today).days), "none"
    if expires_on is None:
        return None, "none"
    days = (expires_on - today).days
    if days < 0:
        return days, "expired"
    if days <= EXPIRY_WINDOW_DAYS:
        return days, "soon"
    return days, "ok"


def expiring_entries(db: Session, today: date) -> list[ApiKeyEntry]:
    """Every key already lapsed or lapsing inside the window, soonest first."""
    rows = (
        db.query(ApiKeyEntry)
        .options(selectinload(ApiKeyEntry.project), selectinload(ApiKeyEntry.provider))
        .filter(ApiKeyEntry.expires_on.isnot(None), ApiKeyEntry.status != "revoked")
        .order_by(ApiKeyEntry.expires_on)
        .all()
    )
    return [r for r in rows if describe_expiry(r.expires_on, r.status, today)[1] in ("soon", "expired")]


def digest_lines(db: Session, today: date) -> list[dict]:
    """The same list, flattened for the weekly email template."""
    out = []
    for row in expiring_entries(db, today):
        days, state = describe_expiry(row.expires_on, row.status, today)
        out.append({
            "project": row.project.name if row.project else (row.project_label or "-"),
            "provider": row.provider.name if row.provider else "-",
            "purpose": row.purpose or "",
            "expires_on": row.expires_on,
            "days": days,
            "state": state,
            "account_email": row.account_email or "",
        })
    return out
