from datetime import datetime

from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Update(Base):
    """A single PPP (Plan / Progress / Problem) log entry against a project.
    The weekly digest email is compiled purely from these rows."""

    __tablename__ = "updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    project = relationship("Project")

    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author = relationship("User")

    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[str | None] = mapped_column(Text, nullable=True)
    problem: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw bullets the user typed, kept alongside the AI Quick-Fill output so
    # nothing is lost even after the AI rewrite.
    raw_bullets: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
