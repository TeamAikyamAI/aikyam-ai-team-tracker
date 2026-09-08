from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, Integer, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DailyTask(Base):
    """One line on somebody's daily to-do list.

    Rollover is deliberately NOT stored. A task carries a ``task_date`` (the day
    it was first planned for) and, once ticked, the local day it was finished on.
    "Today's list" is then derived - everything planned on or before today that
    was not finished before today - so an unfinished task appears on every
    following day by itself, with no midnight job to run.

    That matters here because the app runs on a machine that is not always on:
    a scheduled rollover would silently skip the nights the machine was off and
    could double up if it ever ran twice. Deriving it cannot drift.

    ``completed_on`` is the *local* date (per the configured timezone) rather
    than a timestamp, so every day query is a plain date comparison and behaves
    identically on Postgres and SQLite. ``completed_at`` keeps the exact moment
    for display.
    """

    __tablename__ = "daily_tasks"
    __table_args__ = (
        Index("ix_daily_tasks_user_task_date", "user_id", "task_date"),
        Index("ix_daily_tasks_user_completed_on", "user_id", "completed_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user: Mapped["User"] = relationship("User")  # noqa: F821

    title: Mapped[str] = mapped_column(String(500))

    # The day this was first planned for. Never rewritten by rollover.
    task_date: Mapped[date] = mapped_column(Date, index=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Reserved for the "stop carrying this forever" behaviour; nothing sets it yet.
    parked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
