# Aikyam AI Team Tracker

Production project tracker for Aikyam Capital's AI & Automation team — projects
tagged by business vertical, weekly Plan/Progress/Problem updates, automated
weekly email reporting up the reporting chain, an AI-assisted quick-fill and
Q&A, and the vertical-request/BRD intake workflow.

This runs entirely on your own machine — no Docker, no cloud dependency
(other than optional AI/email). You already have PostgreSQL + pgAdmin
installed, which is what it uses.

**Ports:** backend on `8002`, frontend on `5180` — deliberately not the usual
`8000`/`5173` defaults, so this never clashes with another project already
running on your machine. If `8002` or `5180` are ever taken too, change them
in two places: the `--port` flag when starting the backend (and
`FRONTEND_ORIGIN` in `backend/.env`) plus `port` in `frontend/vite.config.ts`
(and `VITE_API_BASE_URL` in `frontend/.env`).

**Every API route lives under `/api`** (`http://localhost:8002/api/...`);
interactive docs at `http://localhost:8002/api/docs`, health at
`http://localhost:8002/api/health`. In production the backend also serves the
built frontend, so one port serves the whole app (see *Going to production*).

## One-time setup

### 1. Create the database

Open pgAdmin, connect to your local Postgres server, and create a new
database — right-click **Databases > Create > Database**, name it
`aikyam_ai_tracker` (or anything you like, just remember it for step 3).

### 2. Backend

Open a terminal in the `backend/` folder.

```
python -m venv venv
venv\Scripts\activate          (Windows)  -- or: source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:
- `DATABASE_URL` — replace `YOUR_PASSWORD` and the database name with what you
  set up in step 1 (this is your real Postgres via pgAdmin, e.g.
  `postgresql+psycopg2://postgres:mypassword@localhost:5432/aikyam_ai_tracker`)
- `JWT_SECRET` — a random string of at least 32 characters. Generate one with
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`. The app
  refuses to start with a placeholder value.
- `SMTP_*` — the shared automation mailbox that will send weekly digest and
  request-notification emails (leave blank for now if you're not ready to
  wire up email yet — the app runs fine without it, emails just won't send)
- `ANTHROPIC_API_KEY` — optional, enables AI Quick-Fill and Ask-the-Tracker.
  Without it those features still work but fall back to plainer output /
  a "not configured" message instead of erroring.

Then run the migrations and the one-time seed script:

```
alembic upgrade head
python -m scripts.seed
```

The seed script will interactively ask you to create the first admin login
(you), and optionally a second user (e.g. Pranjal) who reports to you — it
also creates a starting set of verticals (Broking & Clearing, Accounts,
Stressed Asset Management, Asset Management) and the delivery pipeline
statuses (In queue → WIP → UAT → Live). All of this — verticals, statuses, who reports to whom,
roles — is editable afterwards from the Admin panel in the app; nothing is
hardcoded, the seed script just saves you starting from a completely empty
database.

Start the backend:

```
uvicorn app.main:app --reload --port 8002
```

It runs on `http://localhost:8002`. Visit `http://localhost:8002/api/docs`
for the interactive API docs.

### 4. Bring in the existing project list (optional, one-time)

The team's `Weekly_Update.xlsx` (one sheet per stage: In queue / WIP / UAT /
Live) imports straight into the tracker:

```
python scripts/import_excel.py data/Weekly_Update.xlsx --dry-run   # shows the plan
python scripts/import_excel.py data/Weekly_Update.xlsx             # does it
```

It is safe to run twice — projects already in the tracker are skipped, as are
duplicate rows inside the workbook. Rows land under an **Unassigned** vertical
(pick a different one with `--vertical "Broking & Clearing"`); a row whose
Status cell says something more specific than its sheet ("confirmation
awaiting from the team") keeps that text in the project's Remarks. Afterwards,
set owners and the real vertical from the dashboard's Edit dialog.

The reverse direction is the **Export Excel** button on the dashboard: every
project, one sheet per status, in the same seven columns as the original file
plus vertical, owners and target date.

### 3. Frontend

Open a second terminal in the `frontend/` folder.

```
npm install
```

Copy `.env.example` to `.env` (the default `VITE_API_BASE_URL=http://localhost:8002`
is already correct if you used the default backend port above).

```
npm run dev
```

It runs on `http://localhost:5180` — open that in your browser and log in
with the admin account you created in the seed step.

## Running it day to day

Two terminals, same two commands:

```
cd backend  && venv\Scripts\activate && uvicorn app.main:app --reload --port 8002
cd frontend && npm run dev
```

## Tests

```
cd backend && venv\Scripts\activate && pytest
```

One command, no services needed: the suite spins up a throwaway SQLite
database and a fake mail outbox, then exercises login and lockout, roles and
permissions, the BRD intake flow (upload limits, filename sanitising, the
authenticated download, approval creating a project), settings (secrets are
write-only), the weekly digest chain, the assistant, branding, Excel
import/export, password reset and the platform headers.

## After pulling a new version

```
cd backend && venv\Scripts\activate && pip install -r requirements.txt && alembic upgrade head
cd frontend && npm install
```

Migrations are the only way the database schema changes; `alembic upgrade
head` is idempotent and safe to run every time.

## What happens automatically

- Every Monday at 9:00 AM IST (configurable via `DIGEST_CRON_*` in `.env`),
  each member's Plan/Progress/Problem updates from the past week are emailed
  to whoever they report to; your own rollup covering the whole team goes to
  whoever *you* report to (a system user if they have a login, or the
  `external_manager_email` you gave the seed script if not).
- When a vertical staffer submits a service request (with a signed BRD, which
  is compulsory — the form won't submit without it), an email goes to every
  admin user, CC'ing the vertical head.
- Every create/update/approve/reject action is logged with who and when —
  visible to admins under Admin > Audit Trail. Failed logins, password
  resets, BRD downloads and Excel exports are logged too.
- **Forgot password** on the login page e-mails a one-time link (validity
  configurable in Settings > Security). The form answers the same way whether
  or not the address exists, so it cannot be used to discover accounts, and
  it shares the login lockout so it cannot be used to flood an inbox.
- Five wrong passwords lock an address for fifteen minutes (both numbers are
  in Settings > Security).

## Changing things later (no redeploy)

Almost nothing about how this app behaves is fixed in code. Signed in as an
admin, under **Admin Panel** you can change:

- **Users** — add people, set roles, and set who reports to whom (this is what
  drives the weekly email chain). Your own row is editable too.
- **Verticals** — add/rename verticals and their head's name and email.
- **Statuses** — add/rename project statuses, their colour, order, and which
  ones count as "finished" (the dashboard's Ongoing count follows that flag
  rather than any fixed status name).
- **Branding** — upload or remove the logo (SVG/PNG). It drives the sidebar,
  the login page and the browser tab icon from one stored asset.
- **Settings** — the application name shown everywhere including emails, the
  app URL used in e-mail links, the SMTP mailbox, the weekly digest
  day/time/timezone (applies immediately, no restart), the AI model and key
  and an on/off switch, upload size limits, minimum password length, login
  lockout, reset-link validity, how long a login stays valid, and the
  assistant's name, greeting, suggested questions and "about us" knowledge.
- **Assistant chats** — every conversation people have had with the in-app
  assistant, so you can see what is being asked.

## The assistant

A robot button sits in the bottom-right corner of every screen. It answers
questions about the tracker from live database data — which projects are
running, which are finished, what is in the queue, which vertical owns what —
plus the "about us" text you set in Settings.

Two deliberate limits: it is **read-only** (it can answer, never change
anything), and it only ever sees what the person asking is allowed to see — a
requestor's assistant answers from the same public queue they can already
browse, while the AI team's also sees update logs, owners and request detail.
That scoping lives in the database queries, not in the prompt, so it holds
however a question is phrased.

**It works with no language model at all.** With `Language model provider` set
to `none` (the default) it needs no API key, no GPU and sends nothing outside
your network — it parses the question, runs the matching query and writes the
answer up in Python. It handles what's in progress, what's completed, what's
overdue, what a vertical is working on, a named project's detail and its latest
update, blockers, service requests, the team, and the verticals. Anything it
can't match, it says so rather than guessing.

Switching the provider to `anthropic` and adding a key upgrades it to free-form
questions. The model then calls the same read-only queries rather than being
handed a copy of the database, so its counts come from the database too.

The only things that stay in `backend/.env` are the ones that genuinely cannot
come from the database: the database connection itself, the token signing key,
the upload directory, the frontend origin and the production plumbing switches
(log format, static folder, scheduler on/off).

## Going to production

The app is built to run as **one process on one port**, behind HTTPS.

1. Build the frontend once: `cd frontend && npm run build` (creates
   `frontend/dist`). Leave `VITE_API_BASE_URL` empty in `frontend/.env` for
   this build — the page then talks to the backend that served it.
2. In `backend/.env` set `FRONTEND_ORIGIN` to the public URL people will use,
   and in Admin > Settings set **App URL** to the same value (that is what
   password-reset e-mails link to).
3. Start the backend without `--reload` and with exactly one worker:
   `uvicorn app.main:app --host 127.0.0.1 --port 8002 --workers 1`. When
   `frontend/dist` exists the backend serves it, with deep links working.
   Only one process may run the scheduler (`RUN_SCHEDULER=1`), or the Monday
   digest goes out twice.
4. Put HTTPS in front of it. `deploy/linux/Caddyfile` does that with automatic
   certificates; set `TRUST_PROXY_HEADERS=1` in `.env` so client IPs in the
   audit log are real.

`deploy/` has the rest:

- `deploy/windows/install-service.ps1` — registers the backend as a Windows
  service (NSSM) or a start-at-boot Task Scheduler job, restarting on failure.
- `deploy/windows/backup.ps1` and `deploy/linux/backup.sh` — nightly Postgres
  dump + zipped BRD uploads, keeping the last 14. Restore instructions are at
  the bottom of each script.
- `deploy/linux/aikyam-tracker.service` — systemd unit with the same
  single-worker rule and filesystem hardening.

Logs are one JSON object per line (`LOG_FORMAT=json`), each carrying the
request id that is also returned to the browser as `X-Request-ID`, so a
problem report can be matched to its exact log lines. `LOG_FORMAT=text` is
friendlier in a terminal. `GET /api/health` reports database reachability,
scheduler state and the next digest run — point an uptime monitor at it.

Security headers (`nosniff`, `frame-ancestors 'none'`, a Content-Security-Policy
on the served frontend, HSTS behind HTTPS) are set on every response. Uploaded
BRDs are never served from a public URL — only through an authenticated route
that checks the requester's role.

## Notes

- New joiners: add them from Admin > Users any time — their `reports_to` is
  just another admin-editable dropdown, no code changes needed.
- The AI features (Quick-Fill, Ask-the-Tracker) only reason over data you can
  already see in the app — they never see or affect anything outside that.
- If you ever want to add more verticals or statuses, or rename the existing
  ones, that's all in the Admin panel — the seed script's list was just a
  starting point.
- Project names are unique (case-insensitive) — the tracker refuses a second
  "FD Treasury" rather than letting two drift apart. Each project also carries
  who assigned it, when, and free-text remarks, matching the team's original
  spreadsheet.
