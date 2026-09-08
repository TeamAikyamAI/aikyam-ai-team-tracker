from pydantic import BaseModel


class QueueItem(BaseModel):
    """Read-only, limited view of a project for Requestor users - no internal
    update-log detail, just enough to see what's already in flight."""
    id: int
    name: str
    vertical_name: str
    status_name: str
    status_color: str
