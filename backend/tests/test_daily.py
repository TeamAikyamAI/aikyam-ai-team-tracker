"""My Day - the personal daily to-do.

The behaviour worth pinning down is the rollover: it is derived from the rows
rather than written by a nightly job, so an unfinished task must appear on every
later day on its own, and the day it was finished must not move afterwards.
"""
from datetime import date, timedelta

import pytest

from app.models.daily_task import DailyTask
from app.services import daily
from app.services import settings as cfg


@pytest.fixture(autouse=True)
def _clean_tasks(db):
    db.query(DailyTask).delete()
    db.commit()
    yield
    db.query(DailyTask).delete()
    db.commit()


def _add(client, auth, who, title, day=None):
    body = {"title": title}
    if day:
        body["task_date"] = day.isoformat()
    r = client.post("/daily-tasks", headers=auth(who), json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_task_added_today_shows_in_todays_open_list(client, auth):
    _add(client, auth, "member", "Write the import script")
    day = client.get("/daily-tasks", headers=auth("member")).json()
    assert [t["title"] for t in day["open"]] == ["Write the import script"]
    assert day["summary"] == {"done": 0, "pending": 1, "carried": 0}
    assert day["is_own"] is True


def test_unfinished_task_rolls_over_by_itself(client, auth, db):
    """No job runs between the two calls - the later day derives it."""
    today = daily.today_for(db)
    _add(client, auth, "member", "Chase the BRD", day=today - timedelta(days=3))

    later = client.get("/daily-tasks", params={"date": today.isoformat()}, headers=auth("member")).json()
    task = later["open"][0]
    assert task["title"] == "Chase the BRD"
    assert task["carried_days"] == 3
    assert later["summary"]["carried"] == 1


def test_finishing_a_task_takes_it_off_later_days_but_leaves_history(client, auth, db):
    today = daily.today_for(db)
    yesterday = today - timedelta(days=1)
    created = _add(client, auth, "member", "Ship the export", day=yesterday)

    client.patch(f"/daily-tasks/{created['id']}", headers=auth("member"), json={"completed": True})

    # Today: gone from open, counted as done today.
    now = client.get("/daily-tasks", headers=auth("member")).json()
    assert now["open"] == []
    assert [t["title"] for t in now["done"]] == ["Ship the export"]

    # Yesterday still shows it as pending - that is what was true then.
    then = client.get("/daily-tasks", params={"date": yesterday.isoformat()}, headers=auth("member")).json()
    assert [t["title"] for t in then["open"]] == ["Ship the export"]
    assert then["done"] == []


def test_unticking_puts_it_back(client, auth):
    created = _add(client, auth, "member", "Half done")
    client.patch(f"/daily-tasks/{created['id']}", headers=auth("member"), json={"completed": True})
    client.patch(f"/daily-tasks/{created['id']}", headers=auth("member"), json={"completed": False})
    day = client.get("/daily-tasks", headers=auth("member")).json()
    assert [t["title"] for t in day["open"]] == ["Half done"]
    assert day["done"] == []


def test_completed_day_follows_the_configured_timezone(client, auth, db):
    """A tick at 23:30 IST belongs to the Indian day, not the UTC one."""
    from datetime import datetime, timezone as tz

    cfg.set_many(db, {"digest_timezone": "Asia/Kolkata"})
    created = _add(client, auth, "member", "Late night fix")
    client.patch(f"/daily-tasks/{created['id']}", headers=auth("member"), json={"completed": True})

    task = db.query(DailyTask).filter(DailyTask.id == created["id"]).one()
    expected = task.completed_at.astimezone(daily.tzinfo_for(db)).date()
    assert task.completed_on == expected

    # Same instant, different configured zone -> a different business day is possible.
    assert daily.today_for(db) == datetime.now(tz.utc).astimezone(daily.tzinfo_for(db)).date()
    cfg.set_many(db, {"digest_timezone": "UTC"})


def test_one_persons_list_is_invisible_to_another(client, auth):
    mine = _add(client, auth, "member", "Members only")
    day = client.get("/daily-tasks", headers=auth("admin")).json()
    assert [t["title"] for t in day["open"]] == []          # admin's own day is empty
    # and the member's task cannot be touched by anyone else
    assert client.patch(f"/daily-tasks/{mine['id']}", headers=auth("admin"),
                        json={"completed": True}).status_code == 404
    assert client.delete(f"/daily-tasks/{mine['id']}", headers=auth("admin")).status_code == 404


def test_admin_can_read_a_members_day_but_not_change_it(client, seed, auth):
    created = _add(client, auth, "member", "Visible to the boss")
    seen = client.get("/daily-tasks", params={"user_id": seed["member"]}, headers=auth("admin"))
    assert seen.status_code == 200
    assert [t["title"] for t in seen.json()["open"]] == ["Visible to the boss"]
    assert seen.json()["is_own"] is False
    assert client.patch(f"/daily-tasks/{created['id']}", headers=auth("admin"),
                        json={"title": "Renamed"}).status_code == 404


def test_member_cannot_read_another_persons_day(client, seed, auth):
    r = client.get("/daily-tasks", params={"user_id": seed["admin"]}, headers=auth("member"))
    assert r.status_code == 403


def test_requestors_have_no_my_day_at_all(client, auth):
    assert client.get("/daily-tasks", headers=auth("req1")).status_code == 403
    assert client.post("/daily-tasks", headers=auth("req1"), json={"title": "nope"}).status_code == 403


def test_team_view_is_admin_only_and_counts_each_person(client, seed, auth, db):
    today = daily.today_for(db)
    a = _add(client, auth, "member", "Done one")
    _add(client, auth, "member", "Still open")
    _add(client, auth, "member", "Old one", day=today - timedelta(days=2))
    client.patch(f"/daily-tasks/{a['id']}", headers=auth("member"), json={"completed": True})

    assert client.get("/daily-tasks/team", headers=auth("member")).status_code == 403

    rows = client.get("/daily-tasks/team", headers=auth("admin")).json()["rows"]
    member_row = next(r for r in rows if r["user_id"] == seed["member"])
    assert member_row["summary"] == {"done": 1, "pending": 2, "carried": 1}


def test_deleting_removes_it_from_the_day(client, auth):
    created = _add(client, auth, "member", "Mistake")
    assert client.delete(f"/daily-tasks/{created['id']}", headers=auth("member")).status_code == 204
    assert client.get("/daily-tasks", headers=auth("member")).json()["open"] == []
