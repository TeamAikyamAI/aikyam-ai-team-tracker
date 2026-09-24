import importlib.util
import io
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone

import pytest
from openpyxl import Workbook, load_workbook
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
SAMPLE = BACKEND_DIR / "data" / "Weekly_Update.xlsx"

LEADING = ["Project Name", "Assigned by", "Date of assignment", "Status"]
TRAILING = ["Date of completion", "Remarks"]


def _export(client, auth):
    r = client.get("/projects/export.xlsx", headers=auth("member"))
    assert r.status_code == 200, r.text
    return load_workbook(io.BytesIO(r.content))


def _header(ws) -> list[str]:
    return [c.value for c in ws[1]]


def _day(value):
    """openpyxl hands back a datetime for a date cell; compare as dates."""
    return value.date() if isinstance(value, datetime) else value


def _row_for(ws, name: str) -> dict:
    header = _header(ws)
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] == name:
            return dict(zip(header, row))
    raise AssertionError(f"{name!r} is not in the export")


def _importer():
    """The import script, loaded in-process so it uses the test database."""
    spec = importlib.util.spec_from_file_location(
        "import_excel_under_test", BACKEND_DIR / "scripts" / "import_excel.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _log_update(db, seed, project_id: int, when: date, **fields):
    """An update stamped as if it had been written on ``when``."""
    from app.models.update import Update
    from app.services import daily

    db.add(Update(
        project_id=project_id,
        author_id=seed["admin"],
        created_at=datetime.combine(when, time(12, 0), tzinfo=daily.tzinfo_for(db)).astimezone(timezone.utc),
        **fields,
    ))
    db.commit()


def test_project_names_unique_case_insensitive(client, seed, auth):
    body = {"name": "Unique Name Project", "vertical_id": seed["vertical"], "status_id": seed["status_queue"]}
    assert client.post("/projects", headers=auth("admin"), json=body).status_code == 201
    r = client.post("/projects", headers=auth("admin"), json={**body, "name": "  unique name PROJECT "})
    assert r.status_code == 409
    other = client.post("/projects", headers=auth("admin"), json={**body, "name": "Rename target"}).json()
    assert client.patch(f"/projects/{other['id']}", headers=auth("admin"), json={"name": "UNIQUE NAME PROJECT"}).status_code == 409


def test_new_fields_round_trip_and_owner_ids_returned(client, seed, auth):
    body = {"name": "Fields project", "vertical_id": seed["vertical"], "status_id": seed["status_queue"],
            "assigned_by": "Vishal Trehan", "assigned_on": "2026-08-25", "remarks": "confirmation awaiting",
            "owner_ids": [seed["member"]]}
    r = client.post("/projects", headers=auth("admin"), json=body)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["assigned_by"] == "Vishal Trehan" and p["assigned_on"] == "2026-08-25" and p["remarks"] == "confirmation awaiting"
    assert p["owner_ids"] == [seed["member"]]
    got = client.get(f"/projects/{p['id']}", headers=auth("member")).json()
    assert got["owner_ids"] == [seed["member"]]

    # A requestor sees the project - owners, dates, the lot - but never the
    # internal Remarks field.
    seen = client.get(f"/projects/{p['id']}", headers=auth("req1"))
    assert seen.status_code == 200
    assert seen.json()["owner_ids"] == [seed["member"]]
    assert seen.json()["assigned_by"] == "Vishal Trehan"
    assert seen.json()["remarks"] is None


def test_moving_to_terminal_status_stamps_completion(client, seed, auth):
    """Whether a status counts as done is a property of the status, not a
    hardcoded name - so the same move stamps or does not stamp depending on it."""
    body = {"name": "Goes live", "vertical_id": seed["vertical"], "status_id": seed["status_queue"]}
    pid = client.post("/projects", headers=auth("admin"), json=body).json()["id"]
    r = client.patch(f"/projects/{pid}", headers=auth("admin"), json={"status_id": seed["status_live"]})
    assert r.json()["actual_completion_date"] is not None

    # Turn the flag off and the same move stops meaning "finished".
    client.patch(f"/statuses/{seed['status_live']}", headers=auth("admin"), json={"is_terminal": False})
    try:
        pid2 = client.post("/projects", headers=auth("admin"), json={**body, "name": "Goes live 2"}).json()["id"]
        r = client.patch(f"/projects/{pid2}", headers=auth("admin"), json={"status_id": seed["status_live"]})
        assert r.json()["actual_completion_date"] is None
    finally:
        client.patch(f"/statuses/{seed['status_live']}", headers=auth("admin"), json={"is_terminal": True})


# --------------------------------------------------------------------------
# Export: one sheet in the team's weekly format, with a column per calendar
# week. Nothing about a week is stored - the columns come from the calendar
# every time the file is built.
# --------------------------------------------------------------------------

def test_export_is_a_single_sheet_in_the_weekly_format(client, seed, auth, db):
    from app.services import daily, weeks as wk

    assert client.get("/projects/export.xlsx", headers=auth("req1")).status_code == 403
    r = client.get("/projects/export.xlsx", headers=auth("member"))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert ".xlsx" in r.headers["content-disposition"]

    wb = load_workbook(io.BytesIO(r.content))
    assert len(wb.worksheets) == 1, "the weekly format is one sheet, not one per status"
    ws = wb.worksheets[0]
    header = _header(ws)
    assert header[:4] == LEADING
    assert header[-2:] == TRAILING

    # The week columns are exactly the weeks the calendar says, in order.
    assert header[4:-2] == [wk.header_for(s) for s in wk.recent_weeks(db, daily.today_for(db))]

    # Every project is one row, and its status is a column now, not a sheet.
    row = _row_for(ws, "Fields project")
    assert row["Assigned by"] == "Vishal Trehan"
    assert _day(row["Date of assignment"]) == date(2026, 8, 25)
    assert row["Status"] == "In queue"
    assert row["Remarks"] == "confirmation awaiting"


def test_week_columns_are_the_calendar_and_the_settings_and_nothing_else(client, seed, auth, db):
    """Six weeks of Thursdays, because that is what the two settings say.

    The week's start day is the digest day: one definition of "a week" for the
    whole app, so the export can never disagree with the digest.
    """
    from app.services import daily, settings as cfg, weeks as wk

    cfg.set_many(db, {"export_weeks": 6, "digest_day_of_week": "thu"})
    try:
        header = _header(_export(client, auth).worksheets[0])
        starts = [wk.parse_header(h) for h in header[4:-2]]
        assert len(starts) == 6
        assert all(s.weekday() == 3 for s in starts), starts   # Thursday
        assert starts == sorted(starts)
        assert (starts[-1] - starts[0]).days == 35
        today = daily.today_for(db)
        assert starts[-1] <= today < starts[-1] + timedelta(days=7)
    finally:
        cfg.set_many(db, {"export_weeks": 4, "digest_day_of_week": "mon"})

    assert len(_header(_export(client, auth).worksheets[0])) == len(LEADING) + 4 + len(TRAILING)


def test_an_update_lands_in_the_column_for_its_own_week(client, seed, auth, db):
    from app.services import daily, weeks as wk

    pid = client.post("/projects", headers=auth("admin"), json={
        "name": "Weekly columns", "vertical_id": seed["vertical"], "status_id": seed["status_queue"],
    }).json()["id"]

    today = daily.today_for(db)
    this_week = wk.week_start_for(today, wk.start_dow(db))
    last_week = this_week - timedelta(weeks=1)
    _log_update(db, seed, pid, today, progress="Shipped the parser")
    _log_update(db, seed, pid, last_week + timedelta(days=1), plan="Draft it", problem="Waiting on data")

    row = _row_for(_export(client, auth).worksheets[0], "Weekly columns")
    assert row[wk.header_for(this_week)] == "Shipped the parser"
    assert row[wk.header_for(last_week)] == "Plan: Draft it\nProblem: Waiting on data"
    # A week nobody reported in stays empty rather than repeating the last one.
    assert row[wk.header_for(this_week - timedelta(weeks=2))] is None


# --------------------------------------------------------------------------
# Round trip: what the export writes, the importer reads back.
# --------------------------------------------------------------------------

def test_export_then_import_reads_every_field_back(client, seed, auth, db, tmp_path):
    """The whole point of sharing weeks.py and the cell format between the two
    sides: a workbook that goes out comes back in unchanged."""
    from app.services import daily, weeks as wk
    from app.services.excel import text_to_update

    pid = client.post("/projects", headers=auth("admin"), json={
        "name": "Round trip project", "vertical_id": seed["vertical"], "status_id": seed["status_queue"],
        "assigned_by": "Kunal Rathi", "assigned_on": "2026-09-01", "remarks": "signed off by ops",
    }).json()["id"]

    this_week = wk.week_start_for(daily.today_for(db), wk.start_dow(db))
    last_week = this_week - timedelta(weeks=1)
    _log_update(db, seed, pid, this_week, progress="Shipped the parser")
    _log_update(db, seed, pid, last_week, plan="Draft it", problem="Waiting on data")

    path = tmp_path / "Weekly_Update.xlsx"
    path.write_bytes(client.get("/projects/export.xlsx", headers=auth("member")).content)

    row = next(r for r in _importer().read_rows(path) if r["name"] == "Round trip project")
    assert row["assigned_by"] == "Kunal Rathi"
    assert row["assigned_on"] == date(2026, 9, 1)
    assert row["status_note"] == "In queue"
    assert row["actual_completion_date"] is None
    assert row["remarks"] == "signed off by ops"
    assert row["updates"] == [(last_week, "Plan: Draft it\nProblem: Waiting on data"),
                              (this_week, "Shipped the parser")]
    # ...and the cell text turns back into the same three fields.
    assert text_to_update(row["updates"][0][1]) == {"plan": "Draft it", "progress": None,
                                                    "problem": "Waiting on data"}
    assert text_to_update(row["updates"][1][1]) == {"plan": None, "progress": "Shipped the parser",
                                                    "problem": None}


# --------------------------------------------------------------------------
# Importing the single-sheet file the team actually keeps.
# --------------------------------------------------------------------------

IMPORTED_PROJECTS = ("Imported WIP", "Imported Hold", "Imported Blank")
IMPORTED_STATUSES = ("WIP", "On Hold")


@pytest.fixture
def imported_cleanup(db):
    """Undo what the import test creates, so it cannot colour later tests."""
    yield
    from app.models.project import Project
    from app.models.status import Status
    from app.models.update import Update
    from app.models.vertical import Vertical

    ids = [p.id for p in db.query(Project).filter(Project.name.in_(IMPORTED_PROJECTS)).all()]
    if ids:
        db.query(Update).filter(Update.project_id.in_(ids)).delete(synchronize_session=False)
        db.query(Project).filter(Project.id.in_(ids)).delete(synchronize_session=False)
    db.query(Status).filter(Status.name.in_(IMPORTED_STATUSES)).delete(synchronize_session=False)
    db.query(Vertical).filter(Vertical.name == "Imported").delete(synchronize_session=False)
    db.commit()


def _single_sheet_workbook(path: Path, db):
    """The team's file: one sheet, statuses in a column, weeks across the top."""
    from app.services import daily, weeks as wk

    this_week = wk.week_start_for(daily.today_for(db), wk.start_dow(db))
    last_week = this_week - timedelta(weeks=1)
    wb = Workbook()
    ws = wb.active
    ws.title = "Weekly Update"
    ws.append(LEADING + [wk.header_for(last_week), wk.header_for(this_week)] + TRAILING)
    ws.append(["Imported WIP", "Kunal Rathi", "01.09.2026", "WIP", "NA", "Built the loader", None, "keep me"])
    ws.append(["Imported Hold", "Vishal Trehan", None, "On Hold", None, None, "11.09.2026", None])
    ws.append(["Imported Blank", None, None, None, None, None, "24-.8.2026", None])
    wb.save(path)
    return last_week, this_week


def test_import_takes_the_status_from_the_row_when_there_is_one_sheet(
    client, seed, auth, db, tmp_path, monkeypatch, capsys, imported_cleanup
):
    from app.models.project import Project
    from app.models.status import Status
    from app.models.update import Update

    path = tmp_path / "Weekly_Update.xlsx"
    last_week, this_week = _single_sheet_workbook(path, db)
    importer = _importer()
    argv = ["import_excel.py", str(path), "--vertical", "Imported"]

    # --dry-run still changes nothing.
    before = db.query(Project).count()
    monkeypatch.setattr(sys, "argv", argv + ["--dry-run"])
    assert importer.main() == 0
    dry = capsys.readouterr().out
    assert "3 project(s) would be created" in dry
    db.expire_all()
    assert db.query(Project).count() == before

    monkeypatch.setattr(sys, "argv", argv)
    assert importer.main() == 0
    out = capsys.readouterr().out
    db.expire_all()

    projects = {p.name: p for p in db.query(Project).filter(Project.name.in_(IMPORTED_PROJECTS)).all()}
    assert set(projects) == set(IMPORTED_PROJECTS)

    # The status is the row's, not the sheet's - and nothing is "delivered"
    # just because the importer created its status.
    assert projects["Imported WIP"].status.name == "WIP"
    assert projects["Imported Hold"].status.name == "On Hold"
    assert all(not p.status.is_terminal for p in projects.values() if p.status.name in IMPORTED_STATUSES)

    # "On Hold" is a real status in the real file, so it stays active even
    # though it is also the name of a seed placeholder.
    on_hold = db.query(Status).filter(Status.name == "On Hold").one()
    assert on_hold.is_active

    # A blank Status lands in the first stage of the pipeline by sort order.
    first = db.query(Status).filter(Status.is_active == True).order_by(Status.sort_order, Status.id).first()  # noqa: E712
    assert projects["Imported Blank"].status_id == first.id

    # Dot-separated dates are read...
    assert projects["Imported WIP"].assigned_on == date(2026, 9, 1)
    assert projects["Imported Hold"].actual_completion_date == date(2026, 9, 11)
    # ...and one that cannot be read names the row instead of failing silently.
    assert projects["Imported Blank"].actual_completion_date is None
    assert "Imported Blank" in out and "24-.8.2026" in out

    # Week cells become dated updates; "NA" and blanks do not.
    updates = db.query(Update).filter(Update.project_id == projects["Imported WIP"].id).all()
    assert [u.progress for u in updates] == ["Built the loader"]
    assert db.query(Update).filter(Update.project_id == projects["Imported Hold"].id).count() == 0

    # The update went into this week, so the next export puts it back in the
    # same column it came from.
    from app.services import weeks as wk

    row = _row_for(_export(client, auth).worksheets[0], "Imported WIP")
    assert row[wk.header_for(this_week)] == "Built the loader"
    assert row[wk.header_for(last_week)] is None
    assert row["Status"] == "WIP"
    assert row["Remarks"] == "keep me"


def test_import_script_dry_run_and_real_import(seed, db, tmp_path):
    if not SAMPLE.exists():
        pytest.skip("sample workbook not present")
    import os
    env = {**os.environ}
    args = [sys.executable, "scripts/import_excel.py", str(SAMPLE), "--vertical", "Imported", "--keep-placeholders"]
    dry = subprocess.run(args + ["--dry-run"], capture_output=True, text=True, env=env, cwd=BACKEND_DIR)
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert "18 project(s) would be created" in dry.stdout and "1 skipped" in dry.stdout
    from app.models.project import Project
    before = db.query(Project).count()
    real = subprocess.run(args, capture_output=True, text=True, env=env, cwd=BACKEND_DIR)
    assert real.returncode == 0, real.stdout + real.stderr
    assert "18 project(s) created" in real.stdout
    db.expire_all()
    assert db.query(Project).count() == before + 18
    fdd = db.query(Project).filter(Project.name == "Financial Due Diligence").one()
    assert fdd.assigned_by == "Kunal Rathi"
    again = subprocess.run(args, capture_output=True, text=True, env=env, cwd=BACKEND_DIR)
    assert "0 project(s) created" in again.stdout and "19 skipped" in again.stdout
