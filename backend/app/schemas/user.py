from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "member"  # admin | member | requestor
    reports_to_id: int | None = None
    vertical_id: int | None = None
    external_manager_email: EmailStr | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    # Optional new password. Previously the form sent this and the API silently
    # dropped it, so "reset password" looked successful and did nothing.
    password: str | None = None
    role: str | None = None
    reports_to_id: int | None = None
    vertical_id: int | None = None
    external_manager_email: str | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    reports_to_id: int | None
    vertical_id: int | None
    external_manager_email: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserBrief(BaseModel):
    """Just enough to render an owner's name - no email, role or reporting chain."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
