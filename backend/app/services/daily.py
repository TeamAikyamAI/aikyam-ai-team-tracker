"""Deriving a person's day from their task rows.

The only place a timezone is used is :func:`today_for` - when someone ticks a
task we need to know which local day that counts as. Everything after that is
plain date arithmetic, which is what keeps the day views identical on Postgres
and SQLite and immune to the server being off overnight.
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.daily_task import DailyTask
from app.services import settings as cfg


def tzinfo_for(db: Session) -> ZoneInfo:
    """The team's working timezone, from Admin > Settings (falls back to UTC)."""
    name = (cfg.get(db, "digest_timezone") or "UTC").strip()
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def today_for(db: Session) -> date:
    """The local business day 'now' falls in."""
    return datetime.now(tzinfo_for(db)).date()


def _base(db: Session, user_id: int):
    return db.query(DailyTask).filter(
        DailyTask.user_id == user_id, DailyTask.parked_at.is_(None)
    )


def open_on(db: Session, user_id: int, day: date) -> list[DailyTask]:
    """Still to do at the end of ``day``: planned by then, not finished by then.

    This is where rollover happens - a task from three days ago that is still
    unticked satisfies both conditions, so it simply appears again today.
    """
    return (
        _base(db, user_id)
        .filter(
            DailyTask.task_date <= day,
            or_(DailyTask.completed_on.is_(None), DailyTask.completed_on > day),
        )
        .order_by(DailyTask.task_date.asc(), DailyTask.sort_order.asc(), DailyTask.id.asc())
        .all()
    )


def done_on(db: Session, user_id: int, day: date) -> list[DailyTask]:
    """Finished on ``day`` - regardless of which day it was originally planned for."""
    return (
        _base(db, user_id)
        .filter(DailyTask.completed_on == day)
        .order_by(DailyTask.completed_at.asc(), DailyTask.id.asc())
        .all()
    )


def carried_days(task: DailyTask, day: date) -> int:
    """How many days this task has been rolling over by ``day``. 0 = planned today."""
    return max(0, (day - task.task_date).days)


def summary(db: Session, user_id: int, day: date) -> dict:
    open_items = open_on(db, user_id, day)
    done_items = done_on(db, user_id, day)
    return {
        "done": len(done_items),
        "pending": len(open_items),
        "carried": sum(1 for t in open_items if carried_days(t, day) > 0),
    }


def mark(db: Session, task: DailyTask, completed: bool) -> DailyTask:
    """Tick or untick, stamping the local day the tick belongs to."""
    if completed:
        if task.completed_at is None:
            now = datetime.now(timezone.utc)
            task.completed_at = now
            task.completed_on = now.astimezone(tzinfo_for(db)).date()
    else:
        task.completed_at = None
        task.completed_on = None
    return task
