"""Seed the throwaway end-to-end database.

Never point this at a real database. It writes fixed accounts with known
passwords so the API and browser suites can sign in as each role, and it
mirrors the reporting chain Naman actually runs: two AI-team accounts under
one head whose own manager has no login.

Run from backend/ with the e2e environment loaded:
    python /root/e2e/seed_e2e.py
"""
import os
import sys
from datetime import date, timedelta

# Find the backend package whether this sits next to it in the repo
# (<repo>/e2e + <repo>/backend) or in the split checkout used on the build box.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _candidate in (
    os.path.join(_HERE, "..", "backend"),
    os.path.join(_HERE, "..", "be", "backend"),
    os.getcwd(),
):
    if os.path.isdir(os.path.join(_candidate, "app")):
        sys.path.insert(0, os.path.abspath(_candidate))
        break
else:
    raise SystemExit("Could not find the backend/ folder next to this script.")

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.vertical import Vertical  # noqa: E402
from app.models.status import Status  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.update import Update  # noqa: E402
from app.models.branding import BrandingAsset  # noqa: E402
from app.core.default_logo import (  # noqa: E402
    DEFAULT_LOGO_SVG, DEFAULT_LOGO_FILENAME, DEFAULT_LOGO_CONTENT_TYPE,
)

PW = {
    "naman@aikyame2e.com": "NamanPass123",
    "aiteam@aikyame2e.com": "AiteamPass123",
    "pranjal@aikyame2e.com": "PranjalPass123",
    "ravi@aikyame2e.com": "RaviPass123",
    "meera@aikyame2e.com": "MeeraPass123",
    # Used only by the lockout test, so locking it cannot break another test.
    "lockme@aikyame2e.com": "LockmePass123",
}

VERTICALS = [
    ("Broking & Clearing", "Head of Broking", "broking.head@aikyame2e.com"),
    ("Accounts", "Head of Accounts", "accounts.head@aikyame2e.com"),
    ("Stressed Asset Management", "Head of SAM", "sam.head@aikyame2e.com"),
    ("Asset Management", "Head of AM", "am.head@aikyame2e.com"),
    ("Automation", "Head of Automation", "automation.head@aikyame2e.com"),
]

STATUSES = [
    ("In queue", "#94a3b8", False, 1),
    ("WIP", "#3b82f6", False, 2),
    ("UAT", "#f59e0b", False, 3),
    ("Live", "#22c55e", True, 4),
]


def main() -> None:
    db = SessionLocal()
    today = date.today()

    verticals = {}
    for name, head_name, head_email in VERTICALS:
        row = db.query(Vertical).filter(Vertical.name == name).first()
        if not row:
            row = Vertical(name=name, head_name=head_name, head_email=head_email, is_active=True)
            db.add(row)
            db.flush()
        verticals[name] = row

    statuses = {}
    for name, colour, is_done, order in STATUSES:
        row = db.query(Status).filter(Status.name == name).first()
        if not row:
            row = Status(name=name, color=colour, is_terminal=is_done, sort_order=order, is_active=True)
            db.add(row)
            db.flush()
        statuses[name] = row

    def user(email, name, role, reports_to=None, vertical=None, external=None):
        row = db.query(User).filter(User.email == email).first()
        if row:
            return row
        row = User(
            name=name, email=email, password_hash=hash_password(PW[email]), role=role,
            reports_to_id=reports_to.id if reports_to else None,
            vertical_id=verticals[vertical].id if vertical else None,
            external_manager_email=external, is_active=True,
        )
        db.add(row)
        db.flush()
        return row

    naman = user("naman@aikyame2e.com", "Naman Jain", "admin", external="management@aikyame2e.com")
    aiteam = user("aiteam@aikyame2e.com", "AI Team", "admin", reports_to=naman)
    pranjal = user("pranjal@aikyame2e.com", "Pranjal Shukla", "member", reports_to=naman)
    ravi = user("ravi@aikyame2e.com", "Ravi Menon", "requestor", vertical="Automation")
    user("meera@aikyame2e.com", "Meera Iyer", "requestor", vertical="Accounts")
    user("lockme@aikyame2e.com", "Lockout Target", "requestor", vertical="Accounts")

    def project(name, vertical, status, owners, remarks, assigned_by, target, done=None, desc=None):
        row = db.query(Project).filter(Project.name == name).first()
        if row:
            return row
        row = Project(
            name=name, description=desc, vertical_id=verticals[vertical].id,
            status_id=statuses[status].id, created_by_id=naman.id,
            assigned_by=assigned_by, assigned_on=today - timedelta(days=45),
            remarks=remarks, target_date=target, actual_completion_date=done,
        )
        row.owners = owners
        db.add(row)
        db.flush()
        return row

    compliance = project(
        "Compliance Tracker", "Broking & Clearing", "WIP", [pranjal],
        "Internal: waiting on the NSE circular before the next build",
        "Vishal", today - timedelta(days=7),
        desc="Tracks NSE/BSE/MSE filing obligations and their due dates.",
    )
    project(
        "FD Treasury Automation", "Accounts", "UAT", [pranjal, aiteam],
        "Internal: UAT running with the accounts team, two defects open",
        "Ranjan", today + timedelta(days=21),
        desc="Automates fixed deposit rollovers and treasury reporting.",
    )
    project(
        "Reconciliation Engine", "Broking & Clearing", "Live", [pranjal],
        "Internal: shipped, monitoring for a month",
        "Venky", today - timedelta(days=30), done=today - timedelta(days=25),
        desc="Daily F&O and MCX reconciliation across member files.",
    )
    project(
        "Bond Deal Portal", "Asset Management", "In queue", [],
        "Internal: requirements still being gathered with the RMs",
        "Manoj", today + timedelta(days=60),
        desc="Centralises block deals currently shared over WhatsApp.",
    )

    if not db.query(Update).filter(Update.project_id == compliance.id).first():
        db.add(Update(
            project_id=compliance.id, author_id=pranjal.id,
            plan="Finish the due-date engine",
            progress="Parser done, calendar rules half written",
            problem="Waiting on the circular",
        ))

    if not db.query(BrandingAsset).first():
        db.add(BrandingAsset(
            kind="logo", filename=DEFAULT_LOGO_FILENAME,
            content_type=DEFAULT_LOGO_CONTENT_TYPE,
            size_bytes=len(DEFAULT_LOGO_SVG), data=DEFAULT_LOGO_SVG,
        ))

    db.commit()
    print("seeded:", db.query(User).count(), "users,", db.query(Project).count(), "projects")
    db.close()


if __name__ == "__main__":
    main()
