from typing import Any
from pydantic import BaseModel


class SettingItem(BaseModel):
    key: str
    group: str
    label: str
    type: str
    help: str = ""
    options: list[str] = []
    min: int | None = None
    max: int | None = None
    value: Any = None
    """True when a secret already has a stored value (the value itself is never returned)."""
    is_set: bool = False
    """True when the value comes from backend/.env and cannot be edited here."""
    env_only: bool = False


class SettingsResponse(BaseModel):
    items: list[SettingItem]


class SettingsUpdate(BaseModel):
    values: dict[str, Any]


class PublicSettings(BaseModel):
    app_name: str
    org_name: str
    login_footer: str
    email_domain: str
    chatbot_enabled: bool
    chatbot_name: str
    chatbot_greeting: str
    chatbot_suggestions: str


class TestEmailResult(BaseModel):
    ok: bool
    detail: str


class DigestPreviewResult(BaseModel):
    ok: bool
    emails_sent: int
    detail: str
