from datetime import datetime
from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    user_name: str | None = None
    action: str
    entity_type: str | None
    entity_id: int | None
    details: str | None
    created_at: datetime

    class Config:
        from_attributes = True
