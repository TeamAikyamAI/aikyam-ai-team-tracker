# End-to-end acceptance suite

Two suites that between them run most of the release run sheet without a human
clicking anything.

| Suite | What it is | Count |
|---|---|---|
| `test_api_e2e.py` | Real HTTP calls to a running server, one signed-in client per role | 67 |
| `ui/run.mjs` | A real Chromium browser driving the built SPA, one browser context per role | 21 |

They run against a **throwaway database**, never the live one. Every test that
changes a setting or a permission puts it back.

The existing `backend/tests/` suite (104 tests, SQLite, in-process) still runs
the way it always did — this is in addition to it, not a replacement. The
difference is that this one exercises Postgres, the middleware, the SPA static
fallback and the actual browser, which is where SQLite and a TestClient can
quietly disagree with production.

---

## What is deliberately NOT automated

Nine checks on the run sheet still need a person, because no test can see them:

1. A real email arriving in a real Office 365 inbox. The suite proves the mail
   is composed with the right recipients, CC, reply-to and signature, and that a
   broken mailbox never takes down the request that triggered it — but not
   delivery.
2. The weekly digest landing with the right manager.
3. A password-reset link opened from an actual inbox.
4. Whether the branding logo, spacing and colours look right.
5. `alembic upgrade head` against the production database.
6. Anything about the host: HTTPS, backups, the machine staying awake.

---

## Running it on a Linux box (how it was built)

```bash
./reset.sh        # drops and rebuilds the test DB, seeds it, starts the server
pytest -q         # the API suite
cd ui && node run.mjs
```

or `./run_all.sh` for all three suites and a single verdict.

`reset.sh` assumes a local Postgres, a `tracker` role and a venv at
`/root/tvenv`. Change the paths at the top if yours differ.

## Running it on the Windows dev machine

`reset.sh` is a bash script and will not run as-is. The equivalent, from
`backend\`, using a scratch database created in pgAdmin (call it
`aikyam_tracker_e2e` — **not** the real one):

```bat
set DATABASE_URL=postgresql+psycopg2://postgres:YOURPASSWORD@localhost:5432/aikyam_tracker_e2e
set JWT_SECRET=e2e-only-secret-at-least-32-characters-long-xxxxx
set APP_ENV=development
set UPLOAD_DIR=..\e2e\uploads
set STATIC_DIR=..\frontend\dist
set RUN_SCHEDULER=0
set SMTP_HOST=

venv\Scripts\python -m alembic upgrade head
venv\Scripts\python ..\e2e\seed_e2e.py
venv\Scripts\python -m uvicorn app.main:app --port 8099
```

Then in a second terminal:

```bat
cd e2e
..\backend\venv\Scripts\python -m pytest -q
cd ui && npm install && node run.mjs
```

Two things to get right:

- The SPA has to be built with a **relative** API base, or the browser suite
  talks to :8002 instead of :8099:
  `cd frontend && set VITE_API_BASE_URL= && npx vite build`
- Drop and recreate the scratch database between full runs. The suite creates
  projects and users with fixed names, so a second run against a dirty database
  reports failures that are really leftovers.

---

## The accounts it seeds

| Login | Role | Notes |
|---|---|---|
| `naman@aikyame2e.com` | Admin | top of the chain, external manager set |
| `aiteam@aikyame2e.com` | Admin | reports to Naman |
| `pranjal@aikyame2e.com` | Member | reports to Naman |
| `ravi@aikyame2e.com` | Requestor | Automation vertical |
| `meera@aikyame2e.com` | Requestor | Accounts vertical |
| `lockme@aikyame2e.com` | Requestor | used only by the lockout test |

Passwords are in `seed_e2e.py`. They are throwaway values for a throwaway
database and must never be reused anywhere real.

`.test` addresses are deliberately avoided — the email validator rejects
special-use domains, so every login would 422.

---

## Reading a failure

Each test's docstring names the run-sheet id it covers (`A4`, `D3`, `E7`…), so a
red line maps to a line on the sheet. The browser suite also writes screenshots
to `ui/shots/` and a machine-readable `ui/results.json`.
