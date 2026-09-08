from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    # "admin" | "member" | "requestor" - validated at the API layer, kept as a
    # plain string so new tiers can be introduced without a schema migration.
    role: Mapped[str] = mapped_column(String(20), default="member")

    reports_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reports_to: Mapped["User | None"] = relationship(remote_side=[id], backref="direct_reports")

    # For the top of a reporting chain (e.g. Naman's own manager) who isn't a system user at all - the weekly rollup goes to this address instead.
    external_manager_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Requestor users are tied to the one vertical they represent.
    vertical_id: Mapped[int | None] = mapped_column(ForeignKey("verticals.id"), nullable=True)
    vertical = relationship("Vertical", foreign_keys=[vertical_id])

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
