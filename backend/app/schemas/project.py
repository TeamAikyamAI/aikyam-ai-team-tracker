from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    vertical_id: int
    status_id: int
    owner_ids: list[int] = []
    assigned_by: str | None = Field(default=None, max_length=120)
    assigned_on: date | None = None
    remarks: str | None = None
    target_date: date | None = None
    source_request_id: int | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    vertical_id: int | None = None
    status_id: int | None = None
    owner_ids: list[int] | None = None
    assigned_by: str | None = Field(default=None, max_length=120)
    assigned_on: date | None = None
    remarks: str | None = None
    target_date: date | None = None
    actual_completion_date: date | None = None

    # Not stored. Only read when this edit moves the project into a terminal
    # status, and only to decide whether the delivered-email also goes to the
    # whole AI team rather than just the person who asked for the work.
    notify_team: bool = False


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None
    vertical_id: int
    status_id: int
    created_by_id: int
    source_request_id: int | None
    assigned_by: str | None
    assigned_on: date | None
    remarks: str | None
    target_date: date | None
    actual_completion_date: date | None
    created_at: datetime
    updated_at: datetime
    owner_ids: list[int] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _owners_from_relationship(cls, data):
        if not isinstance(data, dict) and hasattr(data, "owners"):
            ids = [o.id for o in data.owners]
            fields = {c.name: getattr(data, c.name) for c in data.__table__.columns}
            return {**fields, "owner_ids": ids}
        return data
