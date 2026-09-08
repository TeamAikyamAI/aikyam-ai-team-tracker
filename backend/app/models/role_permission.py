from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RolePermission(Base):
    """One row per (role, feature) an admin has explicitly changed.

    Absent row means "use the registry default", exactly like app_settings.
    That keeps a fresh install working before anything is saved, and means a
    feature added in a later version starts from its own sensible default
    rather than from an empty table (which would lock everyone out).
    """

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role", "feature", name="uq_role_permission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(20), index=True)
    feature: Mapped[str] = mapped_column(String(50), index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True)

    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
