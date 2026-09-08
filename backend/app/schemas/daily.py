from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DailyTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    task_date: date | None = None  # defaults to the team's local today


class DailyTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    completed: bool | None = None
    task_date: date | None = None
    sort_order: int | None = None


class DailyTaskOut(BaseModel):
    id: int
    user_id: int
    title: str
    task_date: date
    completed_at: datetime | None
    completed_on: date | None
    sort_order: int
    carried_days: int = 0

    model_config = ConfigDict(from_attributes=True)


class DaySummary(BaseModel):
    done: int
    pending: int
    carried: int


class DayView(BaseModel):
    date: date
    user_id: int
    user_name: str
    is_own: bool
    open: list[DailyTaskOut]
    done: list[DailyTaskOut]
    summary: DaySummary


class TeamDayRow(BaseModel):
    user_id: int
    user_name: str
    summary: DaySummary


class TeamDayView(BaseModel):
    date: date
    rows: list[TeamDayRow]
