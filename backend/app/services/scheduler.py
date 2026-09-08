"""Weekly digest scheduling.

The schedule is an admin setting, not a fixed cron in .env, so `reschedule_digest`
is called whenever those settings are saved - a change applies immediately
instead of waiting for a restart.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services import settings as cfg
from app.services.digest import send_weekly_digests

JOB_ID = "weekly_digest"
_scheduler = BackgroundScheduler()


def _run_weekly_digest_job():
    db = SessionLocal()
    try:
        if not cfg.get(db, "digest_enabled"):
            return
        send_weekly_digests(db)
    finally:
        db.close()


def _apply(db: Session):
    if not cfg.get(db, "digest_enabled"):
        if _scheduler.get_job(JOB_ID):
            _scheduler.remove_job(JOB_ID)
        return
    trigger = CronTrigger(
        day_of_week=cfg.get(db, "digest_day_of_week"),
        hour=cfg.get(db, "digest_hour"),
        minute=cfg.get(db, "digest_minute"),
        timezone=cfg.get(db, "digest_timezone"),
    )
    _scheduler.add_job(_run_weekly_digest_job, trigger, id=JOB_ID, replace_existing=True)


def reschedule_digest(db: Session):
    """Re-read the schedule from settings and apply it to the running scheduler."""
    if not _scheduler.running:
        return
    _apply(db)


def start_scheduler():
    db = SessionLocal()
    try:
        _apply(db)
    except Exception as exc:  # a missing table on first boot must not stop the app
        logging.getLogger("aikyam.scheduler").warning(f"could not load digest schedule yet: {exc}")
    finally:
        db.close()
    _scheduler.start()


def shutdown_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)


def scheduler_running() -> bool:
    return bool(_scheduler.running)


def next_run_time():
    job = _scheduler.get_job(JOB_ID)
    return job.next_run_time if job else None
