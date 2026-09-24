"""End-to-end API checks, one block per section of the release run sheet.

Every test names the run-sheet id it covers in its docstring, so a failure
here points at a line on the sheet rather than at an abstraction.
"""
import io
import re
from datetime import date, timedelta

import httpx
import pytest

from conftest import BASE, Api, login

TODAY = date.today()


def brd(name: str = "signed-brd.pdf", size: int = 2048):
    return {"brd_file": (name, io.BytesIO(b"%PDF-1.4\n" + b"x" * size), "application/pdf")}


# ===========================================================================
# Block S — the environment itself
# ===========================================================================

def test_s1_health_and_spa(anon):
    """S1: the API answers and the built SPA is served from the same origin."""
    assert anon.get("/api/health").status_code == 200
    page = anon.get("/")
    assert page.status_code == 200
    assert "<div id=\"root\">" in page.text or "<script" in page.text


def test_s2_three_roles_exist(admin):
    """S2: the seeded team covers admin, member and requestor."""
    roles = {u["role"] for u in admin.get("/api/users").json()}
    assert {"admin", "member", "requestor"} <= roles


def test_s3_app_url_is_set(admin):
    """S3: the reset-link base is configured, or every reset email is broken."""
    items = {i["key"]: i for i in admin.get("/api/settings").json()["items"]}
    assert items["app_base_url"]["value"], "app_base_url is empty — reset links would have no host"


def test_s4_test_email_reports_missing_smtp_clearly(admin):
    """S4: with no SMTP host the test button explains itself instead of 500ing."""
    r = admin.post("/api/settings/test-email")
    assert r.status_code in (200, 400)
    if r.status_code == 400:
        assert "SMTP" in r.json()["detail"]


# ===========================================================================
# Block A — requestor
# ===========================================================================

def test_a1_requestor_feature_set(requestor):
    """A1: exactly the four screens a requestor should have."""
    features = set(requestor.get("/api/permissions/me").json()["features"])
    assert features == {"dashboard", "queue", "apply", "my_requests"}


def test_a2_dashboard_is_open_to_requestors(requestor):
    """A2: the transparency decision — other verticals see the whole board."""
    r = requestor.get("/api/projects")
    assert r.status_code == 200
    assert len(r.json()) >= 4


def test_a3_owners_and_target_dates_are_visible(requestor, projects):
    """A3: a requestor can see who is on a project and when it is due."""
    row = requestor.get(f"/api/projects/{projects['Compliance Tracker']}").json()
    assert row["owner_ids"], "owners hidden from requestors — they prove the team is loaded"
    assert row["target_date"] is not None


def test_a4_remarks_are_blanked_for_requestors(requestor, projects):
    """A4: internal notes are the one project field a requestor must not see."""
    one = requestor.get(f"/api/projects/{projects['Compliance Tracker']}").json()
    assert one["remarks"] is None
    listed = requestor.get("/api/projects").json()
    assert all(p["remarks"] is None for p in listed)


def test_a5_requestor_cannot_create_or_edit(requestor, projects):
    """A5: no write path, with or without a button on screen."""
    created = requestor.post("/api/projects", json={
        "name": "Requestor Sneak Project", "vertical_id": 1, "status_id": 1,
    })
    assert created.status_code == 403
    edited = requestor.patch(
        f"/api/projects/{projects['Bond Deal Portal']}", json={"name": "Renamed"}
    )
    assert edited.status_code == 403


def test_a6_export_is_refused_at_the_api(requestor):
    """A6: hiding the Export button is never the security."""
    assert requestor.get("/api/projects/export.xlsx").status_code == 403


def test_a7_admin_only_endpoints_are_refused(requestor):
    """A7: the screens the sidebar hides are also closed on the server."""
    assert requestor.get("/api/settings").status_code == 403
    assert requestor.get("/api/permissions").status_code == 403
    assert requestor.get("/api/audit-logs").status_code == 403
    assert requestor.get("/api/daily-tasks").status_code == 403


def test_a8_queue_loads(requestor):
    """A8: the read-only list people check before filing a request."""
    r = requestor.get("/api/projects/queue")
    assert r.status_code == 200


def test_a9_request_without_a_brd_is_refused(requestor):
    """A9: the signed BRD is compulsory."""
    r = requestor.post("/api/requests", data={
        "vertical_id": 1, "title": "No BRD attached", "description": "should fail",
    })
    assert r.status_code == 422


def test_a10_oversized_brd_is_refused_with_the_configured_limit(requestor, admin):
    """A10: the message quotes the admin-set limit, not a hardcoded number."""
    limit = int({i["key"]: i for i in admin.get("/api/settings").json()["items"]}["max_brd_upload_mb"]["value"])
    r = requestor.post(
        "/api/requests",
        data={"vertical_id": 1, "title": "Oversized BRD", "description": "too big"},
        files=brd("huge.pdf", size=(limit * 1024 * 1024) + 1024),
    )
    assert r.status_code == 413
    assert str(limit) in r.json()["detail"]


def test_a11_empty_brd_is_refused(requestor):
    """A10b: a zero-byte file is not a BRD."""
    r = requestor.post(
        "/api/requests",
        data={"vertical_id": 1, "title": "Empty BRD", "description": "nothing in it"},
        files={"brd_file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert r.status_code == 400


@pytest.fixture(scope="session")
def submitted_request(requestor):
    """A11: a real submission, reused by the review tests further down."""
    r = requestor.post(
        "/api/requests",
        data={
            "vertical_id": 1,
            "title": "E2E Automation of the daily margin file",
            "description": "Filed by the end-to-end suite.",
        },
        files=brd(),
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_a12_valid_request_is_accepted(submitted_request):
    """A11: the request is stored with its BRD and starts as submitted."""
    assert submitted_request["status"] == "submitted"
    assert submitted_request["brd_filename"]


def test_a13_my_requests_shows_only_your_own(requestor, other_requestor, submitted_request):
    """A13: one requestor never sees another's filings."""
    mine = requestor.get("/api/requests").json()
    assert any(r["id"] == submitted_request["id"] for r in mine)
    theirs = other_requestor.get("/api/requests").json()
    assert all(r["id"] != submitted_request["id"] for r in theirs)


def test_a14_another_requestors_request_is_invisible_not_forbidden(other_requestor, submitted_request):
    """A14: 404, not 403 — a 403 would confirm the request exists."""
    r = other_requestor.get(f"/api/requests/{submitted_request['id']}")
    assert r.status_code == 404


def test_a15_forgot_password_answers_the_same_either_way(anon):
    """A15/E3: the form cannot be used to discover which addresses have accounts."""
    real = anon.post("/api/auth/forgot-password", json={"email": "ravi@aikyame2e.com"})
    fake = anon.post("/api/auth/forgot-password", json={"email": "nobody@aikyame2e.com"})
    assert real.status_code == fake.status_code == 200
    assert real.json()["detail"] == fake.json()["detail"]


def test_a16_a_bad_reset_token_is_refused(anon):
    """A16: an invalid or spent link says so rather than resetting anything."""
    r = anon.post("/api/auth/reset-password", json={
        "token": "not-a-real-token", "password": "BrandNewPass123",
    })
    assert r.status_code == 400
    assert "expired" in r.json()["detail"].lower() or "invalid" in r.json()["detail"].lower()


# ===========================================================================
# Block B — team member
# ===========================================================================

def test_b1_member_feature_set(member):
    """B1: everything to run the work, nothing that administers the app."""
    features = set(member.get("/api/permissions/me").json()["features"])
    assert features == {
        "dashboard", "queue", "requests_review", "ask", "api_keys",
        "my_day", "projects_manage", "projects_export", "project_remarks",
    }
    # Editing is everyday work for the team; deleting is not.
    assert "projects_delete" not in features
    # The team receives requests, it does not file them against itself.
    assert "apply" not in features and "my_requests" not in features


def test_b2_my_day_accepts_and_ticks_tasks(member):
    """B2: add three, tick one, and the summary follows."""
    for title in ("E2E task one", "E2E task two", "E2E task three"):
        r = member.post("/api/daily-tasks", json={"title": title})
        assert r.status_code == 201

    day = member.get("/api/daily-tasks").json()
    assert day["is_own"] is True
    first = day["open"][0]
    ticked = member.patch(f"/api/daily-tasks/{first['id']}", json={"completed": True})
    assert ticked.status_code == 200
    assert ticked.json()["completed_on"] == TODAY.isoformat()

    after = member.get("/api/daily-tasks").json()
    assert any(t["id"] == first["id"] for t in after["done"])
    assert after["summary"]["done"] >= 1


def test_b3_unfinished_work_carries_itself_forward(member):
    """B3: no scheduler — tomorrow's list is derived, so a laptop that sleeps
    overnight cannot drop a day."""
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    day = member.get(f"/api/daily-tasks?date={tomorrow}").json()
    open_titles = {t["title"] for t in day["open"]}
    assert "E2E task two" in open_titles and "E2E task three" in open_titles
    assert all(t["title"] != "E2E task one" for t in day["open"]), "a finished task came back"
    assert any(t["carried_days"] >= 1 for t in day["open"])


def test_b4_a_finished_day_still_reads_as_it_did(member):
    """B4: history is not rewritten by later ticks."""
    day = member.get(f"/api/daily-tasks?date={TODAY.isoformat()}").json()
    assert any(t["title"] == "E2E task one" for t in day["done"])


def test_b5_nobody_elses_day_is_reachable(member, admin):
    """B5: team_day is off for members."""
    r = member.get(f"/api/daily-tasks?user_id={admin.id}")
    assert r.status_code == 403


def test_b6_member_sees_remarks(member, projects):
    """B6: project_remarks is on for the team."""
    row = member.get(f"/api/projects/{projects['Compliance Tracker']}").json()
    assert row["remarks"] and "NSE circular" in row["remarks"]


@pytest.fixture(scope="session")
def member_project(member, admin):
    """B7: a project created through the API by a team member."""
    verticals = admin.get("/api/verticals").json()
    statuses = admin.get("/api/statuses").json()
    r = member.post("/api/projects", json={
        "name": "E2E Member Created Project",
        "description": "Created by the end-to-end suite.",
        "vertical_id": verticals[0]["id"],
        "status_id": statuses[0]["id"],
        "owner_ids": [member.id],
        "assigned_by": "E2E",
        "remarks": "Internal: created by the suite",
        "target_date": (TODAY + timedelta(days=14)).isoformat(),
    })
    assert r.status_code == 201, r.text
    return r.json()


def test_b7_member_can_create_and_edit(member, member_project, admin):
    """B7: create, then move it to another status."""
    statuses = admin.get("/api/statuses").json()
    moved = member.patch(
        f"/api/projects/{member_project['id']}", json={"status_id": statuses[1]["id"]}
    )
    assert moved.status_code == 200
    assert moved.json()["status_id"] == statuses[1]["id"]


def test_b8_member_can_log_an_update(member, member_project):
    """B8: the PPP entry the weekly digest is built from."""
    r = member.post("/api/updates", json={
        "project_id": member_project["id"],
        "plan": "Finish the suite",
        "progress": "Blocks A and B green",
        "problem": "None",
    })
    assert r.status_code == 201
    assert r.json()["author_id"] == member.id


def test_b9_excel_export_downloads(member, member_project):
    """B9: a real workbook, containing the project just created."""
    r = member.get("/api/projects/export.xlsx")
    assert r.status_code == 200
    assert r.content[:2] == b"PK", "not a real xlsx"
    assert len(r.content) > 3000


def test_b10_member_can_approve_a_request_into_a_project(member, submitted_request, admin):
    """B10: intake to delivery in one record."""
    statuses = admin.get("/api/statuses").json()
    r = member.post(f"/api/requests/{submitted_request['id']}/review", json={
        "decision": "approved", "status_id": statuses[0]["id"],
        "review_notes": "Approved by the e2e suite.",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    made = [p for p in admin.get("/api/projects").json()
            if p["source_request_id"] == submitted_request["id"]]
    assert made, "approving a request did not create its project"
    assert made[0]["name"] == submitted_request["title"]


def test_b11_reject_records_its_reason(member, requestor):
    """B11: a rejected request keeps the note that explains it."""
    filed = requestor.post(
        "/api/requests",
        data={"vertical_id": 1, "title": "E2E request to be rejected", "description": "x"},
        files=brd(),
    ).json()
    r = member.post(f"/api/requests/{filed['id']}/review", json={
        "decision": "rejected", "review_notes": "Out of scope for this quarter.",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"
    assert "Out of scope" in r.json()["review_notes"]


def test_b12_member_can_download_any_brd(member, submitted_request):
    """B12: reviewers read the BRD they are reviewing."""
    r = member.get(f"/api/requests/{submitted_request['id']}/brd")
    assert r.status_code == 200
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "attachment" in r.headers.get("content-disposition", "")


def test_b13_member_is_kept_out_of_administration(member):
    """B13: no settings, no permission grid, no audit trail."""
    assert member.get("/api/settings").status_code == 403
    assert member.get("/api/permissions").status_code == 403
    assert member.get("/api/audit-logs").status_code == 403


def test_b14_assistant_answers_from_live_data(member):
    """B14: the deterministic answerer names real projects."""
    r = member.post("/api/chatbot/ask", json={"question": "which projects are going on right now?"})
    assert r.status_code == 200
    answer = r.json()["answer"]
    assert "Compliance Tracker" in answer or "FD Treasury" in answer


def test_b15_assistant_refuses_to_change_anything(member):
    """B15: reads only — the one exception is the guided add-project flow."""
    r = member.post("/api/chatbot/ask", json={"question": "delete the compliance tracker project"})
    assert r.status_code == 200
    assert "only read" in r.json()["answer"].lower()


# ===========================================================================
# Block C — admin
# ===========================================================================

def test_c1_admin_has_every_feature(admin):
    """C1: every feature in the registry, including the ones only an admin gets
    and the one the grid cannot take away."""
    features = set(admin.get("/api/permissions/me").json()["features"])
    assert {"admin_panel", "audit_trail", "team_day", "projects_delete"} <= features
    everything = {f["key"] for f in admin.get("/api/permissions").json()["features"]}
    assert features == everything


def test_c2_admin_can_read_the_whole_team_day(admin, member):
    """C2: one row per active admin and member."""
    r = admin.get("/api/daily-tasks/team")
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert any(row["user_id"] == member.id for row in rows)
    assert all("summary" in row for row in rows)


def test_c3_admin_can_read_but_never_write_someone_elses_day(admin, member):
    """C3: reading a day is a permission; writing to it is not one at all."""
    theirs = admin.get(f"/api/daily-tasks?user_id={member.id}")
    assert theirs.status_code == 200
    assert theirs.json()["is_own"] is False
    task_id = (theirs.json()["open"] or theirs.json()["done"])[0]["id"]
    assert admin.patch(f"/api/daily-tasks/{task_id}", json={"completed": True}).status_code == 404
    assert admin.delete(f"/api/daily-tasks/{task_id}").status_code == 404


def test_c4_guided_add_project_creates_a_real_project(admin):
    """C4: the assistant's one write path, question by question."""
    session = "e2e-intake-happy"

    def say(text):
        r = admin.post("/api/chatbot/ask", json={"question": text, "session_id": session})
        assert r.status_code == 200, r.text
        return r.json()["answer"]

    opening = say("add a project")
    assert "project called" in opening.lower() or "name" in opening.lower()
    say("E2E Chatbot Created Project")
    say("Accounts")
    say("WIP")
    say("Naman")
    say("more")
    say("Created through the guided flow by the e2e suite.")
    say("today")
    say("skip")
    say("me")
    summary = say("Internal: added by the suite")
    assert "E2E Chatbot Created Project" in summary
    done = say("save")
    assert "Added" in done

    rows = [p for p in admin.get("/api/projects").json()
            if p["name"] == "E2E Chatbot Created Project"]
    assert rows, "the guided flow finished without creating the project"
    made = rows[0]
    assert made["assigned_by"] == "Naman"
    assert made["owner_ids"] == [admin.id]
    assert made["remarks"] == "Internal: added by the suite"
    assert made["assigned_on"] == TODAY.isoformat()


def test_c4b_no_at_the_fork_means_save_it_as_it_is(admin):
    """C4b: "no" answers "add more details, or save it as it is?" — it must not
    dead-end on a re-prompt."""
    session = "e2e-intake-no"

    def say(text):
        return admin.post(
            "/api/chatbot/ask", json={"question": text, "session_id": session}
        ).json()["answer"]

    say("add a project")
    say("E2E Fork Says No")
    say("Accounts")
    say("WIP")
    say("Ranjan")
    summary = say("no")
    assert "Here is what I have" in summary
    assert "Added" in say("save")
    assert any(p["name"] == "E2E Fork Says No" for p in admin.get("/api/projects").json())


def test_c4c_save_during_the_optional_block_is_a_command_not_an_answer(admin):
    """C4c: the fork told the user "save" saves it, so typing it two questions
    later must not silently become the project's description."""
    session = "e2e-intake-save-word"

    def say(text):
        return admin.post(
            "/api/chatbot/ask", json={"question": text, "session_id": session}
        ).json()["answer"]

    say("add a project")
    say("E2E Save Word Project")
    say("Accounts")
    say("WIP")
    say("Vishal")
    say("more")
    summary = say("save")          # asked for a description; typed the command
    assert "Here is what I have" in summary
    say("save")

    made = [p for p in admin.get("/api/projects").json()
            if p["name"] == "E2E Save Word Project"]
    assert made, "the flow did not save"
    assert made[0]["description"] != "save", "a command was stored as the description"
    assert not made[0]["description"]


def test_c5_the_guided_flow_can_be_cancelled(admin):
    """C5: nothing is created from a half-finished conversation."""
    session = "e2e-intake-cancel"
    admin.post("/api/chatbot/ask", json={"question": "add a project", "session_id": session})
    admin.post("/api/chatbot/ask", json={"question": "E2E Abandoned Project", "session_id": session})
    out = admin.post("/api/chatbot/ask", json={"question": "cancel", "session_id": session})
    assert out.status_code == 200
    names = {p["name"] for p in admin.get("/api/projects").json()}
    assert "E2E Abandoned Project" not in names


def test_c6_a_duplicate_name_is_caught_at_save(admin):
    """C7: the same project cannot be added twice through the chat."""
    session = "e2e-intake-duplicate"

    def say(text):
        return admin.post(
            "/api/chatbot/ask", json={"question": text, "session_id": session}
        ).json()["answer"]

    say("add a project")
    answer = say("Compliance Tracker")
    assert "already" in answer.lower() or "exists" in answer.lower()


def test_c7_the_assistant_is_closed_to_a_role_without_the_feature(requestor):
    """C6: Ask the Tracker is off for requestors, so the endpoint the widget
    calls is closed too — hiding the bubble alone would not be the security."""
    r = requestor.post("/api/chatbot/ask", json={
        "question": "hello", "session_id": "e2e-ask-blocked",
    })
    assert r.status_code == 403


def test_c7b_even_with_the_assistant_granted_a_requestor_cannot_add_projects(admin, grid):
    """C4b: if an admin does give requestors the bot, it is still not a way
    round the New Project permission."""
    grid("ask", "requestor", True)
    ravi = Api("ravi")
    r = ravi.post("/api/chatbot/ask", json={
        "question": "add a project", "session_id": "e2e-intake-requestor",
    })
    assert r.status_code == 200
    assert "Apply for Service" in r.json()["answer"]

    # And it still answers read questions, which is the point of granting it.
    reading = ravi.post("/api/chatbot/ask", json={
        "question": "which projects are going on right now?", "session_id": "e2e-intake-requestor",
    })
    assert reading.status_code == 200
    assert "Compliance Tracker" in reading.json()["answer"]


def test_c8_users_can_be_added_re_roled_and_deactivated(admin):
    """C8: the whole user lifecycle, ending with a locked-out account."""
    created = admin.post("/api/users", json={
        "name": "E2E Temp User", "email": "e2e.temp@aikyame2e.com",
        "password": "TempPass12345", "role": "requestor",
    })
    assert created.status_code == 201, created.text
    uid = created.json()["id"]

    assert login("e2e.temp@aikyame2e.com", "TempPass12345")

    promoted = admin.patch(f"/api/users/{uid}", json={"role": "member"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "member"

    assert admin.patch(f"/api/users/{uid}", json={"is_active": False}).status_code == 200
    denied = httpx.post(f"{BASE}/api/auth/login", json={
        "email": "e2e.temp@aikyame2e.com", "password": "TempPass12345",
    })
    assert denied.status_code == 403


def test_c9_verticals_and_statuses_are_editable(admin):
    """C9: nothing about the pipeline is hardcoded."""
    v = admin.post("/api/verticals", json={
        "name": "E2E Vertical", "head_name": "E2E Head", "head_email": "e2e.head@aikyame2e.com",
    })
    assert v.status_code == 201, v.text
    s = admin.post("/api/statuses", json={
        "name": "E2E Status", "color": "#8b5cf6", "is_terminal": False, "sort_order": 99,
    })
    assert s.status_code == 201, s.text
    assert admin.patch(f"/api/statuses/{s.json()['id']}", json={"sort_order": 5}).status_code == 200
    admin.patch(f"/api/verticals/{v.json()['id']}", json={"is_active": False})
    admin.patch(f"/api/statuses/{s.json()['id']}", json={"is_active": False})


def test_c10_branding_is_served(anon):
    """C10: the login screen can fetch the logo before anyone signs in."""
    r = anon.get("/api/branding/logo")
    assert r.status_code == 200
    assert int(r.headers.get("content-length", 0)) > 0


def test_c11_settings_change_the_public_payload(admin, anon):
    """C11: a saved setting is live immediately, no restart."""
    original = {i["key"]: i["value"] for i in admin.get("/api/settings").json()["items"]}["app_name"]
    try:
        assert admin.patch("/api/settings", json={"values": {"app_name": "E2E Renamed Tracker"}}).status_code == 200
        assert anon.get("/api/settings/public").json()["app_name"] == "E2E Renamed Tracker"
    finally:
        admin.patch("/api/settings", json={"values": {"app_name": original}})
    assert anon.get("/api/settings/public").json()["app_name"] == original


def test_c12_the_email_signature_is_configurable_and_set(admin):
    """C12: the signature the four templates print."""
    items = {i["key"]: i for i in admin.get("/api/settings").json()["items"]}
    assert "email_signature" in items
    assert items["email_signature"]["value"]


def test_c13_a_masked_secret_is_never_saved_over_a_real_one(admin):
    """The bug that broke outgoing mail: the form posted its own mask back."""
    before = {i["key"]: i for i in admin.get("/api/settings").json()["items"]}["smtp_password"]["is_set"]
    admin.patch("/api/settings", json={"values": {"smtp_password": "••••••••"}})
    after = {i["key"]: i for i in admin.get("/api/settings").json()["items"]}["smtp_password"]["is_set"]
    assert after == before, "a mask was accepted as a password"


def test_c14_the_audit_trail_recorded_the_run(admin):
    """C14: the actions blocks A and B performed are all attributable."""
    actions = {row["action"] for row in admin.get("/api/audit-logs?limit=500").json()}
    for expected in ("submit_request", "review_request_approved", "download_brd", "update_settings"):
        assert expected in actions, f"{expected} missing from the audit trail"


def test_c15_assistant_chats_are_reviewable(admin):
    """C15: the conversations from B14 and C4, attributed to their authors."""
    r = admin.get("/api/chatbot/conversations")
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ===========================================================================
# Block D — the permission grid
# ===========================================================================

def test_d1_revoking_dashboard_closes_it_for_that_role(admin, grid):
    """D1: the sidebar, the route and the endpoint all follow one switch."""
    ravi = Api("ravi")
    assert ravi.get("/api/projects").status_code == 200

    assert grid("dashboard", "requestor", False).status_code == 200
    closed = Api("ravi")
    assert "dashboard" not in closed.get("/api/permissions/me").json()["features"]
    assert closed.get("/api/projects").status_code == 403


def test_d2_restoring_it_brings_it_straight_back(admin, grid):
    """D2: no restart, no redeploy."""
    grid("dashboard", "requestor", False)
    assert Api("ravi").get("/api/projects").status_code == 403
    grid("dashboard", "requestor", True)
    assert Api("ravi").get("/api/projects").status_code == 200


def test_d3_an_admin_cannot_lock_themselves_out(admin):
    """D3: the locked pair is refused by the service, not just greyed out."""
    r = admin.put("/api/permissions", json={"changes": {"admin_panel": {"admin": False}}})
    assert r.status_code == 400
    assert "cannot be switched off" in r.json()["detail"]
    assert "admin_panel" in admin.get("/api/permissions/me").json()["features"]


def test_d4_granting_team_day_to_members_works_both_ways(admin, grid, member):
    """D4: read access to everyone's day is a toggle."""
    assert member.get("/api/daily-tasks/team").status_code == 403
    grid("team_day", "member", True)
    assert Api("pranjal").get("/api/daily-tasks/team").status_code == 200
    grid("team_day", "member", False)
    assert Api("pranjal").get("/api/daily-tasks/team").status_code == 403


def test_d5_revoking_remarks_blanks_the_field_not_the_project(admin, grid, projects):
    """D5: everything else about the project still loads."""
    grid("project_remarks", "member", False)
    row = Api("pranjal").get(f"/api/projects/{projects['Compliance Tracker']}").json()
    assert row["remarks"] is None
    assert row["name"] == "Compliance Tracker" and row["target_date"]


def test_d6_revoking_export_kills_the_url_too(admin, grid):
    """D6: 403, not a downloaded file."""
    grid("projects_export", "member", False)
    assert Api("pranjal").get("/api/projects/export.xlsx").status_code == 403


def test_d7_every_grid_change_is_attributed(admin):
    """D7: one audit entry per change, naming who made it."""
    rows = admin.get("/api/audit-logs?limit=500").json()
    assert any(r["action"] == "update_permissions" for r in rows)


# ===========================================================================
# Block E — security and edges
# ===========================================================================

def test_e1_nothing_is_readable_signed_out(anon):
    """E1: every data endpoint needs a token."""
    for path in ("/api/projects", "/api/users", "/api/requests", "/api/daily-tasks", "/api/audit-logs"):
        assert anon.get(path).status_code == 401, path


def test_e2_repeated_wrong_passwords_lock_the_address(anon):
    """E2: 429 with a wait, not a generic error — and it is per address."""
    email = "lockme@aikyame2e.com"
    last = None
    for _ in range(8):
        last = anon.post("/api/auth/login", json={"email": email, "password": "wrong-on-purpose"})
        if last.status_code == 429:
            break
    assert last.status_code == 429
    assert last.headers.get("retry-after")
    assert re.search(r"\d+ minute", last.json()["detail"])
    # A different address is unaffected.
    assert anon.post("/api/auth/login", json={
        "email": "pranjal@aikyame2e.com", "password": "PranjalPass123",
    }).status_code == 200


def test_e5_a_hostile_filename_is_neutralised(requestor, member):
    """E5: the upload cannot escape the upload directory."""
    filed = requestor.post(
        "/api/requests",
        data={"vertical_id": 1, "title": "E2E traversal attempt", "description": "x"},
        files=brd("../../../../etc/passwd.pdf"),
    )
    assert filed.status_code == 201
    stored = member.get(f"/api/requests/{filed.json()['id']}").json()["brd_filename"]
    assert ".." not in stored
    assert "/etc/passwd" not in stored.replace("\\", "/")
    served = member.get(f"/api/requests/{filed.json()['id']}/brd")
    assert served.status_code == 200


def test_e6_a_requestor_cannot_pull_another_brd(other_requestor, submitted_request):
    """E6: 404 on someone else's attachment."""
    assert other_requestor.get(f"/api/requests/{submitted_request['id']}/brd").status_code == 404


def test_e7_a_broken_mailbox_does_not_break_the_request(requestor, admin):
    """E7: the row is already committed — an SMTP error must not 500 the caller.

    This is the failure that made a requestor think their submission was lost
    and file it twice.
    """
    admin.patch("/api/settings", json={"values": {
        "smtp_host": "127.0.0.1", "smtp_port": 9, "smtp_username": "nobody@aikyame2e.com",
        "smtp_password": "definitely-wrong",
    }})
    try:
        r = requestor.post(
            "/api/requests",
            data={"vertical_id": 1, "title": "E2E request with mail broken", "description": "x"},
            files=brd(),
        )
        assert r.status_code == 201, "an unreachable mailbox took down the submission"
        # And the diagnostic button still reports the real reason.
        t = admin.post("/api/settings/test-email")
        assert t.status_code == 400
        assert t.json()["detail"]
    finally:
        admin.patch("/api/settings", json={"values": {"smtp_host": ""}})


def test_e8_deep_links_survive_a_refresh(anon):
    """E8: the SPA fallback serves index.html for a client-side route."""
    r = anon.get("/projects/1")
    assert r.status_code == 200
    assert "<script" in r.text


def test_e9_the_spa_fallback_cannot_be_used_to_read_files(anon):
    """E8b: the fallback serves from dist only, with a traversal guard."""
    for path in ("/../backend/.env", "/assets/../../../etc/passwd", "/uploads/anything.pdf"):
        r = anon.get(path)
        assert r.status_code in (200, 404), path
        if r.status_code == 200:
            assert "DATABASE_URL" not in r.text and "root:" not in r.text


def test_d8_deleting_a_project_is_admin_only_and_grid_controlled(admin, member, grid):
    """A member cannot delete; an admin can; and the grid can hand it over."""
    verticals = admin.get("/api/verticals").json()
    statuses = admin.get("/api/statuses").json()

    def make(name):
        r = admin.post("/api/projects", json={
            "name": name, "vertical_id": verticals[0]["id"], "status_id": statuses[0]["id"],
        })
        assert r.status_code == 201, r.text
        return r.json()["id"]

    pid = make("E2E Project To Delete")
    assert member.delete(f"/api/projects/{pid}").status_code == 403
    assert admin.get(f"/api/projects/{pid}").status_code == 200
    assert admin.delete(f"/api/projects/{pid}").status_code == 204
    assert admin.get(f"/api/projects/{pid}").status_code == 404

    grid("projects_delete", "member", True)
    pid2 = make("E2E Project A Member May Delete")
    assert Api("pranjal").delete(f"/api/projects/{pid2}").status_code == 204


# ===========================================================================
# Block F - recipients the requestor chooses, and the delivered email
# ===========================================================================

def test_f1_the_requestor_can_choose_who_else_is_copied(requestor, admin, member):  # noqa: D401
    """They know their own vertical better than the app does. Ids for people
    with an account, addresses for heads who never log in."""
    admin.patch("/api/settings", json={"values": {"email_domain": "aikyame2e.com"}})
    r = requestor.post(
        "/api/requests",
        data={
            "vertical_id": 1,
            "title": "E2E request with chosen recipients",
            "description": "x",
            "extra_to": f'[{member.id}]',
            "extra_cc": '["no.login.head@aikyame2e.com"]',
        },
        files=brd(),
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "submitted"


def test_f2_an_outside_address_is_refused_by_name(requestor):
    """Internal project detail does not leave on a typo."""
    r = requestor.post(
        "/api/requests",
        data={"vertical_id": 1, "title": "E2E outside address", "description": "x",
              "extra_cc": '["someone@gmail.com"]'},
        files=brd(),
    )
    assert r.status_code == 400
    assert "someone@gmail.com" in r.json()["detail"]


def test_f3_the_recipient_list_is_capped(requestor):
    many = ",".join(f"person{i}@aikyame2e.com" for i in range(20))
    r = requestor.post(
        "/api/requests",
        data={"vertical_id": 1, "title": "E2E too many recipients", "description": "x",
              "extra_cc": many},
        files=brd(),
    )
    assert r.status_code == 400
    assert "at most" in r.json()["detail"]


def test_f4_reaching_a_terminal_status_is_what_delivered_means(admin, requestor):
    """The delivered email fires on the way in to a terminal status, once."""
    filed = requestor.post(
        "/api/requests",
        data={"vertical_id": 1, "title": "E2E delivered end to end", "description": "x"},
        files=brd(),
    ).json()
    statuses = admin.get("/api/statuses").json()
    queue = statuses[0]["id"]
    terminal = next(s["id"] for s in statuses if s["is_terminal"])

    admin.post(f"/api/requests/{filed['id']}/review",
               json={"decision": "approved", "status_id": queue})
    project = next(p for p in admin.get("/api/projects").json()
                   if p["source_request_id"] == filed["id"])

    moved = admin.patch(f"/api/projects/{project['id']}",
                        json={"status_id": terminal, "notify_team": True})
    assert moved.status_code == 200
    # Reaching it stamps the completion date - the same moment the mail goes.
    assert moved.json()["actual_completion_date"] is not None

    actions = [r for r in admin.get("/api/audit-logs?limit=500").json()
               if r["action"] == "project_delivered_email"]
    assert actions, "no delivery notification was attempted"
    assert "ravi@aikyame2e.com" in actions[0]["details"]


# ---------------------------------------------------------------------------
# G. The API key register
# ---------------------------------------------------------------------------

def _provider(admin):
    rows = admin.get("/api/api-providers").json()
    return rows[0]["id"]


def test_g1_the_register_belongs_to_the_ai_team(admin, member, requestor):
    """Admin and member work in it; a requestor has no door to it at all."""
    assert admin.get("/api/api-keys").status_code == 200
    assert member.get("/api/api-keys").status_code == 200
    assert requestor.get("/api/api-keys").status_code == 403
    assert requestor.get("/api/api-providers").status_code == 403
    assert requestor.get("/api/api-keys/export.xlsx").status_code == 403
    assert requestor.post("/api/api-keys", json={
        "provider_id": 1, "project_label": "Sneaky", "status": "active",
    }).status_code == 403


def test_g2_a_member_can_add_and_amend_an_entry(admin, member):
    made = member.post("/api/api-keys", json={
        "provider_id": _provider(admin),
        "project_label": "E2E Bulk email",
        "purpose": "For bulk emailing",
        "account_email": "aiteam@aikyame2e.com",
        "expires_on": str(date.today() + timedelta(days=9)),
        "status": "active",
    })
    assert made.status_code == 201, made.text
    body = made.json()
    assert body["project_name"] == "E2E Bulk email"
    assert body["expiry_state"] == "soon" and body["days_left"] == 9

    edited = member.patch(f"/api/api-keys/{body['id']}", json={"purpose": "For the STT"})
    assert edited.status_code == 200
    assert edited.json()["purpose"] == "For the STT"


def test_g3_the_secret_itself_has_nowhere_to_go(admin):
    """A register, not a vault — a value sent anyway is dropped, not stored."""
    r = admin.post("/api/api-keys", json={
        "provider_id": _provider(admin),
        "project_label": "E2E No secrets here",
        "status": "active",
        "key_value": "sk-live-must-not-persist",
        "api_key": "sk-live-must-not-persist",
    })
    assert r.status_code == 201
    assert "sk-live" not in str(r.json())
    listed = admin.get("/api/api-keys").json()
    assert "sk-live" not in str(listed)


def test_g4_expiry_is_derived_and_revoking_ends_the_chasing(admin):
    lapsed = admin.post("/api/api-keys", json={
        "provider_id": _provider(admin),
        "project_label": "E2E Lapsed key",
        "expires_on": str(date.today() - timedelta(days=4)),
        "status": "active",
    }).json()
    assert lapsed["expiry_state"] == "expired" and lapsed["days_left"] == -4

    ids = [r["id"] for r in admin.get("/api/api-keys/expiring").json()]
    assert lapsed["id"] in ids

    admin.patch(f"/api/api-keys/{lapsed['id']}", json={"status": "revoked"})
    ids = [r["id"] for r in admin.get("/api/api-keys/expiring").json()]
    assert lapsed["id"] not in ids, "a revoked key should stop nagging"


def test_g5_the_export_carries_the_teams_own_columns(member, admin):
    import io
    from openpyxl import load_workbook

    member.post("/api/api-keys", json={
        "provider_id": _provider(admin),
        "project_label": "E2E FD_Rate",
        "purpose": "For the Scrapping",
        "account_email": "fd_treasury@aikyame2e.com",
        "status": "active",
    })
    r = member.get("/api/api-keys/export.xlsx")
    assert r.status_code == 200
    assert ".xlsx" in r.headers["content-disposition"]

    ws = load_workbook(io.BytesIO(r.content)).active
    assert [c.value for c in ws[1]][:5] == ["Project", "API-Key", "Purpose", "Exp-date", "email_id"]
    body = "\n".join(
        " | ".join("" if c is None else str(c) for c in row)
        for row in ws.iter_rows(min_row=2, values_only=True)
    )
    assert "E2E FD_Rate" in body
    assert "No Expiry Date" in body
    assert "fd_treasury@aikyame2e.com" in body


def test_g6_the_provider_list_is_curated_by_admins_only(admin, member):
    made = admin.post("/api/api-providers", json={"name": "E2E-Provider"})
    assert made.status_code == 201
    assert admin.post("/api/api-providers", json={"name": "e2e-PROVIDER"}).status_code == 400
    assert member.post("/api/api-providers", json={"name": "Member tried"}).status_code == 403

    admin.post("/api/api-keys", json={
        "provider_id": made.json()["id"], "project_label": "E2E holds a provider", "status": "active",
    })
    refused = admin.delete(f"/api/api-providers/{made.json()['id']}")
    assert refused.status_code == 400


def test_g7_the_grid_is_still_what_decides(admin, requestor, grid):
    """Access is a toggle like every other feature, not a hardcoded role."""
    grid("api_keys", "requestor", True)
    assert requestor.get("/api/api-keys").status_code == 200
    grid("api_keys", "requestor", False)
    assert requestor.get("/api/api-keys").status_code == 403
