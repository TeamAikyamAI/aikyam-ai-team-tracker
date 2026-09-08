"""Claude API wrapper for Quick-Fill: rough bullet notes in, a structured
Plan/Progress/Problem draft out.

Question answering lives in chatbot.py, which uses tool calling rather than a
context dump - both the chat widget and the Ask-the-Tracker page go through it.

The model, token limit, API key and on/off switch are all admin settings, so
moving to a newer model never needs a code change. Both features fail soft: if
AI is off or unconfigured the rest of the app carries on working.
"""
import json

from sqlalchemy.orm import Session

from app.schemas.update import QuickFillResponse
from app.services import settings as cfg


def _client(api_key: str):
    from anthropic import Anthropic
    return Anthropic(api_key=api_key)


def _config(db: Session):
    return (
        bool(cfg.get(db, "ai_enabled")),
        cfg.get(db, "anthropic_api_key"),
        cfg.get(db, "ai_model"),
        int(cfg.get(db, "ai_max_tokens")),
    )


def quick_fill_update(db: Session, bullets: str) -> QuickFillResponse:
    enabled, api_key, model, max_tokens = _config(db)
    if not enabled or not api_key or cfg.get(db, "ai_provider") != "anthropic":
        return QuickFillResponse(plan="", progress=bullets, problem="")

    prompt = (
        "You are helping an AI automation engineer turn rough bullet notes into a "
        "structured weekly status update. Given the raw notes below, produce a JSON "
        "object with exactly three keys: plan (what's planned next), progress "
        "(what was accomplished), problem (any blockers - empty string if none). "
        "Keep each field to 2-4 concise sentences, professional tone, no markdown.\n\n"
        f"Raw notes:\n{bullets}\n\n"
        "Respond with ONLY the JSON object."
    )
    resp = _client(api_key).messages.create(
        model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}]
    )
    text = resp.content[0].text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return QuickFillResponse(plan="", progress=text, problem="")
    return QuickFillResponse(
        plan=data.get("plan", ""), progress=data.get("progress", ""), problem=data.get("problem", "")
    )
