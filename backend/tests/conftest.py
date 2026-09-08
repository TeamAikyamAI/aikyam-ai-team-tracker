"""Shared fixtures: an isolated SQLite database per test session, a FastAPI
TestClient, seeded users for every role, and an e-mail spy so nothing ever
leaves the machine during tests.

Run with one command from backend/:  pytest
"""
import os
import sys
import tempfile
from pathlib import Path

# The app reads its configuration at import time, so point it at a throwaway
# database *before* anything under app/ is imported.
_TMP = tempfile.mkdtemp(prefix="aikyam-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["UPLOAD_DIR"] = f"{_TMP}/uploads"
os.environ["JWT_SECRET"] = "test-secret-key-that-is-long-enough-0123456789"
os.environ["APP_ENV"] = "test"
os.environ["LOG_FORMAT"] = "text"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["RUN_SCHEDULER"] = "0"
# Point at a directory that cannot exist, so the SPA fallback stays off during
# tests. Otherwise the suite behaves differently depending on whether someone
# has run `npm run build`: with a dist/ present, every unmatched path returns
# index.html (200) instead of 404, and the routing tests below read that as a
# failure. Serving index.html for an unknown path is correct for a single-page
# app - it just isn't what these tests are checking.
os.environ["STATIC_DIR"] = f"{_TMP}/no-frontend"

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)  # Jinja templates are resolved relative to backend/

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
import app.models  # noqa: E402,F401  (registers every table)
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.vertical import Vertical  # noqa: E402
from app.models.status import Status  # noqa: E402

PASSWORD = "CorrectHorse42!"


@pytest.fixture(scope="session")
def outbox():
    """Every e-mail the app tries to send, as (to, subject, cc, html) tuples."""
    return []


@pytest.fixture(scope="session", autouse=True)
def _patch_email(outbox):
    import app.services.email as email_mod
    import app.routers.service_requests as sr
    import app.routers.settings as settings_router
    import app.services.digest as digest

    # Keep the genuine sender reachable. A test that needs to prove the app
    # survives a broken mailbox has to run the real function - and this fixture
    # replaces the name on the email module itself, so without this there is no
    # way back to it.
    real_send_email = email_mod.send_email

    def fake_send(db, to, subject, html_body, cc=None, reply_to=None, from_display_name=None, **_):
        outbox.append({"to": list(to), "subject": subject, "cc": list(cc or []), "html": html_body,
                       "reply_to": reply_to, "from_name": from_display_name})
        return True

    for mod in (email_mod, sr, settings_router, digest):
        if hasattr(mod, "send_email"):
            mod.send_email = fake_send
    email_mod.real_send_email = real_send_email
    yield


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    # Every route lives under /api; the base_url keeps the tests readable.
    with TestClient(app, base_url="http://testserver/api") as c:
        yield c


@pytest.fixture(scope="session")
def seed():
    """Admin -> (member reports to admin) ; two requestors ; one vertical ; two statuses."""
    db = SessionLocal()
    admin = User(name="Ada Admin", email="admin@example.com", password_hash=hash_password(PASSWORD),
                 role="admin", is_active=True, external_manager_email="management@example.com")
    member = User(name="Max Member", email="member@example.com", password_hash=hash_password(PASSWORD),
                  role="member", is_active=True)
    req1 = User(name="Rita Requestor", email="rita@example.com", password_hash=hash_password(PASSWORD),
                role="requestor", is_active=True)
    req2 = User(name="Raj Requestor", email="raj@example.com", password_hash=hash_password(PASSWORD),
                role="requestor", is_active=True)
    disabled = User(name="Dan Disabled", email="disabled@example.com", password_hash=hash_password(PASSWORD),
                    role="member", is_active=False)
    db.add_all([admin, member, req1, req2, disabled])
    db.commit()
    member.reports_to_id = admin.id
    vertical = Vertical(name="Operations", head_name="Olivia Head", head_email="olivia@example.com", is_active=True)
    s1 = Status(name="In queue", sort_order=1, is_active=True, color="#94a3b8")
    s2 = Status(name="Live", sort_order=4, is_active=True, color="#22c55e")
    db.add_all([vertical, s1, s2])
    db.commit()
    ids = {
        "admin": admin.id, "member": member.id, "req1": req1.id, "req2": req2.id, "disabled": disabled.id,
        "vertical": vertical.id, "status_queue": s1.id, "status_live": s2.id,
    }
    db.close()
    return ids


@pytest.fixture(scope="session")
def auth(client, seed):
    """auth("admin") -> Authorization header for that seeded person."""
    emails = {"admin": "admin@example.com", "member": "member@example.com",
              "req1": "rita@example.com", "req2": "raj@example.com"}
    cache: dict[str, dict] = {}

    def _headers(who: str) -> dict:
        if who not in cache:
            r = client.post("/auth/login", json={"email": emails[who], "password": PASSWORD})
            assert r.status_code == 200, r.text
            cache[who] = {"Authorization": f"Bearer {r.json()['access_token']}"}
        return cache[who]

    return _headers


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _reset_login_counters():
    from app.routers.auth import reset_rate_limits
    reset_rate_limits()
    yield
    reset_rate_limits()
