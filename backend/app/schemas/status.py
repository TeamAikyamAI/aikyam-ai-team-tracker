from pydantic import BaseModel


class StatusCreate(BaseModel):
    name: str
    color: str = "#6b7280"
    is_terminal: bool = False
    sort_order: int = 0


class StatusUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    is_terminal: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class StatusOut(BaseModel):
    id: int
    name: str
    color: str
    is_terminal: bool
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True
