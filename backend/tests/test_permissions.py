"""The admin-editable access grid.

The point of these tests is that the grid is enforced on the server, not just
reflected in the menu - a role that loses a feature must get a 403 from the API
even though it can still type the URL.
"""
import pytest

from app.models.role_permission import RolePermission
from app.services import permissions as perms


@pytest.fixture(autouse=True)
def _clean_grid(db):
    """Every test starts from the shipped defaults."""
    db.query(RolePermission).delete()
    db.commit()
    yield
    db.query(RolePermission).delete()
    db.commit()


def test_defaults_match_what_the_team_expects(db):
    assert perms.is_allowed(db, "requestor", "dashboard") is True
    assert perms.is_allowed(db, "requestor", "project_remarks") is False
    assert perms.is_allowed(db, "requestor", "admin_panel") is False
    assert perms.is_allowed(db, "member", "my_day") is True
    assert perms.is_allowed(db, "member", "team_day") is False
    assert perms.is_allowed(db, "admin", "team_day") is True


def test_me_endpoint_lists_only_permitted_features(client, auth):
    mine = client.get("/permissions/me", headers=auth("req1")).json()
    assert mine["role"] == "requestor"
    assert "dashboard" in mine["features"]
    assert "admin_panel" not in mine["features"]
    assert "my_day" not in mine["features"]


def test_only_admins_can_read_or_change_the_grid(client, auth):
    assert client.get("/permissions", headers=auth("member")).status_code == 403
    assert client.get("/permissions", headers=auth("req1")).status_code == 403
    assert client.get("/permissions", headers=auth("admin")).status_code == 200


def test_revoking_a_feature_is_enforced_by_the_api(client, auth):
    """Turn the dashboard off for requestors and the endpoint must refuse."""
    assert client.get("/projects", headers=auth("req1")).status_code == 200

    r = client.put("/permissions", headers=auth("admin"),
                   json={"changes": {"dashboard": {"requestor": False}}})
    assert r.status_code == 200, r.text
    assert client.get("/projects", headers=auth("req1")).status_code == 403

    client.put("/permissions", headers=auth("admin"),
               json={"changes": {"dashboard": {"requestor": True}}})
    assert client.get("/projects", headers=auth("req1")).status_code == 200


def test_granting_a_feature_is_enforced_too(client, auth):
    """A member has no Audit Trail by default; granting it must actually work."""
    assert client.get("/audit-logs", headers=auth("member")).status_code == 403
    client.put("/permissions", headers=auth("admin"),
               json={"changes": {"audit_trail": {"member": True}}})
    assert client.get("/audit-logs", headers=auth("member")).status_code == 200


def test_admin_cannot_lock_themselves_out_of_the_admin_panel(client, auth, db):
    r = client.put("/permissions", headers=auth("admin"),
                   json={"changes": {"admin_panel": {"admin": False}}})
    assert r.status_code == 400
    assert "cannot be switched off" in r.json()["detail"]
    assert perms.is_allowed(db, "admin", "admin_panel") is True
    assert client.get("/permissions", headers=auth("admin")).status_code == 200


def test_unknown_feature_or_role_is_rejected(client, auth):
    assert client.put("/permissions", headers=auth("admin"),
                      json={"changes": {"not_a_feature": {"admin": True}}}).status_code == 400
    assert client.put("/permissions", headers=auth("admin"),
                      json={"changes": {"dashboard": {"wizard": True}}}).status_code == 400


def test_matrix_reports_locked_pairs(client, auth):
    body = client.get("/permissions", headers=auth("admin")).json()
    admin_panel = next(f for f in body["features"] if f["key"] == "admin_panel")
    assert admin_panel["roles"]["admin"]["locked"] is True
    assert admin_panel["roles"]["member"]["locked"] is False
    assert [r["key"] for r in body["roles"]] == ["admin", "member", "requestor"]


def test_requestor_never_sees_internal_remarks(client, seed, auth):
    body = {"name": "Remarks check", "vertical_id": seed["vertical"],
            "status_id": seed["status_queue"], "remarks": "vertical head keeps changing scope"}
    pid = client.post("/projects", headers=auth("admin"), json=body).json()["id"]

    team_view = next(p for p in client.get("/projects", headers=auth("member")).json() if p["id"] == pid)
    assert team_view["remarks"] == "vertical head keeps changing scope"

    their_view = next(p for p in client.get("/projects", headers=auth("req1")).json() if p["id"] == pid)
    assert their_view["remarks"] is None
    assert their_view["name"] == "Remarks check"  # everything else is still there


def test_directory_gives_names_without_emails(client, auth):
    r = client.get("/users/directory", headers=auth("req1"))
    assert r.status_code == 200
    row = r.json()[0]
    assert set(row) == {"id", "name"}
    # the full directory stays team-only
    assert client.get("/users", headers=auth("req1")).status_code == 403
