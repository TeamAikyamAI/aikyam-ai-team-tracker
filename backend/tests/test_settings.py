def test_public_settings_need_no_login_and_expose_only_public_keys(client):
    r = client.get("/settings/public")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"app_name", "org_name", "login_footer", "email_domain",
                         "chatbot_enabled", "chatbot_name", "chatbot_greeting", "chatbot_suggestions"}
    assert "smtp" not in str(body).lower()


def test_admin_only(client, seed, auth):
    assert client.get("/settings", headers=auth("member")).status_code == 403
    assert client.patch("/settings", headers=auth("member"), json={"values": {"app_name": "x"}}).status_code == 403


def test_secrets_are_write_only(client, seed, auth):
    """The SMTP password moved to .env, so this covers the remaining secret."""
    r = client.patch("/settings", headers=auth("admin"), json={"values": {"anthropic_api_key": "hunter2hunter2"}})
    assert r.status_code == 200, r.text
    items = client.get("/settings", headers=auth("admin")).json()["items"]
    key = next(i for i in items if i["key"] == "anthropic_api_key")
    assert key["type"] == "secret" and key["value"] is None and key["is_set"] is True
    assert "hunter2" not in client.get("/settings", headers=auth("admin")).text
    # a blank save keeps the stored secret
    client.patch("/settings", headers=auth("admin"), json={"values": {"anthropic_api_key": ""}})
    items = client.get("/settings", headers=auth("admin")).json()["items"]
    assert next(i for i in items if i["key"] == "anthropic_api_key")["is_set"] is True


def test_validation_rejects_unknown_key_bad_int_bad_select(client, seed, auth):
    assert client.patch("/settings", headers=auth("admin"), json={"values": {"not_a_key": 1}}).status_code == 400
    assert client.patch("/settings", headers=auth("admin"), json={"values": {"session_hours": "lots"}}).status_code == 400
    assert client.patch("/settings", headers=auth("admin"), json={"values": {"ai_provider": "openai"}}).status_code == 400


def test_change_is_live_immediately(client, seed, auth):
    r = client.patch("/settings", headers=auth("admin"), json={"values": {"app_name": "Renamed Tracker"}})
    assert r.status_code == 200
    assert client.get("/settings/public").json()["app_name"] == "Renamed Tracker"
    assert client.get("/health").json()["app"] == "Renamed Tracker"
    client.patch("/settings", headers=auth("admin"), json={"values": {"app_name": "Aikyam AI Team Tracker"}})


def test_test_email_requires_smtp_host(client, seed, auth, outbox, monkeypatch):
    from app.services import settings as cfg

    # Clearing the stored host falls back to the .env value, and a developer
    # machine may well have SMTP_HOST filled in there. Blank both so the test
    # asserts the behaviour rather than the contents of someone's .env.
    monkeypatch.setattr(cfg.env, "smtp_host", "")
    client.patch("/settings", headers=auth("admin"), json={"values": {"smtp_host": ""}})
    assert client.post("/settings/test-email", headers=auth("admin")).status_code == 400
    client.patch("/settings", headers=auth("admin"), json={"values": {"smtp_host": "smtp.example.com"}})
    outbox.clear()
    r = client.post("/settings/test-email", headers=auth("admin"))
    assert r.status_code == 200, r.text
    assert outbox and outbox[-1]["to"] == ["admin@example.com"]


# --------------------------------------------------------------------------
# A broken mailbox must not break the app.
#
# Found in real use: Office 365 rejected the SMTP login and /auth/forgot-password
# returned a 500, because send_email let the exception escape. The same fault
# would have hit a service request AFTER it was already saved, so the requestor
# would have been told their submission failed when it had not.
# --------------------------------------------------------------------------

import smtplib

import pytest


@pytest.fixture
def broken_smtp(db, monkeypatch):
    """Real SMTP settings that fail to authenticate, like a wrong password."""
    from app.services import settings as cfg
    import app.services.email as email_mod

    cfg.set_many(db, {"smtp_host": "smtp.example.com", "smtp_port": 587})
    monkeypatch.setattr(cfg.env, "smtp_username", "bot@example.com")
    monkeypatch.setattr(cfg.env, "smtp_password", "wrong")

    class _Boom:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, *a): raise smtplib.SMTPAuthenticationError(535, b"5.7.139 Authentication unsuccessful")
        def sendmail(self, *a): pass

    monkeypatch.setattr(email_mod.smtplib, "SMTP", _Boom)
    # The conftest spy replaced send_email everywhere; put the genuine one back
    # on the routers under test so the SMTP failure actually happens.
    import app.routers.auth as auth_router
    import app.routers.service_requests as sr
    for mod in (auth_router, sr):
        monkeypatch.setattr(mod, "send_email", email_mod.real_send_email)
    yield
    cfg.set_many(db, {"smtp_host": ""})


def test_forgot_password_survives_a_broken_mailbox(client, seed, auth, broken_smtp):
    r = client.post("/auth/forgot-password", json={"email": "member@example.com"})
    assert r.status_code == 200, r.text


def test_forgot_password_still_issues_the_token_when_email_fails(client, seed, db, broken_smtp):
    from app.models.password_reset import PasswordResetToken
    before = db.query(PasswordResetToken).count()
    client.post("/auth/forgot-password", json={"email": "member@example.com"})
    db.expire_all()
    assert db.query(PasswordResetToken).count() == before + 1


def test_submitting_a_request_survives_a_broken_mailbox(client, seed, auth, db, broken_smtp):
    """The worst version of this bug: the request is saved, then the 500 makes
    the requestor think it was lost and submit it again."""
    from app.models.service_request import ServiceRequest
    before = db.query(ServiceRequest).count()
    r = client.post(
        "/requests",
        headers=auth("req1"),
        data={"vertical_id": seed["vertical"], "title": "Survives bad SMTP", "description": "x"},
        files={"brd_file": ("brd.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert r.status_code == 201, r.text
    db.expire_all()
    assert db.query(ServiceRequest).count() == before + 1


def test_test_email_still_reports_the_real_smtp_error(client, auth, db, monkeypatch):
    """The one place the error must surface: Admin > Settings > Send test email."""
    from app.services import settings as cfg
    import app.services.email as email_mod
    import app.routers.settings as settings_router

    cfg.set_many(db, {"smtp_host": "smtp.example.com", "smtp_port": 587})
    monkeypatch.setattr(cfg.env, "smtp_username", "bot@example.com")
    monkeypatch.setattr(cfg.env, "smtp_password", "wrong")

    class _Boom:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, *a): raise smtplib.SMTPAuthenticationError(535, b"5.7.139 Authentication unsuccessful")
        def sendmail(self, *a): pass

    monkeypatch.setattr(email_mod.smtplib, "SMTP", _Boom)
    monkeypatch.setattr(settings_router, "send_email", email_mod.real_send_email)

    r = client.post("/settings/test-email", headers=auth("admin"))
    assert r.status_code == 400
    assert "Authentication unsuccessful" in r.json()["detail"]
    cfg.set_many(db, {"smtp_host": ""})


# --------------------------------------------------------------------------
# The Settings form must never overwrite a stored password with its own mask.
#
# What went wrong in real use: saving the form for an unrelated change (the
# upload limit) stored the literal string "******" as the SMTP password. Every
# email then failed with "credentials were incorrect" and nothing said why.
# --------------------------------------------------------------------------

def test_smtp_settings_stay_editable_from_the_admin_screen(client, auth, db):
    r = client.patch("/settings", headers=auth("admin"), json={"values": {
        "smtp_host": "smtp.office365.com",
        "smtp_username": "ai.automation@aikyamcap.com",
        "smtp_password": "a-real-password",
        "smtp_from_name": "Aikyam AI Team",
    }})
    assert r.status_code == 200, r.text
    from app.services import settings as cfg
    assert cfg.get(db, "smtp_username") == "ai.automation@aikyamcap.com"
    assert cfg.get(db, "smtp_password") == "a-real-password"
    assert cfg.get(db, "smtp_from_name") == "Aikyam AI Team"


@pytest.mark.parametrize("mask", ["******", "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022", "  ****  ", "\u25cf\u25cf\u25cf\u25cf"])
def test_a_masked_password_never_replaces_the_real_one(client, auth, db, mask):
    from app.services import settings as cfg
    cfg.set_many(db, {"smtp_password": "the-real-password"})

    r = client.patch("/settings", headers=auth("admin"),
                     json={"values": {"smtp_password": mask}})
    assert r.status_code == 200, r.text
    assert cfg.get(db, "smtp_password") == "the-real-password"


def test_saving_an_unrelated_setting_leaves_the_password_alone(client, auth, db):
    """The exact sequence that broke it: change the upload limit, save the form."""
    from app.services import settings as cfg
    cfg.set_many(db, {"smtp_password": "still-here"})
    r = client.patch("/settings", headers=auth("admin"),
                     json={"values": {"max_brd_upload_mb": 38, "smtp_password": "******"}})
    assert r.status_code == 200, r.text
    assert cfg.get(db, "smtp_password") == "still-here"
    assert cfg.get(db, "max_brd_upload_mb") == 38


def test_a_real_password_made_of_other_characters_still_saves(client, auth, db):
    """Guard the guard: only mask characters are ignored."""
    from app.services import settings as cfg
    client.patch("/settings", headers=auth("admin"),
                 json={"values": {"smtp_password": "P*ssw0rd*2026"}})
    assert cfg.get(db, "smtp_password") == "P*ssw0rd*2026"


# --------------------------------------------------------------------------
# Email signature
# --------------------------------------------------------------------------

def test_signature_defaults_to_the_team_and_is_editable(client, auth, db):
    from app.services import settings as cfg
    items = {i["key"]: i for i in client.get("/settings", headers=auth("admin")).json()["items"]}
    assert items["email_signature"]["group"] == "Email"
    assert cfg.get(db, "email_signature") == "AI Team"

    client.patch("/settings", headers=auth("admin"),
                 json={"values": {"email_signature": "AI & Automation Team\nAikyam Capital"}})
    assert cfg.get(db, "email_signature") == "AI & Automation Team\nAikyam Capital"
    cfg.set_many(db, {"email_signature": "AI Team"})


def test_the_signature_appears_in_every_automated_email(client, seed, auth, db, outbox):
    from app.services import settings as cfg
    cfg.set_many(db, {"smtp_host": "smtp.example.com", "email_signature": "AI Team"})

    outbox.clear()
    client.post("/auth/forgot-password", json={"email": "member@example.com"})
    assert "AI Team" in outbox[-1]["html"]

    outbox.clear()
    client.post("/requests", headers=auth("req1"),
                data={"vertical_id": seed["vertical"], "title": "Signed request", "description": "x"},
                files={"brd_file": ("brd.pdf", b"%PDF-1.4", "application/pdf")})
    assert "AI Team" in outbox[-1]["html"]

    outbox.clear()
    client.post("/settings/digest-preview", headers=auth("admin"))
    assert outbox and all("AI Team" in m["html"] for m in outbox)
    cfg.set_many(db, {"smtp_host": ""})
