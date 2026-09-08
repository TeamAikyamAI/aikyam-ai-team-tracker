from datetime import datetime
from pydantic import BaseModel, EmailStr


class VerticalCreate(BaseModel):
    name: str
    head_name: str
    head_email: EmailStr


class VerticalUpdate(BaseModel):
    name: str | None = None
    head_name: str | None = None
    head_email: EmailStr | None = None
    is_active: bool | None = None


class VerticalOut(BaseModel):
    id: int
    name: str
    head_name: str
    head_email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
