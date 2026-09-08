import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_feature
from app.models.user import User
from app.models.chat import ChatMessage
from app.schemas.chat import (
    ChatAskRequest, ChatAskResponse, ChatMessageOut, ChatConversationOut,
)
from app.services import chatbot, settings as cfg
from app.services.audit import log_action

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

MAX_QUESTION_CHARS = 2000


@router.post("/ask", response_model=ChatAskResponse)
def ask(payload: ChatAskRequest, db: Session = Depends(get_db), user: User = Depends(require_feature("ask"))):
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Please type a question")
    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(status_code=400, detail="That question is too long")

    session_id = payload.session_id or uuid.uuid4().hex

    # Prior turns of this conversation, for follow-up questions like "and that one?"
    history = [
        {"role": m.role, "content": m.content}
        for m in db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at)
        .all()
    ]

    reply = chatbot.answer(db, user, question, history, session_id=session_id)

    db.add(ChatMessage(session_id=session_id, user_id=user.id, role="user", content=question))
    db.add(ChatMessage(session_id=session_id, user_id=user.id, role="assistant", content=reply))
    db.commit()

    return ChatAskResponse(session_id=session_id, answer=reply)


@router.get("/history", response_model=list[ChatMessageOut])
def history(session_id: str = Query(...), db: Session = Depends(get_db), user: User = Depends(require_feature("ask"))):
    """A user can only ever load their own conversation."""
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at)
        .all()
    )


@router.get("/conversations", response_model=list[ChatConversationOut])
def conversations(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(require_feature("admin_panel")),
):
    """Admin oversight: who asked the assistant what, and when."""
    rows = db.query(ChatMessage).order_by(ChatMessage.created_at).all()
    grouped: dict[str, list[ChatMessage]] = {}
    for m in rows:
        grouped.setdefault(m.session_id, []).append(m)

    out = []
    for session_id, msgs in grouped.items():
        first_user_msg = next((m for m in msgs if m.role == "user"), None)
        out.append(ChatConversationOut(
            session_id=session_id,
            user_id=msgs[0].user_id,
            user_name=msgs[0].user.name if msgs[0].user else None,
            started_at=msgs[0].created_at,
            last_at=msgs[-1].created_at,
            message_count=len(msgs),
            first_question=(first_user_msg.content[:200] if first_user_msg else ""),
        ))
    out.sort(key=lambda c: c.last_at, reverse=True)
    log_action(db, admin.id, "view_chat_conversations", "chat_message", None)
    return out[:limit]


@router.get("/conversations/{session_id}", response_model=list[ChatMessageOut])
def conversation_detail(session_id: str, db: Session = Depends(get_db), _: User = Depends(require_feature("admin_panel"))):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
