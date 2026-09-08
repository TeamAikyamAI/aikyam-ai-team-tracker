"""Shared fixtures for the end-to-end API suite.

These tests talk to a REAL running server over HTTP, against a throwaway
Postgres database seeded by seed_e2e.py — not the in-process TestClient the
unit suite uses. That is deliberate: it exercises the middleware, the SPA
static fallback and the same Postgres engine production runs on, which is
where the unit suite's SQLite can quietly disagree.
"""
import os

import httpx
import pytest

BASE = os.environ.get("E2E_BASE", "http://127.0.0.1:8099")

ACCOUNTS = {
    "naman": ("naman@aikyame2e.com", "NamanPass123", "admin"),
    "aiteam": ("aiteam@aikyame2e.com", "AiteamPass123", "admin"),
    "pranjal": ("pranjal@aikyame2e.com", "PranjalPass123", "member"),
    "ravi": ("ravi@aikyame2e.com", "RaviPass123", "requestor"),
    "meera": ("meera@aikyame2e.com", "MeeraPass123", "requestor"),
}


def login(email: str, password: str) -> str:
    r = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


class Api:
    """A signed-in HTTP client. Thin on purpose — the tests should read as
    'this role called this endpoint and got this status'."""

    def __init__(self, who: str):
        email, password, self.role = ACCOUNTS[who]
        self.email = email
        self.who = who
        self.token = login(email, password)
        self.http = httpx.Client(
            base_url=BASE,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=60,
            follow_redirects=False,
        )
        self.id = self.http.get("/api/auth/me").json()["id"]

    def get(self, path, **kw):
        return self.http.get(path, **kw)

    def post(self, path, **kw):
        return self.http.post(path, **kw)

    def patch(self, path, **kw):
        return self.http.patch(path, **kw)

    def put(self, path, **kw):
        return self.http.put(path, **kw)

    def delete(self, path, **kw):
        return self.http.delete(path, **kw)


@pytest.fixture(scope="session")
def anon():
    with httpx.Client(base_url=BASE, timeout=30, follow_redirects=False) as c:
        yield c


@pytest.fixture(scope="session")
def admin():
    return Api("aiteam")


@pytest.fixture(scope="session")
def head():
    """The top of the reporting chain — admin, reports to nobody inside the app."""
    return Api("naman")


@pytest.fixture(scope="session")
def member():
    return Api("pranjal")


@pytest.fixture(scope="session")
def requestor():
    return Api("ravi")


@pytest.fixture(scope="session")
def other_requestor():
    return Api("meera")


@pytest.fixture(scope="session")
def projects(admin):
    """Name -> project id, for the seeded projects."""
    rows = admin.get("/api/projects").json()
    return {p["name"]: p["id"] for p in rows}


@pytest.fixture
def grid(admin):
    """Flip permission pairs and put every one of them back afterwards."""
    original = {}

    def flip(feature: str, role: str, allowed: bool):
        if (feature, role) not in original:
            current = admin.get("/api/permissions").json()
            for row in current["features"] if isinstance(current, dict) else current:
                if row["key"] == feature:
                    original[(feature, role)] = row["roles"][role]["allowed"]
                    break
        r = admin.put("/api/permissions", json={"changes": {feature: {role: allowed}}})
        return r

    yield flip

    for (feature, role), was in original.items():
        admin.put("/api/permissions", json={"changes": {feature: {role: was}}})
