from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_feature
from app.models.user import User
from app.models.app_setting import AppSetting
from app.schemas.settings import SettingItem, SettingsResponse, SettingsUpdate, PublicSettings, TestEmailResult, DigestPreviewResult
from app.services import settings as cfg
from app.services.audit import log_action
from app.services.scheduler import reschedule_digest
from app.services.email import send_email
from app.services.digest import send_weekly_digests

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/public", response_model=PublicSettings)
def public_settings(db: Session = Depends(get_db)):
    """Unauthenticated: the login screen needs the app name and footer before sign-in."""
    values = cfg.get_all(db)
    return PublicSettings(**{k: values[k] for k in cfg.PUBLIC_KEYS})


@router.get("", response_model=SettingsResponse)
def list_settings(db: Session = Depends(get_db), _: User = Depends(require_feature("admin_panel"))):
    values = cfg.get_all(db)
    stored = {r.key for r in db.query(AppSetting).all() if r.value}
    items = []
    for d in cfg.REGISTRY:
        # Secrets are never sent back to the browser - only whether one is set.
        value = None if d.type == "secret" else values[d.key]
        items.append(SettingItem(
            key=d.key, group=d.group, label=d.label, type=d.type, help=d.help,
            options=list(d.options), min=d.min, max=d.max, env_only=d.env_only,
            value=value,
            # For an .env-backed field, "set" means the .env has a value - a
            # database row is irrelevant and may not exist at all.
            is_set=bool(
                values[d.key] if d.env_only
                else (d.key in stored or (d.type == "secret" and d.default))
            ),
        ))
    return SettingsResponse(items=items)


@router.patch("", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    try:
        changed = cfg.set_many(db, payload.values, user_id=admin.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if changed:
        log_action(db, admin.id, "update_settings", "app_setting", None, details=", ".join(sorted(changed)))

    # A schedule change has to take effect now, not at the next restart.
    if any(k.startswith("digest_") for k in changed):
        reschedule_digest(db)

    return list_settings(db=db, _=admin)


@router.post("/test-email", response_model=TestEmailResult)
def test_email(db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    """Sends a real email to the signed-in admin using the SMTP settings as
    currently saved, so you find out immediately whether the mailbox works
    instead of waiting for Monday's digest to silently fail."""
    if not cfg.get(db, "smtp_host"):
        raise HTTPException(status_code=400, detail="No SMTP host is configured yet. Fill in the Email settings and save first.")
    if not admin.email:
        raise HTTPException(status_code=400, detail="Your account has no email address to send to.")

    app_name = cfg.get(db, "app_name")
    try:
        send_email(
            db,
            to=[admin.email],
            subject=f"{app_name} - test email",
            html_body=(
                f"<p>This is a test from <strong>{app_name}</strong>.</p>"
                "<p>If you are reading this, the SMTP settings are working and the "
                "weekly digests and service-request notifications will send.</p>"
            ),
            # This screen exists to diagnose the mailbox, so here - and only
            # here - the SMTP error is what the admin needs to see.
            raise_on_error=True,
        )
    except Exception as exc:
        # The SMTP error itself is the useful part - surface it rather than a generic 500.
        log_action(db, admin.id, "test_email_failed", "app_setting", None, details=f"{type(exc).__name__}: {exc}")
        raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}")

    log_action(db, admin.id, "test_email_sent", "app_setting", None, details=admin.email)
    return TestEmailResult(ok=True, detail=f"Test email sent to {admin.email}. Check the inbox.")


@router.post("/digest-preview", response_model=DigestPreviewResult)
def digest_preview(db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    """Send this week's digest to yourself, exactly as Monday would produce it.

    Same data, same templates, same reporting chain - only the recipient is
    swapped for you and the subject is marked, so nobody's manager receives a
    trial run.
    """
    if not cfg.get(db, "smtp_host"):
        raise HTTPException(status_code=400, detail="No SMTP host is configured yet. Fill in the Email settings and save first.")
    try:
        count = send_weekly_digests(db, preview_to=admin.email)
    except Exception as exc:
        log_action(db, admin.id, "digest_preview_failed", "app_setting", None, details=f"{type(exc).__name__}: {exc}")
        raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}")

    log_action(db, admin.id, "digest_preview_sent", "app_setting", None, details=f"{count} email(s) to {admin.email}")
    if count == 0:
        return DigestPreviewResult(
            ok=True, emails_sent=0,
            detail=("Nothing to send: no one has a reporting manager set, or there are no updates "
                    "this week. Set 'Reports to' on your team in Admin > Users and log an update."),
        )
    return DigestPreviewResult(
        ok=True, emails_sent=count,
        detail=f"{count} digest email(s) sent to {admin.email}, marked [Preview].",
    )
