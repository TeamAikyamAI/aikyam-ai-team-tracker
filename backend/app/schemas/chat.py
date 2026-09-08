from datetime import datetime
from pydantic import BaseModel


class ChatAskRequest(BaseModel):
    question: str
    session_id: str | None = None


class ChatMessageOut(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatAskResponse(BaseModel):
    session_id: str
    answer: str


class ChatConversationOut(BaseModel):
    """Admin view: one conversation, summarised."""
    session_id: str
    user_id: int | None
    user_name: str | None
    started_at: datetime
    last_at: datetime
    message_count: int
    first_question: str
