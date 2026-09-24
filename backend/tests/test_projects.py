def _create(client, headers, seed, name, **extra):
    return client.post("/projects", headers=headers,
                       json={"name": name, "vertical_id": seed["vertical"], "status_id": seed["status_queue"], **extra})


def test_requestor_can_read_projects_but_not_create(client, seed, auth):
    """The dashboard is deliberately open across verticals so every team can
    see how loaded the AI team is - but reading is all a requestor may do."""
    assert _create(client, auth("req1"), seed, "Nope").status_code == 403
    assert client.get("/projects", headers=auth("req1")).status_code == 200


def test_member_creates_and_defaults_to_self_as_owner(client, seed, auth, db):
    r = _create(client, auth("member"), seed, "Member project")
    assert r.status_code == 201, r.text
    from app.models.project import Project
    p = db.get(Project, r.json()["id"])
    assert [o.id for o in p.owners] == [seed["member"]]
    assert p.created_by_id == seed["member"]


def test_patch_updates_status_and_owners(client, seed, auth, db):
    pid = _create(client, auth("admin"), seed, "Patch me").json()["id"]
    r = client.patch(f"/projects/{pid}", headers=auth("admin"),
                     json={"status_id": seed["status_live"], "owner_ids": [seed["admin"], seed["member"]],
                           "actual_completion_date": "2026-08-30"})
    assert r.status_code == 200, r.text
    assert r.json()["status_id"] == seed["status_live"]
    from app.models.project import Project
    db.expire_all()
    assert {o.id for o in db.get(Project, pid).owners} == {seed["admin"], seed["member"]}


def test_patch_missing_project_is_404(client, seed, auth):
    assert client.patch("/projects/999999", headers=auth("admin"), json={"name": "x"}).status_code == 404


def test_queue_visible_to_requestors_with_names_not_ids(client, seed, auth):
    _create(client, auth("admin"), seed, "Queue visible")
    r = client.get("/projects/queue", headers=auth("req1"))
    assert r.status_code == 200
    item = next(q for q in r.json() if q["name"] == "Queue visible")
    assert item["vertical_name"] == "Operations"
    assert item["status_name"] == "In queue"


def test_updates_require_existing_project_and_internal_role(client, seed, auth):
    pid = _create(client, auth("admin"), seed, "Has updates").json()["id"]
    body = {"project_id": pid, "plan": "Ship", "progress": "Shipped half", "problem": "None"}
    assert client.post("/updates", headers=auth("req1"), json=body).status_code == 403
    r = client.post("/updates", headers=auth("member"), json=body)
    assert r.status_code == 201, r.text
    assert r.json()["author_id"] == seed["member"]
    assert client.post("/updates", headers=auth("member"), json={**body, "project_id": 999999}).status_code == 404
    listed = client.get(f"/updates/project/{pid}", headers=auth("admin")).json()
    assert len(listed) == 1 and listed[0]["plan"] == "Ship"


def test_audit_trail_records_actions(client, seed, auth):
    _create(client, auth("admin"), seed, "Audited")
    r = client.get("/audit-logs", headers=auth("admin"))
    assert r.status_code == 200
    actions = {a["action"] for a in r.json()}
    assert {"login", "create_project"} <= actions
    assert client.get("/audit-logs", headers=auth("member")).status_code == 403


def test_only_an_admin_can_delete_a_project(client, seed, auth, db):
    """Editing is everyday work for the team; deleting is not, so it sits on
    its own feature that defaults to admin."""
    from app.models.project import Project

    made = client.post("/projects", headers=auth("admin"), json={
        "name": "Deletable Project", "vertical_id": seed["vertical"], "status_id": seed["status_queue"],
    }).json()

    assert client.delete(f"/projects/{made['id']}", headers=auth("member")).status_code == 403
    assert client.delete(f"/projects/{made['id']}", headers=auth("req1")).status_code == 403
    assert db.get(Project, made["id"]) is not None

    assert client.delete(f"/projects/{made['id']}", headers=auth("admin")).status_code == 204
    db.expire_all()
    assert db.get(Project, made["id"]) is None


def test_deleting_a_project_takes_its_updates_with_it(client, seed, auth, db):
    """Update rows are meaningless without their project, and the weekly digest
    joins every update back to one."""
    from app.models.update import Update

    made = client.post("/projects", headers=auth("admin"), json={
        "name": "Project With Updates", "vertical_id": seed["vertical"], "status_id": seed["status_queue"],
    }).json()
    client.post("/updates", headers=auth("member"), json={
        "project_id": made["id"], "plan": "p", "progress": "q", "problem": "r",
    })
    assert db.query(Update).filter(Update.project_id == made["id"]).count() == 1

    assert client.delete(f"/projects/{made['id']}", headers=auth("admin")).status_code == 204
    db.expire_all()
    assert db.query(Update).filter(Update.project_id == made["id"]).count() == 0


def test_deleting_is_recorded_with_the_name_that_is_gone(client, seed, auth):
    """The row disappears, so the audit trail has to carry the name."""
    made = client.post("/projects", headers=auth("admin"), json={
        "name": "Audited Deletion", "vertical_id": seed["vertical"], "status_id": seed["status_queue"],
    }).json()
    client.delete(f"/projects/{made['id']}", headers=auth("admin"))

    rows = client.get("/audit-logs", headers=auth("admin"), params={"action": "delete_project"}).json()
    assert any(r["details"] == "Audited Deletion" for r in rows)


def test_deleting_a_missing_project_is_a_404(client, auth):
    assert client.delete("/projects/999999", headers=auth("admin")).status_code == 404


# ---------------------------------------------------------------------------
# The delivered email
# ---------------------------------------------------------------------------

def _approved_project(client, seed, auth, title):
    """File a request, approve it, and return the project it became."""
    import io
    filed = client.post(
        "/requests", headers=auth("req1"),
        data={"vertical_id": seed["vertical"], "title": title, "description": "x"},
        files={"brd_file": ("brd.pdf", io.BytesIO(b"%PDF-1.4 t"), "application/pdf")},
    ).json()
    client.post(f"/requests/{filed['id']}/review", headers=auth("admin"),
                json={"decision": "approved", "status_id": seed["status_queue"]})
    projects = client.get("/projects", headers=auth("admin")).json()
    return next(p for p in projects if p["source_request_id"] == filed["id"])


def test_reaching_a_terminal_status_tells_the_requestor(client, seed, auth, outbox):
    """"Delivered" is the same moment that stamps the completion date."""
    project = _approved_project(client, seed, auth, "Delivered notification")
    outbox.clear()

    r = client.patch(f"/projects/{project['id']}", headers=auth("admin"),
                     json={"status_id": seed["status_live"]})
    assert r.status_code == 200

    assert len(outbox) == 1
    mail = outbox[0]
    assert mail["to"] == ["rita@example.com"]                 # the requestor
    assert "olivia@example.com" in mail["cc"]                 # their vertical head
    assert "management@example.com" in mail["cc"]             # management
    assert "Delivered" in mail["subject"]
    assert "Delivered notification" in mail["subject"]


def test_the_whole_team_can_be_put_on_the_to_line(client, seed, auth, outbox):
    """The tick box on the edit dialog, and nothing more."""
    project = _approved_project(client, seed, auth, "Delivered with the team")
    outbox.clear()

    client.patch(f"/projects/{project['id']}", headers=auth("admin"),
                 json={"status_id": seed["status_live"], "notify_team": True})

    to = outbox[0]["to"]
    assert "rita@example.com" in to
    assert "admin@example.com" in to and "member@example.com" in to
    assert "disabled@example.com" not in to
    assert len(to) == len(set(to))


def test_editing_a_project_that_is_already_live_does_not_mail_again(client, seed, auth, outbox):
    """Only the way IN to a terminal status counts."""
    project = _approved_project(client, seed, auth, "Delivered only once")
    client.patch(f"/projects/{project['id']}", headers=auth("admin"),
                 json={"status_id": seed["status_live"]})
    outbox.clear()

    client.patch(f"/projects/{project['id']}", headers=auth("admin"),
                 json={"remarks": "Monitoring for a month"})
    assert outbox == []


def test_a_project_with_no_request_behind_it_mails_nobody(client, seed, auth, outbox):
    """A project the team raised itself has no requestor to tell."""
    made = client.post("/projects", headers=auth("admin"), json={
        "name": "Raised By The Team", "vertical_id": seed["vertical"],
        "status_id": seed["status_queue"],
    }).json()
    outbox.clear()

    client.patch(f"/projects/{made['id']}", headers=auth("admin"),
                 json={"status_id": seed["status_live"]})
    assert outbox == []
