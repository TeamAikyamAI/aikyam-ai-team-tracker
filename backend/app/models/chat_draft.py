from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChatDraft(Base):
    """A half-finished guided flow in one chat session.

    Kept in the database rather than in process memory so a half-answered
    "add a project" survives a backend restart, and so the draft belongs to one
    user's session rather than to whichever worker happened to serve the turn.

    ``data`` is JSON text: the answers collected so far. Only the assistant
    writes here, and the row is deleted the moment the flow is saved or
    cancelled - nothing accumulates.
    """

    __tablename__ = "chat_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Which guided flow this is. Only "new_project" today; named so a second
    # flow can be added without another migration.
    kind: Mapped[str] = mapped_column(String(40), default="new_project")
    step: Mapped[str] = mapped_column(String(40))
    data: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
