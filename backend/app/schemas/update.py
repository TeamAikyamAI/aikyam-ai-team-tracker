from datetime import datetime
from pydantic import BaseModel


class UpdateCreate(BaseModel):
    project_id: int
    plan: str | None = None
    progress: str | None = None
    problem: str | None = None
    raw_bullets: str | None = None


class UpdateOut(BaseModel):
    id: int
    project_id: int
    author_id: int
    plan: str | None
    progress: str | None
    problem: str | None
    raw_bullets: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class QuickFillRequest(BaseModel):
    bullets: str


class QuickFillResponse(BaseModel):
    plan: str
    progress: str
    problem: str
