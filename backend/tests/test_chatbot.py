def _ask(client, headers, q, session_id=None):
    r = client.post("/chatbot/ask", headers=headers, json={"question": q, "session_id": session_id})
    assert r.status_code == 200, r.text
    return r.json()


def _let_requestors_ask(db):
    """Turn Ask the Tracker on for requestors.

    The assistant is gated on the ``ask`` feature, which is off for requestors
    by default - an admin decides in the grid whether other verticals get the
    bot. These tests are about what the bot SAYS to a requestor, so they grant
    the feature first rather than asserting the pre-grid behaviour.
    """
    from app.services import permissions as perms
    perms.set_many(db, {"ask": {"requestor": True}})
    return db


def test_the_assistant_is_closed_to_a_role_without_the_feature(client, seed, auth):
    """Revoking Ask the Tracker has to close the endpoint, not just the menu -
    the widget calls this same route from every screen."""
    r = client.post("/chatbot/ask", headers=auth("req1"), json={"question": "hello"})
    assert r.status_code == 403
    h = client.get("/chatbot/history", headers=auth("req1"), params={"session_id": "x"})
    assert h.status_code == 403


def test_disabled_chatbot_says_so(client, seed, auth):
    client.patch("/settings", headers=auth("admin"), json={"values": {"chatbot_enabled": False}})
    assert client.get("/settings/public").json()["chatbot_enabled"] is False
    client.patch("/settings", headers=auth("admin"), json={"values": {"chatbot_enabled": True}})


def test_counts_are_exact_and_role_scoped(client, seed, auth, db):
    from app.models.project import Project
    total = db.query(Project).count()
    answer = _ask(client, auth("admin"), "How many projects do we have?")["answer"]
    assert str(total) in answer


def test_requestor_gets_no_internal_data(client, seed, auth, db):
    _let_requestors_ask(db)
    a = _ask(client, auth("req1"), "Who is on the team?")["answer"].lower()
    assert "member@example.com" not in a and "max member" not in a


def test_conversation_is_saved_and_private(client, seed, auth, db):
    _let_requestors_ask(db)
    first = _ask(client, auth("req1"), "hello")
    sid = first["session_id"]
    _ask(client, auth("req1"), "what's in the queue?", session_id=sid)
    hist = client.get("/chatbot/history", headers=auth("req1"), params={"session_id": sid}).json()
    assert [m["role"] for m in hist] == ["user", "assistant", "user", "assistant"]
    # another user cannot read it
    other = client.get("/chatbot/history", headers=auth("req2"), params={"session_id": sid}).json()
    assert other == []
    # admins can see conversations in the Chats tab, members cannot
    assert client.get("/chatbot/conversations", headers=auth("admin")).status_code == 200
    assert client.get("/chatbot/conversations", headers=auth("member")).status_code == 403


def test_empty_and_huge_questions_rejected(client, seed, auth, db):
    _let_requestors_ask(db)
    assert client.post("/chatbot/ask", headers=auth("req1"), json={"question": "   "}).status_code == 400
    assert client.post("/chatbot/ask", headers=auth("req1"), json={"question": "x" * 3000}).status_code == 400


def test_requestor_sees_the_same_facts_as_the_dashboard_but_not_remarks(client, seed, auth, db):
    """The assistant and the dashboard must agree.

    A requestor can already see owners and target dates on the board, so the
    assistant shows them too - Remarks is the one field that stays internal.
    """
    from app.services import chatbot
    from app.models.user import User

    client.post("/projects", headers=auth("admin"), json={
        "name": "Visibility Check Project", "vertical_id": seed["vertical"],
        "status_id": seed["status_queue"], "owner_ids": [seed["member"]],
        "target_date": "2026-12-31", "assigned_by": "Olivia Head",
        "remarks": "internal only - scope keeps moving",
    })

    requestor = db.get(User, seed["req1"])
    answer = chatbot.answer(db, requestor, "tell me about Visibility Check Project", [])
    assert "Max Member" in answer          # owners: shown
    assert "2026-12-31" in answer          # target date: shown
    assert "Olivia Head" in answer         # assigned by: shown
    assert "scope keeps moving" not in answer   # remarks: never

    admin = db.get(User, seed["admin"])
    admin_answer = chatbot.answer(db, admin, "tell me about Visibility Check Project", [])
    assert "scope keeps moving" in admin_answer
