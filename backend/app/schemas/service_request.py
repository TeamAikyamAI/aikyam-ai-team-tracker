import os
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ServiceRequestCreate(BaseModel):
    vertical_id: int
    title: str
    description: str | None = None
    # brd file is uploaded separately as multipart; this is filled server-side


class ServiceRequestReview(BaseModel):
    decision: str  # approved | rejected | on_hold
    review_notes: str | None = None
    # fields used only when decision == approved, to seed the new Project
    status_id: int | None = None
    target_date: str | None = None


class ServiceRequestOut(BaseModel):
    """Public shape of a request. The server-side storage path is read from
    the model but never serialised - the file itself is fetched through the
    authenticated GET /requests/{id}/brd endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vertical_id: int
    requestor_id: int
    title: str
    description: str | None
    brd_file_path: str = Field(exclude=True)
    status: str
    reviewed_by_id: int | None
    reviewed_at: datetime | None
    review_notes: str | None
    created_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def brd_filename(self) -> str:
        """The name the requestor uploaded, recovered from ``<uuid>_<name>``."""
        base = os.path.basename(self.brd_file_path or "")
        return base.split("_", 1)[1] if "_" in base else base
