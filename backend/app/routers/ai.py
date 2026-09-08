from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_feature
from app.models.user import User
from app.schemas.ai import AskRequest, AskResponse
from app.services import chatbot

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db), user: User = Depends(require_feature("ask"))):
    """Ask-the-Tracker: the full-page version of the assistant.

    Deliberately the same engine as the chat widget - one set of tools, one set
    of scoping rules, one place to fix a bug. It just doesn't keep a
    conversation thread.
    """
    return AskResponse(answer=chatbot.answer(db, user, payload.question, history=[]))
