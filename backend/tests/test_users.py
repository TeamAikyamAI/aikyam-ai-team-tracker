from tests.conftest import PASSWORD


def test_requestor_cannot_list_users(client, seed, auth):
    assert client.get("/users", headers=auth("req1")).status_code == 403


def test_member_can_list_users(client, seed, auth):
    r = client.get("/users", headers=auth("member"))
    assert r.status_code == 200
    assert {u["email"] for u in r.json()} >= {"admin@example.com", "member@example.com"}


def test_only_admin_creates_users(client, seed, auth):
    body = {"name": "New", "email": "new@example.com", "password": PASSWORD, "role": "member"}
    assert client.post("/users", headers=auth("member"), json=body).status_code == 403
    r = client.post("/users", headers=auth("admin"), json=body)
    assert r.status_code == 201, r.text
    assert "password_hash" not in r.json()


def test_create_rejects_bad_role_and_short_password(client, seed, auth):
    r = client.post("/users", headers=auth("admin"),
                    json={"name": "X", "email": "x1@example.com", "password": PASSWORD, "role": "superuser"})
    assert r.status_code == 400
    r = client.post("/users", headers=auth("admin"),
                    json={"name": "X", "email": "x2@example.com", "password": "short", "role": "member"})
    assert r.status_code == 400


def test_patch_password_actually_changes_login(client, seed, auth):
    uid = seed["req2"]
    r = client.patch(f"/users/{uid}", headers=auth("admin"), json={"password": "AnotherGoodPass99"})
    assert r.status_code == 200, r.text
    assert client.post("/auth/login", json={"email": "raj@example.com", "password": "AnotherGoodPass99"}).status_code == 200
    # put it back so other tests keep working
    client.patch(f"/users/{uid}", headers=auth("admin"), json={"password": PASSWORD})


def test_patch_email_must_be_unique(client, seed, auth):
    r = client.patch(f"/users/{seed['member']}", headers=auth("admin"), json={"email": "admin@example.com"})
    assert r.status_code == 400


def test_last_admin_cannot_be_demoted_or_disabled(client, seed, auth):
    aid = seed["admin"]
    assert client.patch(f"/users/{aid}", headers=auth("admin"), json={"role": "member"}).status_code == 400
    assert client.patch(f"/users/{aid}", headers=auth("admin"), json={"is_active": False}).status_code == 400
