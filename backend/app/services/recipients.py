"""Who else goes on a request's emails, as chosen by the requestor.

A requestor knows their own vertical better than the app does: who is standing
in for a head this week, which manager wants to see the intake, which colleague
is doing the UAT. So the Apply form lets them name extra people, and that one
choice follows the request through all three of its emails - submitted,
reviewed, delivered.

Two rules keep it safe:
  * an address must belong to an active user of the tracker, or sit on the
    company's own email domain (Admin > Settings > Organisation > Email domain).
    Anything else is refused with the address named, so nobody can quietly copy
    internal project detail to a personal or outside mailbox;
  * the list is capped, so a form cannot turn into a mailing list.
"""
import json
import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.services import settings as cfg

MAX_RECIPIENTS = 10

# Deliberately loose: the real check is the domain / known-user rule below.
_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RecipientError(ValueError):
    """Raised with a message meant to be shown to the person who typed it."""


def parse(raw: str | None) -> list[str]:
    """Read a stored JSON list back. Never raises - a corrupt value is simply
    no extra recipients rather than a broken email."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if isinstance(v, str)]


def dump(emails: list[str]) -> str | None:
    return json.dumps(emails) if emails else None


def _split(raw: str | None) -> list[str]:
    """Accept a JSON array or a plain comma/semicolon/newline separated list -
    the form sends JSON, a human poking the API may not."""
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("["):
        try:
            value = json.loads(text)
            if isinstance(value, list):
                return [str(v).strip() for v in value if str(v).strip()]
        except ValueError:
            pass
    return [part.strip() for part in re.split(r"[,;\n]+", text) if part.strip()]


def clean(db: Session, raw: str | None, *, field: str) -> list[str]:
    """Validate what the requestor typed and return it ready to store.

    ``field`` only shapes the error message ("To" / "Cc").
    """
    wanted = _split(raw)
    if not wanted:
        return []

    # A bare number is a user the person picked by name in the form; the
    # directory deliberately never exposes addresses, so we resolve them here.
    ids = [int(v) for v in wanted if v.isdigit()]
    by_id: dict[int, str] = {}
    if ids:
        rows = (
            db.query(User.id, User.email)
            .filter(User.id.in_(ids), User.is_active == True)  # noqa: E712
            .all()
        )
        by_id = {uid: email for uid, email in rows}
        missing = [str(i) for i in ids if i not in by_id]
        if missing:
            raise RecipientError(
                f"{field}: one of the people you picked is no longer active. "
                "Remove them and try again."
            )

    resolved = [by_id[int(v)] if v.isdigit() else v for v in wanted]

    # De-duplicate case-insensitively but keep what the person typed.
    seen: dict[str, str] = {}
    for address in resolved:
        seen.setdefault(address.lower(), address)
    ordered = list(seen.values())

    if len(ordered) > MAX_RECIPIENTS:
        raise RecipientError(
            f"{field}: pick at most {MAX_RECIPIENTS} people. "
            f"You listed {len(ordered)}."
        )

    known = {
        email.lower()
        for (email,) in db.query(User.email).filter(User.is_active == True).all()  # noqa: E712
    }
    domain = (cfg.get(db, "email_domain") or "").strip().lower().lstrip("@")

    bad: list[str] = []
    for address in ordered:
        low = address.lower()
        if not _SHAPE.match(address):
            bad.append(address)
        elif low in known:
            continue
        elif domain and low.endswith("@" + domain):
            continue
        else:
            bad.append(address)

    if bad:
        listed = ", ".join(bad)
        where = f" or an address ending in @{domain}" if domain else ""
        raise RecipientError(
            f"{field}: {listed} cannot be added. Pick someone with a tracker "
            f"account{where}."
        )

    return ordered


def merge(*groups: list[str], exclude: list[str] | None = None) -> list[str]:
    """Join recipient lists in order, dropping duplicates and anything already
    on another line - the same person must never appear twice in one email."""
    skip = {e.lower() for e in (exclude or [])}
    out: list[str] = []
    for group in groups:
        for address in group:
            low = address.lower()
            if low and low not in skip:
                skip.add(low)
                out.append(address)
    return out
