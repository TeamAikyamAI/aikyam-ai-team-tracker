"""Production plumbing: /api prefix, health, headers, request ids, password reset."""
import re

from tests.conftest import PASSWORD


def test_everything_lives_under_api(client, seed):
    assert client.get("http://testserver/auth/me").status_code == 404
    assert client.get("/auth/me").status_code == 401
    assert client.get("http://testserver/api/openapi.json").status_code == 200


def test_deep_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["version"]
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["scheduler"] in ("running", "disabled", "stopped")
    assert "smtp_configured" in body["checks"]


def test_security_headers_and_request_id(client):
    r = client.get("/settings/public", headers={"X-Request-ID": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "referrer-policy" in r.headers
    r2 = client.get("/settings/public")
    assert re.fullmatch(r"[0-9a-f]{32}", r2.headers["x-request-id"])


def test_forgot_password_is_uniform_and_sends_link(client, seed, auth, outbox):
    client.patch("/settings", headers=auth("admin"),
                 json={"values": {"smtp_host": "smtp.example.com", "app_base_url": "https://tracker.example.com/"}})
    outbox.clear()
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    known = client.post("/auth/forgot-password", json={"email": "RITA@example.com"})
    assert unknown.status_code == known.status_code == 200
    assert unknown.json() == known.json()  # no account enumeration
    assert len(outbox) == 1 and outbox[0]["to"] == ["rita@example.com"]
    link = re.search(r'href="(https://tracker\.example\.com/reset-password\?token=[^"]+)"', outbox[0]["html"])
    assert link, outbox[0]["html"]
    token = link.group(1).split("token=")[1]

    # too short -> rejected, token still usable
    assert client.post("/auth/reset-password", json={"token": token, "password": "short"}).status_code == 400
    ok = client.post("/auth/reset-password", json={"token": token, "password": "BrandNewPassword77"})
    assert ok.status_code == 200, ok.text
    assert client.post("/auth/login", json={"email": "rita@example.com", "password": "BrandNewPassword77"}).status_code == 200
    # one-time use
    assert client.post("/auth/reset-password", json={"token": token, "password": "AnotherOne12345"}).status_code == 400
    assert client.post("/auth/reset-password", json={"token": "garbage", "password": "AnotherOne12345"}).status_code == 400
    # restore for the other tests
    client.patch(f"/users/{seed['req1']}", headers=auth("admin"), json={"password": PASSWORD})


def test_expired_reset_token_rejected(client, seed, db):
    from datetime import datetime, timedelta, timezone
    from app.models.password_reset import PasswordResetToken
    from app.routers.auth import _hash_token
    db.add(PasswordResetToken(user_id=seed["req2"], token_hash=_hash_token("old-token"),
                              expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
    db.commit()
    r = client.post("/auth/reset-password", json={"token": "old-token", "password": "AnotherOne12345"})
    assert r.status_code == 400
