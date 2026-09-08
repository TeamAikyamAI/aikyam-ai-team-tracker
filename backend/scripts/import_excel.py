"""Import the team's Weekly_Update.xlsx into the tracker.

    cd backend
    python scripts/import_excel.py "C:/path/Weekly_Update.xlsx"            # do it
    python scripts/import_excel.py "C:/path/Weekly_Update.xlsx" --dry-run  # show what would happen

Workbook layout expected (one sheet per pipeline stage, first row = header):
    Project Name | Project Description | Assigned by | Date of assignment |
    Status | Date of completion | Remarks

What it does, idempotently (safe to run twice):
  * creates a status per sheet name if missing (the last sheet is treated as
    the terminal "done" stage), and deactivates the seed placeholders
    (Ongoing / Blocked / On Hold / Completed) when no project uses them
  * creates the "--vertical" (default: Unassigned) if missing, so every row
    lands somewhere and can be re-homed from Admin > Verticals later
  * skips rows whose project name already exists (case-insensitive) and
    duplicate names inside the workbook itself
  * keeps the sheet name as the project's status; when a row's own Status
    cell says something more specific (e.g. "confirmation awaiting from the
    team") that text is preserved in Remarks instead of being lost
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

from openpyxl import load_workbook  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
import app.models  # noqa: E402,F401
from app.models.project import Project  # noqa: E402
from app.models.status import Status  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.vertical import Vertical  # noqa: E402
from app.services.audit import log_action  # noqa: E402
from sqlalchemy import func  # noqa: E402

HEADER_ALIASES = {
    "project name": "name",
    "project description": "description",
    "assigned by": "assigned_by",
    "date of assignment": "assigned_on",
    "status": "status_note",
    "date of completion": "actual_completion_date",
    "remarks": "remarks",
}

# Row-level status spellings that mean "same as the sheet", so they are not
# copied into remarks as noise.
STATUS_SYNONYMS = {
    "wip": {"wip", "in progress", "in-progress", "in-progess", "inprogress", "ongoing"},
    "uat": {"uat", "in uat", "in-uat", "testing"},
    "live": {"live", "completed", "done", "in production"},
    "in queue": {"in queue", "queue", "queued", "pending", "backlog"},
}

# Colours for stages created from sheet names; anything else gets grey.
STAGE_COLOURS = {
    "in queue": "#94a3b8",
    "wip": "#3b82f6",
    "uat": "#f59e0b",
    "live": "#22c55e",
}

PLACEHOLDER_STATUSES = ("Ongoing", "Blocked", "On Hold", "Completed")


def _norm(value) -> str:
    return " ".join(str(value or "").split()).strip().lower()


def _as_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    print(f"    ! could not parse date {value!r}; leaving blank")
    return None


def _clean(value) -> str | None:
    text = " ".join(str(value).split()).strip() if value is not None else ""
    return text or None


def read_rows(path: Path) -> list[dict]:
    wb = load_workbook(path, data_only=True)
    rows: list[dict] = []
    for order, ws in enumerate(wb.worksheets):
        header = [(_norm(c)) for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
        mapping = {i: HEADER_ALIASES[h] for i, h in enumerate(header) if h in HEADER_ALIASES}
        if "name" not in mapping.values():
            print(f"  sheet {ws.title!r}: no 'Project Name' column, skipped")
            continue
        for raw in ws.iter_rows(min_row=2, values_only=True):
            record = {field: raw[i] if i < len(raw) else None for i, field in mapping.items()}
            name = _clean(record.get("name"))
            if not name:
                continue
            rows.append({
                "sheet": ws.title.strip(),
                "sheet_order": order,
                "name": name,
                "description": _clean(record.get("description")),
                "assigned_by": _clean(record.get("assigned_by")),
                "assigned_on": _as_date(record.get("assigned_on")),
                "status_note": _clean(record.get("status_note")),
                "actual_completion_date": _as_date(record.get("actual_completion_date")),
                "remarks": _clean(record.get("remarks")),
            })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workbook", help="Path to Weekly_Update.xlsx")
    ap.add_argument("--vertical", default="Unassigned", help="Vertical to file imported projects under (created if missing)")
    ap.add_argument("--created-by", default=None, help="E-mail of the tracker user to record as creator (default: first active admin)")
    ap.add_argument("--keep-placeholders", action="store_true", help="Do not deactivate the seed statuses Ongoing/Blocked/On Hold/Completed")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan, change nothing")
    args = ap.parse_args()

    path = Path(args.workbook).expanduser()
    if not path.is_file():
        print(f"Workbook not found: {path}")
        return 2

    rows = read_rows(path)
    print(f"Read {len(rows)} row(s) from {path.name} across {len({r['sheet'] for r in rows})} sheet(s)")

    db = SessionLocal()
    try:
        creator = None
        if args.created_by:
            creator = db.query(User).filter(func.lower(User.email) == args.created_by.lower()).first()
            if not creator:
                print(f"No user with e-mail {args.created_by}")
                return 2
        else:
            creator = db.query(User).filter(User.role == "admin", User.is_active == True).order_by(User.id).first()  # noqa: E712
        if not creator:
            print("No active admin found - run scripts/seed.py first")
            return 2
        print(f"Recording {creator.name} <{creator.email}> as creator")

        # --- vertical -------------------------------------------------------
        vertical = db.query(Vertical).filter(func.lower(Vertical.name) == args.vertical.lower()).first()
        if not vertical:
            print(f"Vertical {args.vertical!r}: will create (head = {creator.name})")
            vertical = Vertical(name=args.vertical, head_name=creator.name, head_email=creator.email, is_active=True)
            if not args.dry_run:
                db.add(vertical)
                db.flush()
        else:
            print(f"Vertical {vertical.name!r}: exists")

        # --- statuses from sheet names -------------------------------------
        sheets = sorted({(r["sheet_order"], r["sheet"]) for r in rows})
        status_by_sheet: dict[str, Status] = {}
        for idx, (_, sheet) in enumerate(sheets):
            st = db.query(Status).filter(func.lower(Status.name) == sheet.lower()).first()
            if st:
                if not st.is_active:
                    print(f"Status {sheet!r}: exists but inactive -> re-activating")
                    st.is_active = True
                else:
                    print(f"Status {sheet!r}: exists")
            else:
                terminal = idx == len(sheets) - 1
                print(f"Status {sheet!r}: will create (order {idx + 1}{', terminal' if terminal else ''})")
                st = Status(name=sheet, color=STAGE_COLOURS.get(sheet.lower(), "#6b7280"),
                            is_terminal=terminal, sort_order=idx + 1, is_active=True)
                if not args.dry_run:
                    db.add(st)
                    db.flush()
            status_by_sheet[sheet] = st

        if not args.keep_placeholders:
            for name in PLACEHOLDER_STATUSES:
                st = db.query(Status).filter(Status.name == name, Status.is_active == True).first()  # noqa: E712
                if not st or name.lower() in {s.lower() for _, s in sheets}:
                    continue
                in_use = db.query(Project.id).filter(Project.status_id == st.id).first() is not None
                if in_use:
                    print(f"Placeholder status {name!r}: in use, left active")
                else:
                    print(f"Placeholder status {name!r}: unused -> deactivating (re-enable any time in Admin > Statuses)")
                    if not args.dry_run:
                        st.is_active = False

        # --- projects ---------------------------------------------------------
        existing = {n.lower() for (n,) in db.query(Project.name).all()}
        seen_in_file: set[str] = set()
        created = skipped = 0
        for r in rows:
            key = r["name"].lower()
            if key in existing:
                print(f"  - {r['name']!r}: already in tracker, skipped")
                skipped += 1
                continue
            if key in seen_in_file:
                print(f"  - {r['name']!r}: duplicate row in workbook, skipped")
                skipped += 1
                continue
            seen_in_file.add(key)

            remarks = r["remarks"]
            note = _norm(r["status_note"])
            sheet_key = r["sheet"].lower()
            if note and note != sheet_key and note not in STATUS_SYNONYMS.get(sheet_key, set()):
                line = f"Status note from import: {r['status_note']}"
                remarks = f"{remarks}\n{line}" if remarks else line

            st = status_by_sheet[r["sheet"]]
            completion = r["actual_completion_date"]
            print(f"  + {r['name']!r} -> {st.name}"
                  + (f", assigned by {r['assigned_by']}" if r["assigned_by"] else "")
                  + (f" on {r['assigned_on']}" if r["assigned_on"] else "")
                  + (f", completed {completion}" if completion else "")
                  + (f", remarks: {remarks!r}" if remarks else ""))
            if not args.dry_run:
                project = Project(
                    name=r["name"],
                    description=r["description"],
                    vertical_id=vertical.id,
                    status_id=st.id,
                    created_by_id=creator.id,
                    assigned_by=r["assigned_by"],
                    assigned_on=r["assigned_on"],
                    remarks=remarks,
                    actual_completion_date=completion,
                )
                project.owners = []
                db.add(project)
            created += 1

        if args.dry_run:
            db.rollback()
            print(f"\nDry run: {created} project(s) would be created, {skipped} skipped. Nothing changed.")
        else:
            db.commit()
            log_action(db, creator.id, "import_excel", details=f"{path.name}: {created} created, {skipped} skipped")
            print(f"\nDone: {created} project(s) created, {skipped} skipped."
                  f"\nNext: open the dashboard, set owners on each project, and move any project"
                  f" from '{vertical.name}' to its real vertical (Edit project > Vertical).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
