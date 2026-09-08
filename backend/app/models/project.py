from datetime import datetime, date

from sqlalchemy import String, Text, DateTime, Date, ForeignKey, func, Table, Column, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

project_owners = Table(
    "project_owners",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    vertical_id: Mapped[int] = mapped_column(ForeignKey("verticals.id"))
    vertical = relationship("Vertical")

    status_id: Mapped[int] = mapped_column(ForeignKey("statuses.id"))
    status = relationship("Status")

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_by = relationship("User", foreign_keys=[created_by_id])

    owners = relationship("User", secondary=project_owners)

    # Set when this project originated from an approved service request -
    # keeps the full paper trail from intake to delivery in one record.
    source_request_id: Mapped[int | None] = mapped_column(ForeignKey("service_requests.id"), nullable=True)

    # Who in the business asked for this and when - free text because the
    # assigner is usually a vertical head or manager without a tracker login.
    assigned_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assigned_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Case-insensitive uniqueness: "FD Treasury" and "fd treasury" are one project.
# (Created by migration a7c3e5d9f1b2; declared here so create_all matches.)
Index("ux_projects_name_lower", func.lower(Project.name), unique=True)
