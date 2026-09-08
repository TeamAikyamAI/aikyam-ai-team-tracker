"""Aikyam AI Team Tracker - FastAPI entrypoint.

Everything the browser talks to lives under /api. When the built frontend
(frontend/dist) is present next to the backend, it is served from the same
process with an SPA fallback, so one port serves the whole app in production.
Uploaded BRDs are never served statically - see routers/service_requests.
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import APP_VERSION, settings
from app.core.database import get_db
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.services.scheduler import next_run_time, scheduler_running, start_scheduler, shutdown_scheduler

from app.routers import (
    auth, users, verticals, statuses, projects, updates, service_requests, ai, audit,
    branding, chatbot, daily, permissions, settings as settings_router,
)

configure_logging()
_log = logging.getLogger("aikyam")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    if settings.run_scheduler:
        start_scheduler()
    else:
        _log.info("scheduler disabled by RUN_SCHEDULER=0")
    _log.info("started", extra={"extra_fields": {"version": APP_VERSION, "env": settings.app_env}})
    yield
    shutdown_scheduler()


app = FastAPI(
    title="Aikyam AI Team Tracker",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

# Middleware order: the last added runs first. Security headers wrap
# everything, then request context, then CORS closest to the routes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Request-ID"],
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

api = APIRouter(prefix="/api")
for r in (auth, users, verticals, statuses, projects, updates, service_requests, ai, audit,
          branding, settings_router, chatbot, daily, permissions):
    api.include_router(r.router)


@api.get("/health", tags=["health"])
def health(db=Depends(get_db)):
    """Deep health: database reachable, digest scheduler state, next run."""
    from app.services import settings as cfg

    checks: dict[str, object] = {"database": "ok"}
    try:
        db.execute(text("SELECT 1"))
        app_name = cfg.get(db, "app_name")
        smtp_ready = bool(cfg.get(db, "smtp_host"))
    except Exception as exc:  # pragma: no cover - only on a broken DB
        _log.exception("health check failed")
        raise HTTPException(status_code=503, detail=f"database: {type(exc).__name__}")
    nxt = next_run_time()
    checks["scheduler"] = "running" if scheduler_running() else ("disabled" if not settings.run_scheduler else "stopped")
    checks["next_digest"] = nxt.isoformat() if nxt else None
    checks["smtp_configured"] = smtp_ready
    return {
        "status": "ok",
        "app": app_name,
        "version": APP_VERSION,
        "time": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


app.include_router(api)


# ---------------------------------------------------------------------------
# Built frontend (optional). `npm run build` in frontend/ produces dist/; when
# it exists the backend serves it with an SPA fallback so deep links work.
# ---------------------------------------------------------------------------
_static_dir = os.path.abspath(settings.static_dir)
_index_html = os.path.join(_static_dir, "index.html")

if os.path.isfile(_index_html):
    _assets = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = os.path.abspath(os.path.join(_static_dir, full_path))
        if full_path and candidate.startswith(_static_dir + os.sep) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(_index_html, headers={"Cache-Control": "no-cache"})

    _log.info("serving frontend", extra={"extra_fields": {"static_dir": _static_dir}})
else:
    _log.info("no built frontend found; API only", extra={"extra_fields": {"static_dir": _static_dir}})
