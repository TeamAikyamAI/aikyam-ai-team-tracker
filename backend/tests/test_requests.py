import io


def _submit(client, headers, seed, title="Automate invoice matching", filename="Signed BRD.pdf", body=b"%PDF-1.4 test"):
    return client.post(
        "/requests", headers=headers,
        data={"vertical_id": seed["vertical"], "title": title, "description": "Please build this."},
        files={"brd_file": (filename, io.BytesIO(body), "application/pdf")},
    )


def test_brd_is_compulsory(client, seed, auth):
    r = client.post("/requests", headers=auth("req1"), data={"vertical_id": seed["vertical"], "title": "No BRD"})
    assert r.status_code == 422


def test_empty_brd_rejected(client, seed, auth):
    assert _submit(client, auth("req1"), seed, body=b"").status_code == 400


def test_oversized_brd_rejected(client, seed, auth):
    items = client.get("/settings", headers=auth("admin")).json()["items"]
    max_mb = next(i["value"] for i in items if i["key"] == "max_brd_upload_mb")
    big = b"x" * (max_mb * 1024 * 1024 + 1)
    assert _submit(client, auth("req1"), seed, body=big).status_code == 413


def test_submit_sanitises_filename_hides_path_and_notifies_chain(client, seed, auth, outbox):
    outbox.clear()
    r = _submit(client, auth("req1"), seed, filename="../../etc/pass wd?.pdf")
    assert r.status_code == 201, r.text
    body = r.json()
    assert "brd_file_path" not in body
    assert body["brd_filename"] == "pass_wd_.pdf"  # directory part dropped, unsafe chars replaced
    assert body["status"] == "submitted"
    # The whole AI team gets the mail; vertical head AND management are CC'd
    assert len(outbox) == 1
    assert outbox[0]["to"] == ["admin@example.com", "member@example.com"]
    assert outbox[0]["cc"] == ["olivia@example.com", "management@example.com"]
    assert outbox[0]["reply_to"] == "rita@example.com"


def test_every_active_team_member_is_notified_not_just_admins(client, seed, auth, outbox, db):
    """A request that only reaches the shared admin mailbox is one the engineer
    who will actually build it never saw. Deactivated people stay out."""
    outbox.clear()
    assert _submit(client, auth("req1"), seed, title="Notify the whole team").status_code == 201

    recipients = set(outbox[0]["to"])
    assert "admin@example.com" in recipients      # admin
    assert "member@example.com" in recipients     # team member
    assert "disabled@example.com" not in recipients
    assert "rita@example.com" not in recipients   # requestors are not the team


def test_team_members_cannot_file_requests_by_default(client, seed, auth):
    """The AI team receives requests, it does not file them against itself.
    An admin can still switch this on per role in Admin > Access."""
    assert _submit(client, auth("member"), seed, title="Filed by the team itself").status_code == 403


def test_a_team_member_filing_a_request_is_not_mailed_twice(client, seed, auth, outbox, db):
    """If an admin does turn Apply on for the team, the submitter appears in the
    To line once, not twice."""
    from app.services import permissions as perms
    perms.set_many(db, {"apply": {"member": True}})
    try:
        outbox.clear()
        assert _submit(client, auth("member"), seed, title="Filed by the team itself").status_code == 201
        to = outbox[0]["to"]
        assert len(to) == len(set(to))
        assert "member@example.com" in to
    finally:
        perms.set_many(db, {"apply": {"member": False}})


def test_requestor_sees_only_own_requests(client, seed, auth):
    _submit(client, auth("req2"), seed, title="Raj's request")
    mine = client.get("/requests", headers=auth("req1")).json()
    assert mine and all(r["requestor_id"] == seed["req1"] for r in mine)
    everyone = client.get("/requests", headers=auth("member")).json()
    assert {r["requestor_id"] for r in everyone} >= {seed["req1"], seed["req2"]}


def test_brd_download_is_authenticated_and_scoped(client, seed, auth):
    rid = _submit(client, auth("req1"), seed, title="Scoped download", body=b"%PDF-1.4 scoped").json()["id"]
    assert client.get(f"/requests/{rid}/brd").status_code == 401
    assert client.get(f"/requests/{rid}/brd", headers=auth("req2")).status_code == 404
    r = client.get(f"/requests/{rid}/brd", headers=auth("req1"))
    assert r.status_code == 200 and r.content == b"%PDF-1.4 scoped"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in r.headers["content-disposition"]
    assert client.get(f"/requests/{rid}/brd", headers=auth("member")).status_code == 200
    # the old public static mount must be gone (at the root and under /api)
    assert client.get("http://testserver/uploads/anything.pdf").status_code == 404
    assert client.get("/uploads/anything.pdf").status_code == 404


def test_requestor_cannot_review(client, seed, auth):
    rid = _submit(client, auth("req1"), seed, title="Review me").json()["id"]
    r = client.post(f"/requests/{rid}/review", headers=auth("req1"),
                    json={"decision": "approved", "status_id": seed["status_queue"]})
    assert r.status_code == 403


def test_approval_creates_linked_project(client, seed, auth):
    rid = _submit(client, auth("req1"), seed, title="Approve me please").json()["id"]
    r = client.post(f"/requests/{rid}/review", headers=auth("admin"),
                    json={"decision": "approved", "status_id": seed["status_queue"], "review_notes": "Go"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"
    projects = client.get("/projects", headers=auth("admin")).json()
    linked = [p for p in projects if p["source_request_id"] == rid]
    assert len(linked) == 1
    assert linked[0]["name"] == "Approve me please"
    assert linked[0]["status_id"] == seed["status_queue"]


def test_invalid_decision_rejected(client, seed, auth):
    rid = _submit(client, auth("req1"), seed, title="Bad decision").json()["id"]
    r = client.post(f"/requests/{rid}/review", headers=auth("admin"), json={"decision": "maybe"})
    assert r.status_code == 400


def test_the_requestor_and_their_vertical_head_are_told_the_decision(client, seed, auth, outbox):
    """A decision that only exists inside the app is a decision the requestor
    has to come looking for. Approving mails them, CC'ing the head who signed
    the BRD, and names the project it became."""
    filed = _submit(client, auth("req1"), seed, title="Tell me what you decided").json()
    outbox.clear()

    r = client.post(f"/requests/{filed['id']}/review", headers=auth("admin"),
                    json={"decision": "approved", "review_notes": "Starting next sprint."})
    assert r.status_code == 200

    assert len(outbox) == 1
    mail = outbox[0]
    assert mail["to"] == ["rita@example.com"]
    assert mail["cc"] == ["olivia@example.com"]
    assert "Approved" in mail["subject"]
    assert "Starting next sprint." in mail["html"]
    assert "Tell me what you decided" in mail["html"]


def test_a_rejection_carries_the_reason(client, seed, auth, outbox):
    filed = _submit(client, auth("req2"), seed, title="Rejected with a reason").json()
    outbox.clear()

    r = client.post(f"/requests/{filed['id']}/review", headers=auth("admin"),
                    json={"decision": "rejected", "review_notes": "Duplicate of an existing tool."})
    assert r.status_code == 200

    mail = outbox[0]
    assert mail["to"] == ["raj@example.com"]
    assert "Not taken up" in mail["subject"]
    assert "Duplicate of an existing tool." in mail["html"]
    # Nothing was built, so no project is named.
    assert "on the tracker as" not in mail["html"]


def test_a_review_still_succeeds_when_the_mailbox_is_broken(client, seed, auth, monkeypatch):
    """The decision is already committed - a mail failure must not undo it."""
    import app.routers.service_requests as sr
    filed = _submit(client, auth("req1"), seed, title="Mail is broken but review works").json()

    def boom(*a, **k):
        raise RuntimeError("SMTP is down")

    monkeypatch.setattr(sr, "send_email", boom)
    r = client.post(f"/requests/{filed['id']}/review", headers=auth("admin"),
                    json={"decision": "on_hold", "review_notes": "Parked."})
    assert r.status_code == 200
    assert r.json()["status"] == "on_hold"


def test_a_submission_still_succeeds_when_the_mailbox_is_broken(client, seed, auth, monkeypatch):
    """The row is committed before the mail goes out. A failure there must not
    turn a saved request into a 500 - that is what made a requestor file the
    same thing twice."""
    import app.routers.service_requests as sr

    def boom(*a, **k):
        raise RuntimeError("SMTP is down")

    monkeypatch.setattr(sr, "send_email", boom)
    r = _submit(client, auth("req1"), seed, title="Saved even though mail failed")
    assert r.status_code == 201
    assert r.json()["status"] == "submitted"
