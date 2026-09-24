"""Compiles and sends the weekly reporting chain:
 - every member's own updates -> emailed to their direct manager
 - every manager's own + their FULL reporting subtree's updates -> emailed
   up to THEIR manager (or external_manager_email if they're the top of the
   chain inside this system, e.g. Naman -> Aikyam management)
Entirely driven by the `reports_to` graph on User - no hardcoded names.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.update import Update
from app.models.project import Project, project_owners
from app.models.vertical import Vertical
from app.models.status import Status
from app.services.email import send_email
from app.services import settings as cfg
from app.services import api_keys as keys
from app.services import daily

_env = Environment(loader=FileSystemLoader("app/templates"))


def _week_window(db: Session):
    """Last seven days, expressed in the admin-configured digest timezone so the
    dates in subjects and templates match what the team sees on their calendar."""
    try:
        tz = ZoneInfo(cfg.get(db, "digest_timezone") or "UTC")
    except Exception:
        tz = timezone.utc
    end = datetime.now(tz)
    start = end - timedelta(days=7)
    return start, end


def _entries_for_user(db: Session, user: User, start, end) -> list[dict]:
    rows = (
        db.query(Update, Project, Vertical, Status)
        .join(Project, Update.project_id == Project.id)
        .join(Vertical, Project.vertical_id == Vertical.id)
        .join(Status, Project.status_id == Status.id)
        .filter(
            Update.author_id == user.id,
            # Compare in UTC: Postgres stores timestamptz, SQLite (tests) drops
            # the offset - UTC keeps both consistent with func.now().
            Update.created_at >= start.astimezone(timezone.utc),
            Update.created_at <= end.astimezone(timezone.utc),
        )
        .order_by(Update.created_at.desc())
        .all()
    )
    return [
        {
            "project_name": p.name,
            "vertical_name": v.name,
            "status_name": s.name,
            "plan": u.plan,
            "progress": u.progress,
            "problem": u.problem,
        }
        for u, p, v, s in rows
    ]


def _all_reports_recursive(db: Session, manager: User) -> list[User]:
    result: list[User] = []
    frontier = list(db.query(User).filter(User.reports_to_id == manager.id, User.is_active == True).all())  # noqa: E712
    seen = set()
    while frontier:
        person = frontier.pop()
        if person.id in seen:
            continue
        seen.add(person.id)
        result.append(person)
        frontier.extend(db.query(User).filter(User.reports_to_id == person.id, User.is_active == True).all())  # noqa: E712
    return result


def send_weekly_digests(db: Session, preview_to: str | None = None) -> int:
    """Compile and send this week's digests.

    `preview_to` redirects every message to one address and marks the subject,
    so an admin can see exactly what Monday will produce - the same data, the
    same templates, the same reporting chain - without a half-finished digest
    landing with their manager. Returns how many emails were sent.
    """
    start, end = _week_window(db)
    app_name = cfg.get(db, "app_name")
    signature = cfg.get(db, "email_signature")
    sent = 0

    def deliver(to: list[str], subject: str, html: str, reply_to: str, from_name: str):
        nonlocal sent
        if preview_to:
            to = [preview_to]
            subject = f"[Preview] {subject}"
        # Count what actually went out, not what was attempted, and keep going
        # when one address fails - otherwise a single bad mailbox means nobody
        # further down the list gets their digest either.
        if send_email(db, to=to, subject=subject, html_body=html,
                      reply_to=reply_to, from_display_name=from_name):
            sent += 1
    people = db.query(User).filter(User.role.in_(["admin", "member"]), User.is_active == True).all()  # noqa: E712

    # 1) individual -> direct manager
    tpl = _env.get_template("weekly_digest.html")
    for person in people:
        if not person.reports_to:
            continue
        entries = _entries_for_user(db, person, start, end)
        html = tpl.render(person_name=person.name, week_start=start.date(), week_end=end.date(), entries=entries, app_name=app_name, signature=signature)
        deliver(
            [person.reports_to.email],
            f"Weekly update - {person.name} - {start.date()} to {end.date()}",
            html, person.email, person.name,
        )

    # 2) manager rollup -> their own manager / external_manager_email
    #
    # The rollup is also where API keys about to lapse are raised: it is the
    # one message that reaches the person who can get a renewal approved, and a
    # key that dies quietly takes a running automation down with it.
    expiring = keys.digest_lines(db, daily.today_for(db))
    rollup_tpl = _env.get_template("team_rollup.html")
    managers = [p for p in people if p.direct_reports]
    for manager in managers:
        subtree = _all_reports_recursive(db, manager)
        by_person: dict[str, list[dict]] = {manager.name: _entries_for_user(db, manager, start, end)}
        for person in subtree:
            by_person[person.name] = _entries_for_user(db, person, start, end)

        recipient = manager.reports_to.email if manager.reports_to else manager.external_manager_email
        if not recipient:
            continue
        html = rollup_tpl.render(manager_name=manager.name, week_start=start.date(), week_end=end.date(),
                                 by_person=by_person, app_name=app_name, signature=signature,
                                 expiring_keys=expiring, expiry_window=keys.EXPIRY_WINDOW_DAYS)
        deliver(
            [recipient],
            f"{app_name} - weekly rollup - {start.date()} to {end.date()}",
            html, manager.email, manager.name,
        )

    return sent
