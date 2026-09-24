from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STATUSES = ("active", "pending", "revoked")


class ApiProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    is_active: bool = True
    sort_order: int = 0


class ApiProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    is_active: bool | None = None
    sort_order: int | None = None


class ApiProviderOut(BaseModel):
    id: int
    name: str
    is_active: bool
    sort_order: int
    model_config = ConfigDict(from_attributes=True)


class ApiKeyBase(BaseModel):
    project_id: int | None = None
    project_label: str | None = Field(default=None, max_length=200)
    provider_id: int | None = None
    purpose: str | None = None
    expires_on: date | None = None
    account_email: str | None = Field(default=None, max_length=255)
    status: str = "active"
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def _known_status(cls, v: str) -> str:
        if v not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        return v

    @model_validator(mode="after")
    def _needs_a_project(self):
        """Every key belongs to something. Either it is one of the tracker's
        projects or it is a piece of work that never became one - but it cannot
        be neither, or the register stops answering "what uses this key"."""
        if not self.project_id and not (self.project_label or "").strip():
            raise ValueError("Pick a project, or type a name for the work this key belongs to")
        return self

    @model_validator(mode="after")
    def _provider_unless_pending(self):
        """A key that is already in use came from somewhere. Only a pending
        one - planned, not yet taken out - may have no provider named."""
        if self.provider_id is None and self.status != "pending":
            raise ValueError("Pick a provider, or set the status to pending if it is not decided yet")
        return self


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKeyUpdate(BaseModel):
    project_id: int | None = None
    project_label: str | None = Field(default=None, max_length=200)
    provider_id: int | None = None
    purpose: str | None = None
    expires_on: date | None = None
    account_email: str | None = Field(default=None, max_length=255)
    status: str | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def _known_status(cls, v: str | None) -> str | None:
        if v is not None and v not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        return v


class ApiKeyOut(BaseModel):
    id: int
    project_id: int | None
    project_label: str | None
    provider_id: int | None
    purpose: str | None
    expires_on: date | None
    account_email: str | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Filled in by the router so every screen agrees on the wording.
    project_name: str = ""
    provider_name: str = ""
    days_left: int | None = None
    expiry_state: str = "none"  # none | ok | soon | expired

    model_config = ConfigDict(from_attributes=True)
