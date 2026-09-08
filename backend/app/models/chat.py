from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatMessage(Base):
    """One turn of a conversation with the in-app assistant.

    Stored so an admin can see what people are asking the bot, in the same
    spirit as the audit trail. Grouped into conversations by `session_id`.
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user = relationship("User")

    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
