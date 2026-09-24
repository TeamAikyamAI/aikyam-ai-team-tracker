from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, Boolean, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApiProvider(Base):
    """The master list of key providers - Gemini, Groq, Azure, Deep-infra.

    Kept as a table rather than free text so "Groq" and "groq" are one thing
    and the count of keys per provider is answerable. Admin-editable, like
    verticals and statuses: nothing about the list is written into code.
    """

    __tablename__ = "api_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiKeyEntry(Base):
    """One row of the team's API key register.

    This is a REGISTER, not a vault: it records which provider's key is used by
    which project, what for, whose account it sits on and when it expires. The
    secret itself is never stored here and there is no field for it - the point
    is to know what exists and what is about to lapse, not to hand the value
    out through a web page.
    """

    __tablename__ = "api_key_entries"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Linked to a tracker project where one exists; otherwise a typed label,
    # because plenty of keys belong to work that is not a tracker project
    # (bulk emailing, a scraping job).
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    project = relationship("Project")
    project_label: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Null only while the key is pending: the work is planned but nobody has
    # settled which vendor it will come from. An active key always has one.
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("api_providers.id"), nullable=True)
    provider = relationship("ApiProvider")

    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Null means no expiry date - which is a real answer, not missing data.
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    # The account the key sits on, so whoever has to renew it knows where to go.
    account_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # active | pending | revoked. "Expired" is never stored - it is worked out
    # from expires_on, so a row cannot drift out of step with its own date.
    status: Mapped[str] = mapped_column(String(20), default="active")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by = relationship("User", foreign_keys=[created_by_id])
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
