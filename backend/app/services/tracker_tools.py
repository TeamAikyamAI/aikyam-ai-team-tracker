"""Deterministic, read-only queries the assistant can call.

Two problems this solves.

1. Counting. Previously the whole project list was pushed into the prompt and
   the model counted for itself. Counting from a JSON blob is exactly what
   small models get wrong, and it is wasted work even for a large one. Every
   figure here is computed by the database or by Python - never by the model.

2. Scope. Previously role scoping lived in how the context was assembled, which
   means it lived in the prompt. Here it is enforced inside each function: a
   requestor's call returns requestor-visible rows no matter what the model
   asks for, because the filter is in the query, not in an instruction the
   model could be talked out of.

Nothing here writes. There is no tool that can change the tracker.
"""
from datetime import date, datetime, timedelta
from typing import Any, Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.project import Project, project_owners
from app.models.status import Status
from app.models.vertical import Vertical
from app.models.update import Update
from app.models.service_request import ServiceRequest

# Roles that may see internal detail: update logs, owners, blockers, requests
# from other people, the team list.
INTERNAL_ROLES = ("admin", "member")

MAX_ROWS = 100


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _status_lookup(db: Session) -> dict[int, Status]:
    return {s.id: s for s in db.query(Status).all()}


def _vertical_lookup(db: Session) -> dict[int, Vertical]:
    return {v.id: v for v in db.query(Vertical).all()}


def _is_internal(user: User) -> bool:
    return user.role in INTERNAL_ROLES


def _project_row(p: Project, statuses, verticals, *, internal: bool) -> dict:
    status = statuses.get(p.status_id)
    row = {
        "project": p.name,
        "vertical": verticals[p.vertical_id].name if p.vertical_id in verticals else None,
        "status": status.name if status else "Unknown",
        "is_completed": bool(status and status.is_terminal),
    }
    # Open to everyone, and deliberately so: the dashboard already shows all of
    # this to every logged-in person, so the assistant matches it rather than
    # being quietly stricter than the screen next to it.
    row["owners"] = [o.name for o in p.owners]
    row["target_date"] = p.target_date.isoformat() if p.target_date else None
    row["completed_on"] = p.actual_completion_date.isoformat() if p.actual_completion_date else None
    row["description"] = p.description
    row["assigned_by"] = p.assigned_by
    row["assigned_on"] = p.assigned_on.isoformat() if p.assigned_on else None

    # Team-only. Remarks is where internal notes about a request or a vertical
    # end up, so it is the one project field that does not cross verticals.
    if internal:
        row["remarks"] = p.remarks
        row["from_service_request"] = p.source_request_id is not None
    return row


# --------------------------------------------------------------------------
# the tools
# --------------------------------------------------------------------------

def get_summary(db: Session, user: User) -> dict:
    """Every headline figure, counted in the database rather than by the model."""
    statuses = _status_lookup(db)
    verticals = _vertical_lookup(db)
    projects = db.query(Project).all()

    def done(p: Project) -> bool:
        s = statuses.get(p.status_id)
        return bool(s and s.is_terminal)

    today = date.today()
    month_start = today.replace(day=1)

    by_status: dict[str, int] = {}
    by_vertical: dict[str, int] = {}
    overdue = 0
    for p in projects:
        s = statuses.get(p.status_id)
        by_status[s.name if s else "Unknown"] = by_status.get(s.name if s else "Unknown", 0) + 1
        vname = verticals[p.vertical_id].name if p.vertical_id in verticals else "Unassigned"
        by_vertical[vname] = by_vertical.get(vname, 0) + 1
        if p.target_date and p.target_date < today and not done(p):
            overdue += 1

    summary: dict[str, Any] = {
        "today": today.isoformat(),
        "total_projects": len(projects),
        "in_progress": sum(1 for p in projects if not done(p)),
        "completed": sum(1 for p in projects if done(p)),
        "completed_this_month": sum(
            1 for p in projects
            if p.actual_completion_date and p.actual_completion_date >= month_start
        ),
        "overdue": overdue,
        "projects_by_status": by_status,
        "projects_by_vertical": by_vertical,
        "active_verticals": [v.name for v in verticals.values() if v.is_active],
        "statuses_that_count_as_finished": [s.name for s in statuses.values() if s.is_terminal],
    }

    if _is_internal(user):
        reqs = db.query(ServiceRequest).all()
        by_req_status: dict[str, int] = {}
        for r in reqs:
            by_req_status[r.status] = by_req_status.get(r.status, 0) + 1
        summary["service_requests_total"] = len(reqs)
        summary["service_requests_by_status"] = by_req_status
        summary["service_requests_awaiting_review"] = sum(
            1 for r in reqs if r.status in ("submitted", "under_review")
        )
        summary["team_size"] = db.query(User).filter(
            User.role.in_(INTERNAL_ROLES), User.is_active == True  # noqa: E712
        ).count()
    else:
        own = db.query(ServiceRequest).filter(ServiceRequest.requestor_id == user.id).all()
        summary["my_service_requests_total"] = len(own)
        summary["my_service_requests_by_status"] = {
            r.status: sum(1 for x in own if x.status == r.status) for r in own
        }
    return summary


def list_projects(
    db: Session,
    user: User,
    status: str | None = None,
    vertical: str | None = None,
    owner: str | None = None,
    only_completed: bool | None = None,
    only_overdue: bool | None = None,
    limit: int = 50,
) -> dict:
    """Projects, optionally filtered. Requestors get the queue-level view only."""
    statuses = _status_lookup(db)
    verticals = _vertical_lookup(db)
    internal = _is_internal(user)

    q = db.query(Project)
    if status:
        match = [s.id for s in statuses.values() if s.name.lower() == status.lower()]
        if not match:
            return {"error": f"No status called '{status}'. Available: "
                             f"{', '.join(sorted(s.name for s in statuses.values()))}"}
        q = q.filter(Project.status_id.in_(match))
    if vertical:
        match = [v.id for v in verticals.values() if v.name.lower() == vertical.lower()]
        if not match:
            return {"error": f"No vertical called '{vertical}'. Available: "
                             f"{', '.join(sorted(v.name for v in verticals.values()))}"}
        q = q.filter(Project.vertical_id.in_(match))
    if owner:
        if not internal:
            return {"error": "Owner information isn't available at your access level."}
        owner_ids = [u.id for u in db.query(User).filter(User.name.ilike(f"%{owner}%")).all()]
        if not owner_ids:
            return {"error": f"No team member matching '{owner}'."}
        proj_ids = {
            r[0] for r in db.query(project_owners.c.project_id)
            .filter(project_owners.c.user_id.in_(owner_ids)).all()
        }
        q = q.filter(Project.id.in_(proj_ids or {-1}))

    projects = q.limit(min(limit, MAX_ROWS)).all()

    terminal_ids = {s.id for s in statuses.values() if s.is_terminal}
    if only_completed is True:
        projects = [p for p in projects if p.status_id in terminal_ids]
    elif only_completed is False:
        projects = [p for p in projects if p.status_id not in terminal_ids]
    if only_overdue:
        today = date.today()
        projects = [
            p for p in projects
            if p.target_date and p.target_date < today and p.status_id not in terminal_ids
        ]

    return {
        "count": len(projects),
        "projects": [_project_row(p, statuses, verticals, internal=internal) for p in projects],
    }


def get_project(db: Session, user: User, name: str) -> dict:
    """One project by name, with its recent update log for the AI team."""
    statuses = _status_lookup(db)
    verticals = _vertical_lookup(db)
    internal = _is_internal(user)

    p = db.query(Project).filter(Project.name.ilike(f"%{name}%")).first()
    if not p:
        return {"error": f"No project matching '{name}'."}

    row = _project_row(p, statuses, verticals, internal=internal)
    if internal:
        updates = (
            db.query(Update).filter(Update.project_id == p.id)
            .order_by(Update.created_at.desc()).limit(10).all()
        )
        authors = {u.id: u.name for u in db.query(User).all()}
        row["recent_updates"] = [
            {
                "date": u.created_at.date().isoformat() if u.created_at else None,
                "by": authors.get(u.author_id),
                "plan": u.plan,
                "progress": u.progress,
                "problem": u.problem,
            }
            for u in updates
        ]
    return row


def list_service_requests(db: Session, user: User, status: str | None = None, limit: int = 50) -> dict:
    """Intake requests. A requestor only ever sees their own."""
    verticals = _vertical_lookup(db)
    q = db.query(ServiceRequest)
    if not _is_internal(user):
        q = q.filter(ServiceRequest.requestor_id == user.id)
    if status:
        q = q.filter(ServiceRequest.status == status.lower().replace(" ", "_"))

    rows = q.order_by(ServiceRequest.created_at.desc()).limit(min(limit, MAX_ROWS)).all()
    requestors = {u.id: u.name for u in db.query(User).all()}
    return {
        "count": len(rows),
        "requests": [
            {
                "title": r.title,
                "vertical": verticals[r.vertical_id].name if r.vertical_id in verticals else None,
                "status": r.status,
                "submitted": r.created_at.date().isoformat() if r.created_at else None,
                "requested_by": requestors.get(r.requestor_id) if _is_internal(user) else "you",
                "description": r.description,
            }
            for r in rows
        ],
    }


def search_updates(db: Session, user: User, keyword: str | None = None, days: int = 30, limit: int = 40) -> dict:
    """Search the Plan/Progress/Problem log. Internal only - this is where blockers live."""
    if not _is_internal(user):
        return {"error": "Update logs aren't available at your access level."}

    since = datetime.utcnow() - timedelta(days=max(1, min(days, 365)))
    q = db.query(Update).filter(Update.created_at >= since)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(Update.plan.ilike(like), Update.progress.ilike(like), Update.problem.ilike(like)))

    rows = q.order_by(Update.created_at.desc()).limit(min(limit, MAX_ROWS)).all()
    names = {p.id: p.name for p in db.query(Project).all()}
    authors = {u.id: u.name for u in db.query(User).all()}
    return {
        "count": len(rows),
        "window_days": days,
        "updates": [
            {
                "project": names.get(u.project_id),
                "date": u.created_at.date().isoformat() if u.created_at else None,
                "by": authors.get(u.author_id),
                "plan": u.plan,
                "progress": u.progress,
                "problem": u.problem,
            }
            for u in rows
        ],
    }


def get_team(db: Session, user: User) -> dict:
    """Who is on the AI team and who reports to whom. Internal only."""
    if not _is_internal(user):
        return {"error": "Team details aren't available at your access level."}
    users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    by_id = {u.id: u.name for u in users}
    return {
        "count": len(users),
        "people": [
            {
                "name": u.name,
                "role": u.role,
                "reports_to": by_id.get(u.reports_to_id) if u.reports_to_id else None,
            }
            for u in users
        ],
    }


def get_verticals(db: Session, user: User) -> dict:
    """The business verticals and their heads."""
    rows = db.query(Vertical).filter(Vertical.is_active == True).all()  # noqa: E712
    return {
        "count": len(rows),
        "verticals": [{"name": v.name, "head": v.head_name} for v in rows],
    }


# --------------------------------------------------------------------------
# registry - the schemas handed to the model
# --------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "list_projects",
        "description": (
            "List projects, optionally filtered by status, vertical, owner, whether they are "
            "completed, or whether they are overdue. Use this for 'which projects are...' "
            "questions. For plain totals prefer the summary already provided."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Status name, e.g. Ongoing, Completed"},
                "vertical": {"type": "string", "description": "Business vertical name"},
                "owner": {"type": "string", "description": "Team member name (partial match)"},
                "only_completed": {"type": "boolean", "description": "true = finished only, false = unfinished only"},
                "only_overdue": {"type": "boolean", "description": "Past target date and not finished"},
                "limit": {"type": "integer", "description": "Max rows, default 50"},
            },
        },
        "fn": list_projects,
    },
    {
        "name": "get_project",
        "description": "Full detail for one project by name, including its recent Plan/Progress/Problem updates.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Project name or part of it"}},
            "required": ["name"],
        },
        "fn": get_project,
    },
    {
        "name": "list_service_requests",
        "description": (
            "Intake requests from business verticals. Optionally filter by status: submitted, "
            "under_review, approved, rejected, on_hold."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
        "fn": list_service_requests,
    },
    {
        "name": "search_updates",
        "description": (
            "Search the Plan/Progress/Problem update log by keyword and time window. Use this for "
            "'what is blocked', 'what happened recently', or anything about progress narrative."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "days": {"type": "integer", "description": "How far back to look, default 30"},
                "limit": {"type": "integer"},
            },
        },
        "fn": search_updates,
    },
    {
        "name": "get_team",
        "description": "The AI team members, their roles, and the reporting chain.",
        "input_schema": {"type": "object", "properties": {}},
        "fn": get_team,
    },
    {
        "name": "get_verticals",
        "description": "The business verticals and the head of each.",
        "input_schema": {"type": "object", "properties": {}},
        "fn": get_verticals,
    },
]

BY_NAME: dict[str, Callable] = {t["name"]: t["fn"] for t in TOOLS}


def schemas() -> list[dict]:
    """Tool definitions without the Python callables, for sending to the model."""
    return [{k: v for k, v in t.items() if k != "fn"} for t in TOOLS]


def run(db: Session, user: User, name: str, arguments: dict) -> dict:
    fn = BY_NAME.get(name)
    if fn is None:
        return {"error": f"Unknown tool '{name}'."}
    try:
        return fn(db, user, **(arguments or {}))
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}
