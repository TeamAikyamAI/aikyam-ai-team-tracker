"""Answering common questions with no language model at all.

The tool layer already returns exact, role-scoped data. For the questions people
actually ask this bot - what's running, what's done, what's overdue, what's in
the queue, what is X working on - a language model was only ever doing two jobs:
picking the right query, and writing the result up in a sentence. Both can be
done in Python, which means the assistant works with no API key, no GPU and no
data leaving the building.

It is a query parser, not an intelligence. When it doesn't recognise a question
it says so rather than guessing - `try_answer` returns None and the caller
explains what it can do.

The vocabulary it matches on (vertical names, status names, project names,
people) is read from the database, never hardcoded - so it keeps working when an
admin renames a vertical or adds a status.
"""
import re
from datetime import date

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.project import Project
from app.models.status import Status
from app.models.vertical import Vertical
from app.services import settings as cfg
from app.services import project_intake as intake
from app.services import tracker_tools as tools

INTERNAL = ("admin", "member")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())


def _any(q: str, *words: str) -> bool:
    """Whole-word matching, deliberately not substring.

    Substring matching quietly breaks on real data: "Accounts" contains "count",
    so "what is the Accounts vertical working on?" was being read as a
    how-many question. Word boundaries keep a vertical's name from colliding
    with the vocabulary.
    """
    return any(re.search(rf"\b{re.escape(w)}(?:s|es)?\b", q) for w in words)


def _bullets(rows: list[str], empty: str) -> str:
    if not rows:
        return empty
    return "\n".join(f"• {r}" for r in rows)


def _project_line(p: dict, *, internal: bool) -> str:
    """One project as a single line.

    Owners and target dates are shown to everyone, because the dashboard shows
    them to everyone: the assistant answering more cautiously than the screen
    the same person can already open only makes the two look inconsistent.
    Internal notes (Remarks, update text, blockers) are the part that stays
    with the team, and those are handled by their own branches below.
    """
    line = f"{p['project']} [{p['status']}]"
    if p.get("vertical"):
        line += f" ({p['vertical']})"
    if p.get("owners"):
        line += f", owners: {', '.join(p['owners'])}"
    if p.get("target_date"):
        line += f", due {p['target_date']}"
    return line


# --------------------------------------------------------------------------

def try_answer(db: Session, user: User, question: str, session_id: str | None = None) -> str | None:
    q = _norm(question)
    if not q.strip():
        return None
    internal = user.role in INTERNAL

    # ---- a guided form already in progress --------------------------------
    # This has to come first. Once "add a project" is running, the next thing
    # typed is an answer to the question just asked - if it fell through to the
    # matching below, a project name like "Compliance Tracker" would be read as
    # a question about that project instead of as the answer.
    draft = intake.get_draft(db, session_id, user) if session_id else None
    if draft is not None:
        return intake.handle(db, user, draft, question)

    if intake.wants_to_add(q):
        if not intake.may_add(db, user):
            return ("Adding projects is for the AI team. To ask for a new piece of work, use "
                    "Apply for Service and attach a BRD signed by your vertical head.")
        return intake.start(db, user, session_id or "")

    summary = tools.get_summary(db, user)

    # ---- greetings -------------------------------------------------------
    if re.fullmatch(r"\s*(hi|hello|hey|hola|namaste|good (morning|afternoon|evening))\s*[a-z ]*", q):
        name = cfg.get(db, "chatbot_name")
        more = ", what's blocked" if internal else ""
        return (
            f"Hello {user.name.split()[0]}! I'm {name}. I can tell you what's running, what's "
            f"finished, what's overdue{more}, what's in the request queue, and what any vertical is "
            "working on. What would you like to know?"
        )

    # ---- who are you / what do you do ------------------------------------
    if _any(q, "who are you", "what are you", "what do you do", "about you", "about us",
            "about the team", "what is this app", "what does this app"):
        return cfg.get(db, "chatbot_about")

    if _any(q, "what can you", "help me", "what questions", "how do you work"):
        extra = "" if not internal else (
            "\n• What's blocked, and recent update notes\n• Who is working on what\n• Service requests and their status"
        )
        return (
            "I read this tracker's live data and answer from it. Try asking:\n"
            "• Which projects are going on right now?\n"
            "• Which projects are completed?\n"
            "• What's overdue?\n"
            "• What is the Accounts vertical working on?\n"
            "• Tell me about <project name>" + extra
        )

    # ---- attempts to change things: refuse -------------------------------
    # Adding a project through the guided flow above is the single exception;
    # everything else still has to happen on a screen, where it is visible and
    # undoable.
    if _any(q, "delete", "remove", "change the", "change status", "change it", "update the", "set the", "set status", "mark",
            "move", "create", "add", "assign", "edit", "rename", "close", "reopen", "approve",
            "reject", "cancel", "archive"):
        where = ("open the project from the dashboard and use its Edit button"
                 if internal else "the AI team can make changes for you")
        extra = ""
        if intake.may_add(db, user):
            extra = ' To add a new project, say "add a project" and I will take you through it.'
        return ("I can only read the tracker, not change it. To make that change, " + where + "." + extra)

    # ---- entities present in the question ---------------------------------
    verticals = db.query(Vertical).filter(Vertical.is_active == True).all()  # noqa: E712
    statuses = db.query(Status).filter(Status.is_active == True).all()  # noqa: E712
    named_vertical = next((v.name for v in verticals if _norm(v.name) in q), None)
    named_status = next((s.name for s in statuses if _norm(s.name) in q), None)

    projects = db.query(Project).all()
    named_project = next(
        (p.name for p in sorted(projects, key=lambda x: -len(x.name)) if _norm(p.name) in q), None
    )

    asks_count = _any(q, "how many", "count", "number of", "total")
    asks_about = re.search(r"\b(tell me about|about|status of|details? (of|for|on)|info(rmation)? (on|about)|what is|what's|show me)\b", q)

    # ---- a specific project ----------------------------------------------
    if named_project and not asks_count:
        d = tools.get_project(db, user, named_project)
        if "error" in d:
            return d["error"]
        parts = [f"{d['project']}", f"Status: {d['status']}"]
        if d.get("vertical"):
            parts.append(f"Vertical: {d['vertical']}")

        # Shown to everyone - the same facts the dashboard already puts on screen.
        if d.get("owners"):
            parts.append(f"Owners: {', '.join(d['owners'])}")
        else:
            parts.append("Owners: not assigned yet")
        if d.get("assigned_by"):
            parts.append(f"Assigned by: {d['assigned_by']}"
                         + (f" on {d['assigned_on']}" if d.get("assigned_on") else ""))
        if d.get("target_date"):
            parts.append(f"Target date: {d['target_date']}")
        if d.get("completed_on"):
            parts.append(f"Completed on: {d['completed_on']}")
        if d.get("description"):
            parts.append(f"\n{d['description']}")

        # Team-only: internal notes and the running commentary behind them.
        if internal:
            if d.get("remarks"):
                parts.append(f"Remarks: {d['remarks']}")
            ups = d.get("recent_updates") or []
            if ups:
                u = ups[0]
                parts.append(f"\nLatest update ({u['date']}, {u['by']}):")
                if u.get("progress"): parts.append(f"  Progress: {u['progress']}")
                if u.get("plan"):     parts.append(f"  Plan: {u['plan']}")
                if u.get("problem"):  parts.append(f"  Problem: {u['problem']}")
        return "\n".join(parts)

    # "tell me about <something>" that matched no project, vertical or status
    if asks_about and not named_vertical and not named_status and not _any(
        q, "vertical", "department", "team", "request", "queue", "overdue", "blocked",
        "complete", "done", "finish", "progress", "going on", "running", "live", "pipeline",
        "status", "you", "this app", "app",
    ):
        wanted = q[asks_about.end():].strip()
        wanted = re.sub(r"\b(the|a|an|projects?|please)\b", " ", wanted).strip()
        wanted = " ".join(wanted.split())
        if wanted:
            return (f"I couldn't find a project called \"{wanted}\". Check the spelling, or ask "
                    "\"which projects are going on right now?\" for the full list.")

    # ---- overdue ----------------------------------------------------------
    if _any(q, "overdue", "late", "delayed", "behind schedule", "past due"):
        res = tools.list_projects(db, user, only_overdue=True, limit=50)
        rows = [_project_line(p, internal=internal) for p in res["projects"]]
        if not rows:
            return "Nothing is overdue right now."
        return f"{len(rows)} project(s) past their target date:\n" + _bullets(rows, "")

    # ---- blocked / problems (internal only) -------------------------------
    if _any(q, "blocked", "blocker", "stuck", "problem", "issue", "risk"):
        if not internal:
            return ("I can't share internal blockers or update notes. For anything on a specific "
                    "request, the AI team can help directly.")
        res = tools.search_updates(db, user, days=60, limit=40)
        rows = [
            f"{u['project']} ({u['date']}): {u['problem']}"
            for u in res.get("updates", []) if (u.get("problem") or "").strip()
        ]
        blocked_status = [
            _project_line(p, internal=True)
            for p in tools.list_projects(db, user, limit=50)["projects"]
            if "block" in p["status"].lower()
        ]
        out = []
        if blocked_status:
            out.append("Projects in a blocked status:\n" + _bullets(blocked_status, ""))
        if rows:
            out.append("Problems noted in the last 60 days:\n" + _bullets(rows[:10], ""))
        return "\n\n".join(out) if out else "No blockers recorded in the last 60 days."

    # ---- service requests / queue ----------------------------------------
    if _any(q, "request", "brd", "apply", "application", "intake"):
        res = tools.list_service_requests(db, user, limit=50)
        rows = [
            f"{r['title']}: {r['status'].replace('_', ' ')}"
            + (f" ({r['vertical']})" if r.get("vertical") else "")
            + (f" · from {r['requested_by']}" if internal and r.get("requested_by") else "")
            for r in res["requests"]
        ]
        header = ("Service requests:" if internal else "Your service requests:")
        if internal and summary.get("service_requests_awaiting_review") is not None:
            header = (f"Service requests: {summary['service_requests_awaiting_review']} awaiting "
                      f"review of {summary.get('service_requests_total', len(rows))} total:")
        return header + "\n" + _bullets(rows, "None yet.")

    # ---- team -------------------------------------------------------------
    if _any(q, "who is on the team", "team member", "who works", "reporting", "reports to", "who is in the team"):
        if not internal:
            return "Team details aren't something I can share. The AI team can be reached through a service request."
        res = tools.get_team(db, user)
        rows = [
            f"{p['name']}: {p['role']}" + (f" · reports to {p['reports_to']}" if p["reports_to"] else "")
            for p in res["people"]
        ]
        return "The team:\n" + _bullets(rows, "No one yet.")

    # ---- verticals --------------------------------------------------------
    if _any(q, "vertical", "department", "business unit") and not named_vertical:
        res = tools.get_verticals(db, user)
        rows = [f"{v['name']}: head: {v['head']}" for v in res["verticals"]]
        return "Business verticals:\n" + _bullets(rows, "None configured.")

    # ---- counts -----------------------------------------------------------
    if asks_count:
        if named_vertical:
            n = summary["projects_by_vertical"].get(named_vertical, 0)
            return f"{named_vertical} has {n} project(s)."
        if named_status:
            n = summary["projects_by_status"].get(named_status, 0)
            return f"{n} project(s) are in '{named_status}'."
        if _any(q, "complete", "done", "finish", "live", "delivered"):
            return f"{summary['completed']} project(s) are completed, {summary['completed_this_month']} of them this month."
        if _any(q, "progress", "going on", "running", "ongoing", "active", "open", "pending"):
            return f"{summary['in_progress']} project(s) are in progress right now."
        if _any(q, "overdue", "late", "delayed"):
            return f"{summary['overdue']} project(s) are overdue."
        if _any(q, "request"):
            return f"{summary.get('service_requests_total', 0)} service request(s) in total."
        return (
            f"{summary['total_projects']} projects in total: {summary['in_progress']} in progress, "
            f"{summary['completed']} completed, {summary['overdue']} overdue."
        )

    # ---- completed --------------------------------------------------------
    if _any(q, "complete", "completed", "finished", "done", "delivered", "closed"):
        res = tools.list_projects(db, user, only_completed=True, limit=50)
        rows = [_project_line(p, internal=internal) for p in res["projects"]]
        return (f"{len(rows)} completed project(s):\n" + _bullets(rows, "")) if rows else "No projects are completed yet."

    # ---- filtered by vertical --------------------------------------------
    if named_vertical:
        res = tools.list_projects(db, user, vertical=named_vertical, limit=50)
        rows = [_project_line(p, internal=internal) for p in res["projects"]]
        return f"{named_vertical}: {len(rows)} project(s):\n" + _bullets(rows, "Nothing yet.")

    # ---- "the queue" = the queue-like status, when the team has one -------
    if _any(q, "queue", "queued", "backlog", "waiting to start", "not started"):
        queue_status = next((st.name for st in statuses if "queue" in st.name.lower()), None)
        if queue_status and not named_status:
            named_status = queue_status

    # ---- filtered by an explicit status ----------------------------------
    if named_status:
        res = tools.list_projects(db, user, status=named_status, limit=50)
        rows = [_project_line(p, internal=internal) for p in res["projects"]]
        return f"{named_status}: {len(rows)} project(s):\n" + _bullets(rows, "None.")

    # ---- running / queue / everything ------------------------------------
    if _any(q, "going on", "ongoing", "in progress", "running", "working on", "current",
            "active", "queue", "pipeline", "what are you doing", "status", "projects", "list"):
        res = tools.list_projects(db, user, only_completed=False, limit=50)
        rows = [_project_line(p, internal=internal) for p in res["projects"]]
        if not rows:
            return "There are no projects in progress right now."
        return (
            f"{len(rows)} project(s) in progress "
            f"(of {summary['total_projects']} total, {summary['completed']} completed):\n"
            + _bullets(rows, "")
        )

    return None


def cannot_answer_message(db: Session, user: User) -> str:
    internal = user.role in INTERNAL
    extra = "\n• What's blocked" if internal else ""
    return (
        "I couldn't match that to something I can look up. I'm running without a language model "
        "at the moment, so I answer a fixed set of questions directly from the tracker:\n"
        "• What's going on / in progress\n"
        "• What's completed\n"
        "• What's overdue\n"
        "• What a vertical is working on\n"
        "• Details of a project by name\n"
        "• Service requests" + extra +
        "\n\nTry rephrasing, or ask an admin to connect a language model in Admin > Settings."
    )
