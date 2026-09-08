"""Login / whoami.

Brute-force protection is a small in-memory counter keyed by the e-mail
address being tried. Both the threshold and the lockout window are admin
settings (``login_max_attempts`` / ``login_lockout_minutes``). The counter
lives in this process, which is correct for the single-worker deployment
this app ships with (see README - the in-process scheduler needs that too).
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import client_ip
from app.core.security import verify_password, create_access_token, hash_password
from app.core.deps import get_current_user
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, TokenResponse, MeResponse, ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
)
from app.services.audit import log_action
from app.services.email import send_email
from app.services import settings as cfg

_env = Environment(loader=FileSystemLoader("app/templates"), autoescape=True)

router = APIRouter(prefix="/auth", tags=["auth"])

# email -> (failed attempts, first failure time)
_attempts: dict[str, tuple[int, datetime]] = {}
_attempts_lock = Lock()


def _lockout_remaining(email: str, max_attempts: int, window: timedelta) -> int:
    """Seconds left on a lockout for this e-mail, or 0 when login may proceed."""
    with _attempts_lock:
        entry = _attempts.get(email)
        if not entry:
            return 0
        count, first = entry
        if datetime.utcnow() - first > window:
            _attempts.pop(email, None)
            return 0
        if count >= max_attempts:
            return int((first + window - datetime.utcnow()).total_seconds()) or 1
        return 0


def _record_failure(email: str, window: timedelta) -> None:
    with _attempts_lock:
        count, first = _attempts.get(email, (0, datetime.utcnow()))
        if datetime.utcnow() - first > window:
            count, first = 0, datetime.utcnow()
        _attempts[email] = (count + 1, first)


def _clear_failures(email: str) -> None:
    with _attempts_lock:
        _attempts.pop(email, None)


def reset_rate_limits() -> None:
    """Test hook - forget every counter."""
    with _attempts_lock:
        _attempts.clear()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    max_attempts = max(1, int(cfg.get(db, "login_max_attempts")))
    window = timedelta(minutes=max(1, int(cfg.get(db, "login_lockout_minutes"))))

    remaining = _lockout_remaining(email, max_attempts, window)
    if remaining:
        minutes = max(1, -(-remaining // 60))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed sign-in attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
            headers={"Retry-After": str(remaining)},
        )

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        _record_failure(email, window)
        log_action(db, user.id if user else None, "login_failed", "user", user.id if user else None,
                   f"email={email} ip={client_ip(request)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    _clear_failures(email)
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role},
        expire_minutes=int(cfg.get(db, "session_hours")) * 60,
    )
    log_action(db, user.id, "login")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------
_GENERIC_FORGOT_REPLY = "If that address has an account, a reset link is on its way."


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Always answers the same way, so the form cannot be used to discover
    which addresses have accounts. Shares the login lockout counter, so it
    cannot be used to flood someone's inbox either."""
    email = payload.email.strip().lower()
    max_attempts = max(1, int(cfg.get(db, "login_max_attempts")))
    window = timedelta(minutes=max(1, int(cfg.get(db, "login_lockout_minutes"))))
    if _lockout_remaining(email, max_attempts, window):
        return MessageResponse(detail=_GENERIC_FORGOT_REPLY)
    _record_failure(email, window)

    user = db.query(User).filter(func.lower(User.email) == email, User.is_active == True).first()  # noqa: E712
    if not user:
        return MessageResponse(detail=_GENERIC_FORGOT_REPLY)

    minutes = int(cfg.get(db, "password_reset_minutes"))
    token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
    ))
    db.commit()

    base = (cfg.get(db, "app_base_url") or "").rstrip("/")
    link = f"{base}/reset-password?token={token}"
    app_name = cfg.get(db, "app_name")
    html = _env.get_template("password_reset.html").render(
        signature=cfg.get(db, "email_signature"),
        app_name=app_name, name=user.name, email=user.email, minutes=minutes, link=link,
    )
    send_email(db, to=[user.email], subject=f"{app_name}: reset your password", html_body=html)
    log_action(db, user.id, "password_reset_requested", "user", user.id, f"ip={client_ip(request)}")
    return MessageResponse(detail=_GENERIC_FORGOT_REPLY)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    from app.routers.users import _check_password  # same rules as the admin form

    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == _hash_token(payload.token)).first()
    now = datetime.now(timezone.utc)
    expires = record.expires_at if record else None
    if expires is not None and expires.tzinfo is None:  # SQLite hands back naive datetimes
        expires = expires.replace(tzinfo=timezone.utc)
    if not record or record.used_at is not None or expires < now:
        raise HTTPException(status_code=400, detail="That reset link is invalid or has expired. Please request a new one.")

    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="That reset link is invalid or has expired. Please request a new one.")

    _check_password(db, payload.password)
    user.password_hash = hash_password(payload.password)
    record.used_at = now
    # Any other outstanding links for this person stop working too.
    for other in db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None), PasswordResetToken.id != record.id
    ):
        other.used_at = now
    db.commit()
    _clear_failures(user.email.lower())
    log_action(db, user.id, "password_reset_completed", "user", user.id, f"ip={client_ip(request)}")
    return MessageResponse(detail="Your password has been changed. You can sign in now.")
