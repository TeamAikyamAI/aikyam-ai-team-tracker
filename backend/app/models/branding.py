from datetime import datetime

from sqlalchemy import String, Integer, LargeBinary, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BrandingAsset(Base):
    """A brand asset (currently just the logo) held in the database rather than
    checked into the repo, so an admin can replace it from the Settings screen
    with no deploy. `updated_at` doubles as the cache-busting version token."""

    __tablename__ = "branding_assets"

    id: Mapped[int] = mapped_column(primary_key=True)

    # "logo" today; keeps the table open to favicons/wordmarks later without a migration.
    kind: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    data: Mapped[bytes] = mapped_column(LargeBinary)

    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_by = relationship("User")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
