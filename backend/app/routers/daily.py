from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_feature
from app.models.daily_task import DailyTask
from app.models.user import User
from app.schemas.daily import (
    DailyTaskCreate,
    DailyTaskOut,
    DailyTaskUpdate,
    DayView,
    TeamDayRow,
    TeamDayView,
)
from app.services import daily
from app.services import permissions as perms

router = APIRouter(prefix="/daily-tasks", tags=["daily"])


def _out(task: DailyTask, day: date) -> DailyTaskOut:
    return DailyTaskOut(
        id=task.id,
        user_id=task.user_id,
        title=task.title,
        task_date=task.task_date,
        completed_at=task.completed_at,
        completed_on=task.completed_on,
        sort_order=task.sort_order,
        carried_days=daily.carried_days(task, day),
    )


def _owned(db: Session, task_id: int, user: User) -> DailyTask:
    """A task the caller may change.

    Reading someone else's day is a permission ('team_day'); writing to it is
    not a permission at all. Nobody ticks, edits or deletes another person's
    task, admin included - a daily list is only honest if it is the owner's.
    """
    task = db.get(DailyTask, task_id)
    if task is None or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("", response_model=DayView)
def get_day(
    day: date | None = Query(default=None, alias="date"),
    user_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("my_day", "team_day")),
):
    """One person's day. Defaults to the caller, today."""
    target = user
    if user_id is not None and user_id != user.id:
        if not perms.is_allowed(db, user.role, "team_day"):
            raise HTTPException(status_code=403, detail="Not permitted for this role")
        found = db.get(User, user_id)
        if found is None:
            raise HTTPException(status_code=404, detail="User not found")
        target = found
    elif not perms.is_allowed(db, user.role, "my_day"):
        raise HTTPException(status_code=403, detail="Not permitted for this role")

    day = day or daily.today_for(db)
    open_items = daily.open_on(db, target.id, day)
    done_items = daily.done_on(db, target.id, day)
    return DayView(
        date=day,
        user_id=target.id,
        user_name=target.name,
        is_own=target.id == user.id,
        open=[_out(t, day) for t in open_items],
        done=[_out(t, day) for t in done_items],
        summary=daily.summary(db, target.id, day),
    )


@router.get("/team", response_model=TeamDayView)
def get_team_day(
    day: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("team_day")),
):
    """Everyone's day at a glance - counts only, the lists open one at a time."""
    day = day or daily.today_for(db)
    people = (
        db.query(User)
        .filter(User.is_active == True, User.role.in_(["admin", "member"]))  # noqa: E712
        .order_by(User.name)
        .all()
    )
    return TeamDayView(
        date=day,
        rows=[
            TeamDayRow(user_id=p.id, user_name=p.name, summary=daily.summary(db, p.id, day))
            for p in people
        ],
    )


@router.post("", response_model=DailyTaskOut, status_code=201)
def create_task(
    payload: DailyTaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("my_day")),
):
    day = payload.task_date or daily.today_for(db)
    highest = (
        db.query(DailyTask.sort_order)
        .filter(DailyTask.user_id == user.id, DailyTask.task_date == day)
        .order_by(DailyTask.sort_order.desc())
        .first()
    )
    task = DailyTask(
        user_id=user.id,
        title=payload.title.strip(),
        task_date=day,
        sort_order=(highest[0] + 1) if highest else 0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _out(task, day)


@router.patch("/{task_id}", response_model=DailyTaskOut)
def update_task(
    task_id: int,
    payload: DailyTaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("my_day")),
):
    task = _owned(db, task_id, user)
    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        task.title = data["title"].strip()
    if "task_date" in data and data["task_date"] is not None:
        task.task_date = data["task_date"]
    if "sort_order" in data and data["sort_order"] is not None:
        task.sort_order = data["sort_order"]
    if "completed" in data and data["completed"] is not None:
        daily.mark(db, task, data["completed"])
    db.commit()
    db.refresh(task)
    return _out(task, daily.today_for(db))


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("my_day")),
):
    task = _owned(db, task_id, user)
    db.delete(task)
    db.commit()
