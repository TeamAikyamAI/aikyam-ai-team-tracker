"""Adding a project by answering the assistant's questions.

This is the one thing the assistant is allowed to write, and it is deliberately
not a free-form instruction. It is a fixed sequence of questions with a summary
and an explicit "save" at the end, so nothing is ever created from a sentence
the bot only half understood. Everything else stays read-only.

The flow lives in the database (chat_drafts), keyed by the chat session, so a
half-finished answer survives a restart and belongs to exactly one person.

Verticals, statuses and owners are all read from the database when the question
is asked - none of them are written into this file.
"""
import json
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.chat_draft import ChatDraft
from app.models.project import Project
from app.models.status import Status
from app.models.user import User
from app.models.vertical import Vertical
from app.services import daily
from app.services import permissions as perms
from app.services.audit import log_action

KIND = "new_project"

# Words that get someone out of the flow at any point.
CANCEL_WORDS = {"cancel", "stop", "quit", "abort", "exit", "never mind", "nevermind", "leave it"}
SKIP_WORDS = {"skip", "-", "none", "no", "n/a", "na", "nil", "later", "blank"}
YES_WORDS = {"yes", "y", "yeah", "yep", "ok", "okay", "sure", "add", "more", "continue"}
# Words that mean "stop asking and save it". The fork question offers "save"
# explicitly, so people keep typing it through the optional questions - without
# this it was stored as the answer instead, and a project quietly ended up with
# the description "save".
SAVE_WORDS = {"save", "save it", "done", "finish", "finished", "that's it", "thats it"}

# The question chain. Required first, then the optional detail block.
REQUIRED_STEPS = ("name", "vertical", "status", "assigned_by")
OPTIONAL_STEPS = ("description", "assigned_on", "target_date", "owners", "remarks")


# --------------------------------------------------------------------------
# draft storage
# --------------------------------------------------------------------------

def get_draft(db: Session, session_id: str, user: User) -> ChatDraft | None:
    if not session_id:
        return None
    return (
        db.query(ChatDraft)
        .filter(ChatDraft.session_id == session_id, ChatDraft.user_id == user.id)
        .first()
    )


def _save(db: Session, draft: ChatDraft, step: str, data: dict) -> None:
    draft.step = step
    draft.data = json.dumps(data, default=str)
    db.commit()


def _clear(db: Session, draft: ChatDraft) -> None:
    db.delete(draft)
    db.commit()


def _data(draft: ChatDraft) -> dict:
    try:
        return json.loads(draft.data or "{}")
    except ValueError:
        return {}


# --------------------------------------------------------------------------
# permission + intent
# --------------------------------------------------------------------------

def may_add(db: Session, user: User) -> bool:
    """Same permission as the New Project button, so the chat is not a way round it."""
    return perms.is_allowed(db, user.role, "projects_manage")


def wants_to_add(q: str) -> bool:
    """Only a clear, unambiguous request starts the flow."""
    q = q.strip().lower().rstrip("?.! ")
    starters = (
        "add a project", "add project", "add a new project", "add new project",
        "create a project", "create project", "create a new project", "create new project",
        "new project", "start a project", "log a project", "register a project",
        "i want to add a project", "can i add a project", "let me add a project",
        "add a project to the tracker", "add project to tracker",
    )
    return q in starters or any(q.startswith(s) for s in starters)


# --------------------------------------------------------------------------
# answer parsing
# --------------------------------------------------------------------------

def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _match_one(answer: str, rows: list, label_of) -> object | None:
    """Match a typed answer against a list of database rows by name.

    Accepts the exact name, a case-insensitive match, a unique prefix, or the
    number shown in the list - whichever the person happens to type.
    """
    a = _norm(answer)
    if not a:
        return None
    if a.isdigit():
        i = int(a) - 1
        return rows[i] if 0 <= i < len(rows) else None
    for r in rows:
        if _norm(label_of(r)) == a:
            return r
    starts = [r for r in rows if _norm(label_of(r)).startswith(a)]
    if len(starts) == 1:
        return starts[0]
    contains = [r for r in rows if a in _norm(label_of(r))]
    if len(contains) == 1:
        return contains[0]
    return None


def _parse_date(answer: str, today: date) -> date | None | str:
    """A date, None to skip, or a string describing what went wrong."""
    a = _norm(answer)
    if a in SKIP_WORDS:
        return None
    if a == "today":
        return today
    if a == "yesterday":
        return today - timedelta(days=1)
    if a == "tomorrow":
        return today + timedelta(days=1)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(answer.strip(), fmt).date()
        except ValueError:
            continue
    return 'I could not read that as a date. Try 25/08/2026, or "today", or "skip".'


def _numbered(rows: list, label_of) -> str:
    return "\n".join(f"  {i + 1}. {label_of(r)}" for i, r in enumerate(rows))


def _active_verticals(db: Session) -> list[Vertical]:
    return db.query(Vertical).filter(Vertical.is_active == True).order_by(Vertical.name).all()  # noqa: E712


def _active_statuses(db: Session) -> list[Status]:
    return db.query(Status).filter(Status.is_active == True).order_by(Status.sort_order).all()  # noqa: E712


def _team(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.is_active == True, User.role.in_(["admin", "member"]))  # noqa: E712
        .order_by(User.name)
        .all()
    )


# --------------------------------------------------------------------------
# the questions
# --------------------------------------------------------------------------

def _ask(db: Session, step: str, data: dict) -> str:
    if step == "name":
        return 'What is the project called?\n\n(Type "cancel" at any point to stop.)'
    if step == "vertical":
        rows = _active_verticals(db)
        return "Which vertical is it for?\n" + _numbered(rows, lambda v: v.name)
    if step == "status":
        rows = _active_statuses(db)
        return "What status should it start in?\n" + _numbered(rows, lambda s: s.name)
    if step == "assigned_by":
        return "Who asked for it? (the person or vertical head who assigned it)"
    if step == "more":
        return ('Got the essentials. Add more details, or save it as it is?\n\n'
                '"more" to add description, dates, owners and remarks\n'
                '"save" to save it now')
    if step == "description":
        return 'A short description of the project? (or "skip")'
    if step == "assigned_on":
        return 'What date was it assigned? (e.g. 25/08/2026, "today", or "skip")'
    if step == "target_date":
        return 'Target completion date? (e.g. 30/09/2026 or "skip")'
    if step == "owners":
        rows = _team(db)
        return ('Who on the team will own it? Comma-separated, or "me", or "skip".\n'
                + _numbered(rows, lambda u: u.name))
    if step == "remarks":
        return 'Any remarks? These stay internal to the team. (or "skip")'
    if step == "confirm":
        return _summary(db, data) + '\n\nSave this? ("save" or "cancel")'
    return "Something went wrong with this form. Type \"cancel\" and start again."


def _summary(db: Session, data: dict) -> str:
    vertical = db.get(Vertical, data["vertical_id"]) if data.get("vertical_id") else None
    status = db.get(Status, data["status_id"]) if data.get("status_id") else None
    owners = (
        db.query(User).filter(User.id.in_(data["owner_ids"])).all() if data.get("owner_ids") else []
    )
    lines = [
        "Here is what I have:",
        f"  Project: {data.get('name')}",
        f"  Vertical: {vertical.name if vertical else '-'}",
        f"  Status: {status.name if status else '-'}",
        f"  Assigned by: {data.get('assigned_by') or '-'}",
    ]
    if data.get("description"):
        lines.append(f"  Description: {data['description']}")
    if data.get("assigned_on"):
        lines.append(f"  Date of assignment: {data['assigned_on']}")
    if data.get("target_date"):
        lines.append(f"  Target date: {data['target_date']}")
    if owners:
        lines.append(f"  Owners: {', '.join(u.name for u in owners)}")
    if data.get("remarks"):
        lines.append(f"  Remarks: {data['remarks']}")
    return "\n".join(lines)


def _next_step(step: str) -> str:
    chain = list(REQUIRED_STEPS) + ["more"] + list(OPTIONAL_STEPS) + ["confirm"]
    i = chain.index(step)
    return chain[i + 1]


# --------------------------------------------------------------------------
# entry points
# --------------------------------------------------------------------------

def start(db: Session, user: User, session_id: str) -> str:
    if not session_id:
        return ("I can walk you through adding a project in the chat window (the button in the "
                "bottom corner) - this page answers one question at a time and cannot hold a form. "
                "You can also use the New Project button on the dashboard.")
    existing = get_draft(db, session_id, user)
    if existing:
        _clear(db, existing)
    draft = ChatDraft(session_id=session_id, user_id=user.id, kind=KIND, step="name", data="{}")
    db.add(draft)
    db.commit()
    return "Let's add a project. " + _ask(db, "name", {})


def handle(db: Session, user: User, draft: ChatDraft, answer: str) -> str:
    """Take one answer, advance the flow, and return the next thing to say."""
    a = _norm(answer)
    data = _data(draft)
    step = draft.step

    if a in CANCEL_WORDS:
        _clear(db, draft)
        return "Cancelled - nothing was saved."

    # "save" is a command everywhere in the optional block, not an answer.
    # Whatever has been filled in so far goes straight to the summary.
    if step in OPTIONAL_STEPS and a in SAVE_WORDS:
        _save(db, draft, "confirm", data)
        return _ask(db, "confirm", data)

    # ---- required -------------------------------------------------------
    if step == "name":
        name = answer.strip()
        if len(name) < 2:
            return "That name looks too short. What is the project called?"
        if len(name) > 200:
            return "That name is too long (200 characters max). What should I call it?"
        taken = db.query(Project.id).filter(func.lower(Project.name) == name.lower()).first()
        if taken:
            return f'There is already a project called "{name}". Give me a different name, or "cancel".'
        data["name"] = name

    elif step == "vertical":
        rows = _active_verticals(db)
        match = _match_one(answer, rows, lambda v: v.name)
        if match is None:
            return "I did not recognise that vertical. Pick one by name or number:\n" + _numbered(
                rows, lambda v: v.name
            )
        data["vertical_id"] = match.id

    elif step == "status":
        rows = _active_statuses(db)
        match = _match_one(answer, rows, lambda s: s.name)
        if match is None:
            return "I did not recognise that status. Pick one by name or number:\n" + _numbered(
                rows, lambda s: s.name
            )
        data["status_id"] = match.id

    elif step == "assigned_by":
        who = answer.strip()
        if len(who) > 120:
            return "That is a bit long for a name (120 characters max). Who asked for it?"
        data["assigned_by"] = None if a in SKIP_WORDS else who

    # ---- the fork -------------------------------------------------------
    elif step == "more":
        # "no" is the natural answer to "add more details, or save it as it is?"
        # and it plainly means save - so treat the skip words as save here too.
        if a in SAVE_WORDS or a in SKIP_WORDS:
            _save(db, draft, "confirm", data)
            return _ask(db, "confirm", data)
        if a in YES_WORDS or a.startswith("more"):
            _save(db, draft, "description", data)
            return _ask(db, "description", data)
        return 'Type "more" to add the extra details, or "save" to save it as it is.'

    # ---- optional -------------------------------------------------------
    elif step == "description":
        data["description"] = None if a in SKIP_WORDS else answer.strip()

    elif step in ("assigned_on", "target_date"):
        parsed = _parse_date(answer, daily.today_for(db))
        if isinstance(parsed, str):
            return parsed
        data[step] = parsed.isoformat() if parsed else None

    elif step == "owners":
        if a in SKIP_WORDS:
            data["owner_ids"] = []
        elif a in ("me", "myself"):
            data["owner_ids"] = [user.id]
        else:
            rows = _team(db)
            ids, unknown = [], []
            for part in answer.split(","):
                if not part.strip():
                    continue
                match = _match_one(part, rows, lambda u: u.name)
                if match is None:
                    unknown.append(part.strip())
                else:
                    ids.append(match.id)
            if unknown:
                return (f"I could not find: {', '.join(unknown)}. Pick from:\n"
                        + _numbered(rows, lambda u: u.name)
                        + '\n\nOr "me", or "skip".')
            data["owner_ids"] = list(dict.fromkeys(ids))

    elif step == "remarks":
        data["remarks"] = None if a in SKIP_WORDS else answer.strip()

    # ---- confirm --------------------------------------------------------
    elif step == "confirm":
        if a in ("save", "yes", "y", "confirm", "ok", "okay", "save it", "go ahead"):
            return _create(db, user, draft, data)
        return 'Type "save" to add it, or "cancel" to throw it away.'

    else:
        _clear(db, draft)
        return "That form got into a state I did not expect, so I have cleared it. Try again?"

    nxt = _next_step(step)
    _save(db, draft, nxt, data)
    return _ask(db, nxt, data)


def _create(db: Session, user: User, draft: ChatDraft, data: dict) -> str:
    # Re-check the name here as well: someone may have created it in the UI
    # while this conversation was open.
    name = data["name"]
    if db.query(Project.id).filter(func.lower(Project.name) == name.lower()).first():
        _clear(db, draft)
        return (f'Someone added a project called "{name}" while we were talking, so I have not '
                "created a second one. Nothing was saved.")

    project = Project(
        name=name,
        description=data.get("description"),
        vertical_id=data["vertical_id"],
        status_id=data["status_id"],
        assigned_by=data.get("assigned_by"),
        assigned_on=date.fromisoformat(data["assigned_on"]) if data.get("assigned_on") else None,
        target_date=date.fromisoformat(data["target_date"]) if data.get("target_date") else None,
        remarks=data.get("remarks"),
        created_by_id=user.id,
    )
    owner_ids = data.get("owner_ids") or []
    project.owners = db.query(User).filter(User.id.in_(owner_ids)).all() if owner_ids else []
    db.add(project)
    db.commit()
    db.refresh(project)

    log_action(db, user.id, "create_project_via_assistant", "project", project.id)
    _clear(db, draft)

    status = db.get(Status, project.status_id)
    return (f'Added "{project.name}" under {status.name if status else "its status"}. '
            "It is on the dashboard now, and it will be included the next time you export to Excel.")
