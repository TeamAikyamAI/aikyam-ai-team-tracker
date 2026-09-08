"""The in-app assistant.

How it works, and why:

The model is not handed a dump of the database any more. It gets two things -
a summary of headline figures already counted by the database, and a set of
named read-only tools it can call to fetch exactly what a question needs
(see tracker_tools.py). That change buys three things:

  * Counts are right. "How many are completed" is answered by a COUNT, not by
    a model tallying JSON.
  * It scales. A tracker with 500 projects no longer has to fit in the prompt.
  * Scope is enforced in the query, not in the prompt. A requestor's tools
    return requestor-visible rows however the question is phrased.

It still never writes. There is no tool that can change anything.
"""
import json

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import settings as cfg
from app.services import deterministic
from app.services import tracker_tools

MAX_HISTORY_TURNS = 12
MAX_TOOL_ROUNDS = 5  # a question needing more than this is a question we should not guess at


def _is_form_turn(db: Session, user: User, session_id: str | None) -> bool:
    """Is this session part-way through a guided form right now?"""
    from app.services import project_intake as intake
    return session_id is not None and intake.get_draft(db, session_id, user) is not None


def _starts_form(question: str) -> bool:
    from app.services import project_intake as intake
    return intake.wants_to_add(question)


def _system_prompt(db: Session, user: User, summary: dict) -> str:
    bot_name = cfg.get(db, "chatbot_name")
    app_name = cfg.get(db, "app_name")
    about = cfg.get(db, "chatbot_about")

    if user.role == "requestor":
        scope = (
            "This person is a requestor from a business vertical. Your tools return only what they "
            "can already see in the app: the project queue, their own service requests, and the "
            "background below. If they ask about internal blockers, owners or other people's "
            "requests, say plainly that this isn't information you can share, and suggest they "
            "contact the AI team."
        )
    else:
        scope = (
            "This person is on the AI & Automation team, so your tools reach internal detail: "
            "update logs, owners, blockers and every service request."
        )

    return (
        f"You are {bot_name}, the assistant built into {app_name}.\n\n"
        f"You are speaking with {user.name} ({user.role}). {scope}\n\n"
        "BACKGROUND ABOUT THE TEAM (set by an admin):\n"
        f"{about}\n\n"
        "CURRENT FIGURES - these were counted by the database just now and are exact. "
        "Use them directly rather than recounting anything:\n"
        f"{json.dumps(summary, default=str)}\n\n"
        "Rules:\n"
        "- For anything beyond the figures above, call a tool. Never guess at a project name, "
        "date, owner or number.\n"
        "- If a tool returns an error or an empty result, say so plainly instead of inventing an answer.\n"
        "- Be concise and friendly. Short bullet lists for multiple items.\n"
        "- You are read-only. If asked to change something, explain that and point to the right "
        "screen in the app.\n"
        "- Answer only from this tracker's data and the background above; you are not a general "
        "purpose assistant."
    )


def answer(db: Session, user: User, question: str, history: list[dict],
           session_id: str | None = None) -> str:
    """history: prior turns as [{'role': 'user'|'assistant', 'content': str}].

    ``session_id`` lets the model-free path carry a multi-step guided flow (see
    project_intake). Without one - the stateless Ask page - it just answers.
    """
    if not cfg.get(db, "chatbot_enabled"):
        return "The assistant is currently switched off. An admin can turn it back on in Admin > Settings."

    provider = cfg.get(db, "ai_provider")
    api_key = cfg.get(db, "anthropic_api_key")
    has_model = bool(cfg.get(db, "ai_enabled")) and provider == "anthropic" and bool(api_key)

    if not has_model:
        # No language model configured. The tool layer still holds exact, role-scoped
        # data, so answer the questions we can parse and be honest about the rest.
        direct = deterministic.try_answer(db, user, question, session_id)
        return direct if direct is not None else deterministic.cannot_answer_message(db, user)

    # A guided form behaves the same whether or not a model is configured: it is
    # a form, and the model must not answer over the top of it. Checked BEFORE
    # handing the turn over, because handling it may finish and clear the form.
    if _is_form_turn(db, user, session_id) or (session_id and _starts_form(question)):
        handled = deterministic.try_answer(db, user, question, session_id)
        if handled is not None:
            return handled

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    model = cfg.get(db, "ai_model")
    max_tokens = int(cfg.get(db, "ai_max_tokens"))

    summary = tracker_tools.get_summary(db, user)
    system = _system_prompt(db, user, summary)

    messages: list[dict] = [
        {"role": m["role"], "content": m["content"]}
        for m in history[-MAX_HISTORY_TURNS:]
        if m.get("content")
    ]
    messages.append({"role": "user", "content": question})

    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=tracker_tools.schemas(),
            messages=messages,
        )

        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text").strip()

        # Run every tool the model asked for, then hand the results back.
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            output = tracker_tools.run(db, user, block.name, dict(block.input or {}))
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(output, default=str),
            })
        messages.append({"role": "user", "content": results})

    # Ran out of rounds: answer from what we have rather than looping forever.
    final = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system + "\n\nAnswer now from what you already have. Do not call any more tools.",
        messages=messages,
    )
    return "".join(b.text for b in final.content if b.type == "text").strip()
