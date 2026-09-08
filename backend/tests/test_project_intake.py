"""Adding a project by talking to the assistant.

The flow is the one exception to the bot being read-only, so these tests are
mostly about the edges: nothing is created without an explicit save, a
requestor cannot use it at all, and an answer that happens to look like a
question is still treated as an answer.
"""
import pytest

from app.models.chat_draft import ChatDraft
from app.models.project import Project
from app.models.user import User


@pytest.fixture(autouse=True)
def _clean(db):
    db.query(ChatDraft).delete()
    db.commit()
    yield
    db.query(ChatDraft).delete()
    db.commit()


def say(client, auth, who, text, session=None):
    body = {"question": text}
    if session:
        body["session_id"] = session
    r = client.post("/chatbot/ask", headers=auth(who), json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_full_happy_path_creates_the_project(client, seed, auth, db):
    s = say(client, auth, "admin", "add a project")
    sid = s["session_id"]
    assert "what is the project called" in s["answer"].lower()

    assert "vertical" in say(client, auth, "admin", "Margin Call Automation", sid)["answer"].lower()
    assert "status" in say(client, auth, "admin", "Operations", sid)["answer"].lower()
    assert "asked for it" in say(client, auth, "admin", "In queue", sid)["answer"].lower()
    more = say(client, auth, "admin", "Olivia Head", sid)["answer"].lower()
    assert "save" in more  # offered the fork

    confirm = say(client, auth, "admin", "save", sid)["answer"]
    assert "Margin Call Automation" in confirm and "Save this?" in confirm

    # Nothing exists until the final save.
    assert db.query(Project).filter(Project.name == "Margin Call Automation").first() is None

    done = say(client, auth, "admin", "save", sid)["answer"]
    assert "Added" in done

    p = db.query(Project).filter(Project.name == "Margin Call Automation").one()
    assert p.vertical_id == seed["vertical"]
    assert p.status_id == seed["status_queue"]
    assert p.assigned_by == "Olivia Head"
    assert p.created_by_id == seed["admin"]
    assert db.query(ChatDraft).count() == 0  # draft cleaned up


def test_optional_details_are_collected(client, seed, auth, db):
    sid = say(client, auth, "admin", "add a project")["session_id"]
    say(client, auth, "admin", "Detailed Project", sid)
    say(client, auth, "admin", "Operations", sid)
    say(client, auth, "admin", "In queue", sid)
    say(client, auth, "admin", "Vishal Trehan", sid)

    say(client, auth, "admin", "more", sid)
    say(client, auth, "admin", "Automates the daily margin file", sid)   # description
    say(client, auth, "admin", "25/08/2026", sid)                        # assigned on
    say(client, auth, "admin", "30/09/2026", sid)                        # target
    say(client, auth, "admin", "me", sid)                                # owners
    say(client, auth, "admin", "waiting on file format", sid)            # remarks
    say(client, auth, "admin", "save", sid)

    p = db.query(Project).filter(Project.name == "Detailed Project").one()
    assert p.description == "Automates the daily margin file"
    assert p.assigned_on.isoformat() == "2026-08-25"
    assert p.target_date.isoformat() == "2026-09-30"
    assert p.remarks == "waiting on file format"
    assert [o.id for o in p.owners] == [seed["admin"]]


def test_cancel_leaves_nothing_behind(client, auth, db):
    sid = say(client, auth, "admin", "add a project")["session_id"]
    say(client, auth, "admin", "Abandoned Project", sid)
    out = say(client, auth, "admin", "cancel", sid)["answer"]
    assert "Cancelled" in out
    assert db.query(Project).filter(Project.name == "Abandoned Project").first() is None
    assert db.query(ChatDraft).count() == 0


def test_an_answer_is_not_mistaken_for_a_question(client, seed, auth, db):
    """A project name that matches an existing project must still be an answer."""
    client.post("/projects", headers=auth("admin"), json={
        "name": "Existing Thing", "vertical_id": seed["vertical"], "status_id": seed["status_queue"]})

    sid = say(client, auth, "admin", "add a project")["session_id"]
    out = say(client, auth, "admin", "Existing Thing", sid)["answer"]
    # It is read as the name (and refused as a duplicate), not as "tell me about it".
    assert "already a project called" in out
    assert "Status:" not in out


def test_duplicate_name_is_refused_then_accepts_a_new_one(client, seed, auth, db):
    client.post("/projects", headers=auth("admin"), json={
        "name": "Taken Name", "vertical_id": seed["vertical"], "status_id": seed["status_queue"]})
    sid = say(client, auth, "admin", "add a project")["session_id"]
    assert "already a project" in say(client, auth, "admin", "Taken Name", sid)["answer"]
    assert "vertical" in say(client, auth, "admin", "Free Name", sid)["answer"].lower()


def test_unknown_vertical_re_asks_with_the_list(client, auth):
    sid = say(client, auth, "admin", "add a project")["session_id"]
    say(client, auth, "admin", "Some Project", sid)
    out = say(client, auth, "admin", "Marketing", sid)["answer"]
    assert "did not recognise" in out and "Operations" in out


def test_picking_by_number_works(client, auth, db):
    """"1" means the first row of the list the bot just printed."""
    from app.models.status import Status
    from app.models.vertical import Vertical

    first_vertical = db.query(Vertical).filter(Vertical.is_active == True).order_by(Vertical.name).first()  # noqa: E712
    first_status = db.query(Status).filter(Status.is_active == True).order_by(Status.sort_order).first()  # noqa: E712

    sid = say(client, auth, "admin", "add a project")["session_id"]
    say(client, auth, "admin", "Numbered Pick", sid)
    say(client, auth, "admin", "1", sid)   # first vertical
    say(client, auth, "admin", "1", sid)   # first status
    say(client, auth, "admin", "Someone", sid)
    say(client, auth, "admin", "save", sid)
    say(client, auth, "admin", "save", sid)

    p = db.query(Project).filter(Project.name == "Numbered Pick").one()
    assert p.vertical_id == first_vertical.id
    assert p.status_id == first_status.id


def test_a_requestor_is_sent_to_the_brd_route(client, auth, db):
    # Only reachable at all when an admin has given requestors the assistant;
    # the point of the test is that even then it will not write for them.
    from app.services import permissions as perms
    perms.set_many(db, {"ask": {"requestor": True}})
    out = say(client, auth, "req1", "add a project")["answer"]
    assert "Apply for Service" in out and "BRD" in out
    assert db.query(ChatDraft).count() == 0


def test_members_can_use_it(client, auth):
    out = say(client, auth, "member", "add a project")["answer"]
    assert "what is the project called" in out.lower()


def test_other_write_attempts_are_still_refused(client, seed, auth, db):
    client.post("/projects", headers=auth("admin"), json={
        "name": "Do Not Touch", "vertical_id": seed["vertical"], "status_id": seed["status_queue"]})
    out = say(client, auth, "admin", "delete Do Not Touch")["answer"]
    assert "can only read the tracker" in out
    assert db.query(Project).filter(Project.name == "Do Not Touch").first() is not None


def test_one_persons_draft_is_invisible_to_another(client, auth, db):
    sid = say(client, auth, "admin", "add a project")["session_id"]
    # Same session id, different user: no draft of theirs, so it is a normal question.
    out = say(client, auth, "member", "what's overdue?", sid)["answer"]
    assert "what is the project called" not in out.lower()
    assert db.query(ChatDraft).count() == 1


def test_the_stateless_ask_page_points_at_the_chat_window(client, auth):
    r = client.post("/ai/ask", headers=auth("admin"), json={"question": "add a project"})
    assert r.status_code == 200
    assert "chat window" in r.json()["answer"].lower()
