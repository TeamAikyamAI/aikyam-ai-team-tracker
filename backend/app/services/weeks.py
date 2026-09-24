"""What "a week" means, for the whole app.

Nothing here is stored. A week is worked out from the calendar every time it is
asked for - the same principle as the My Day rollover and the API key expiry -
so the Excel export grows a new column next week without anybody running a
migration, a job, or remembering to.

The week starts on the day an admin picked under
Admin > Settings > Weekly digest > Day (``digest_day_of_week``). There is
deliberately no second setting for it: if the digest goes out on a Monday then
the week the export reports on is a Monday week, and the two can never drift.

Both sides of the workbook go through this module - :func:`header_for` writes a
column heading, :func:`parse_header` reads one back - so the export and the
importer cannot disagree about which column is which week.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.services import settings as cfg

# Monday = 0, matching date.weekday(), in the order the setting offers them.
DAYS = cfg.DAYS

HEADER_PREFIX = "Week update"
HEADER_DATE_FORMAT = "%d.%m.%Y"

# "Week update - 08.09.2026", but also the looser spellings a human might type
# into the team's own file: "Week 08-09-2026", "Week ending 8/9/2026".
_HEADER_RE = re.compile(
    r"^\s*week\b.*?(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})\s*$",
    re.IGNORECASE | re.DOTALL,
)


def start_dow(db: Session) -> int:
    """The weekday a week starts on, as ``date.weekday()`` numbers it (Mon=0)."""
    name = str(cfg.get(db, "digest_day_of_week") or "mon").strip().lower()[:3]
    try:
        return DAYS.index(name)
    except ValueError:
        return 0


def week_start_for(day: date, dow: int) -> date:
    """The boundary date of the week ``day`` falls in."""
    return day - timedelta(days=(day.weekday() - dow) % 7)


def recent_weeks(db: Session, today: date, count: int | None = None) -> list[date]:
    """The last ``count`` week boundaries, oldest first, ending with this week.

    ``count`` defaults to the ``export_weeks`` setting. ``today`` is passed in
    rather than read here so the caller decides which clock and timezone the
    "current" week is measured against.
    """
    if count is None:
        count = cfg.get(db, "export_weeks")
    count = max(1, int(count))
    current = week_start_for(today, start_dow(db))
    return [current - timedelta(weeks=n) for n in range(count - 1, -1, -1)]


def header_for(start: date) -> str:
    """The column heading for the week beginning ``start``."""
    return f"{HEADER_PREFIX} - {start.strftime(HEADER_DATE_FORMAT)}"


def parse_header(text: object) -> date | None:
    """The week boundary a column heading refers to, or None if it is not one."""
    match = _HEADER_RE.match(" ".join(str(text or "").split()))
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None
