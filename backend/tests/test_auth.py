from tests.conftest import PASSWORD


def test_login_returns_token_and_me(client, seed):
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"
    assert me.json()["role"] == "admin"


def test_login_is_case_insensitive_on_email(client, seed):
    r = client.post("/auth/login", json={"email": "Admin@Example.com", "password": PASSWORD})
    assert r.status_code == 200


def test_wrong_password_rejected(client, seed):
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "nope-nope-nope"})
    assert r.status_code == 401


def test_disabled_account_rejected(client, seed):
    r = client.post("/auth/login", json={"email": "disabled@example.com", "password": PASSWORD})
    assert r.status_code == 403


def test_lockout_after_configured_failures(client, seed, auth):
    # Read the live threshold so the test follows whatever the admin configured.
    items = client.get("/settings", headers=auth("admin")).json()["items"]
    max_attempts = next(i["value"] for i in items if i["key"] == "login_max_attempts")
    for _ in range(max_attempts):
        assert client.post("/auth/login", json={"email": "raj@example.com", "password": "wrong"}).status_code == 401
    r = client.post("/auth/login", json={"email": "raj@example.com", "password": PASSWORD})
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_no_token_is_401(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/projects").status_code == 401
