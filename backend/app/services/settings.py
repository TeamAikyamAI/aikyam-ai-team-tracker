"""Admin-editable application settings.

Everything an admin might reasonably want to change while the app is running
lives here rather than in code or .env: the product name shown in the UI and
emails, SMTP credentials, the weekly digest schedule, the AI model, and upload
limits. Each value falls back to the matching .env value (and then to a sane
default), so an existing install keeps working before anything is saved.

Deliberately NOT here - these are bootstrap or security concerns that cannot or
should not be served from the database the app has not connected to yet:
  DATABASE_URL, JWT_SECRET, UPLOAD_DIR, FRONTEND_ORIGIN.
"""
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings as env
from app.models.app_setting import AppSetting

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True)
class SettingDef:
    key: str
    group: str
    label: str
    type: str  # string | text | int | bool | select | secret
    default: Any
    help: str = ""
    options: tuple[str, ...] = ()
    min: int | None = None
    max: int | None = None
    # Read from .env only. The Admin screen shows it but cannot change it, and
    # nothing is written to the database. Used for the mail credentials: a
    # password has no business sitting in a table that ends up in every backup,
    # and it stopped the Settings form from ever overwriting one by accident.
    env_only: bool = False


REGISTRY: tuple[SettingDef, ...] = (
    # --- Organisation -------------------------------------------------------
    SettingDef("app_name", "Organisation", "Application name", "string",
               "Aikyam AI Team Tracker",
               "Shown in the sidebar, on the login page, in the browser tab and at the foot of every automated email."),
    SettingDef("org_name", "Organisation", "Organisation name", "string", "Aikyam Capital",
               "Used where the company is referred to, e.g. the verticals screen."),
    SettingDef("login_footer", "Organisation", "Login page footer", "string",
               "Aikyam Capital · AI & Automation Team · Internal use only"),
    SettingDef("email_domain", "Organisation", "Email domain", "string", "aikyamcapital.com",
               "Only used to build the example address shown in the login form."),
    SettingDef("app_base_url", "Organisation", "App URL", "string", env.frontend_origin,
               "Where people open the tracker in their browser. Used to build links in e-mails "
               "(password reset, notifications), e.g. https://tracker.aikyamcap.com"),

    # --- Email --------------------------------------------------------------
    SettingDef("smtp_host", "Email", "SMTP host", "string", env.smtp_host,
               "Leave blank to disable sending; the app still works, emails are just skipped."),
    SettingDef("smtp_port", "Email", "SMTP port", "int", env.smtp_port, min=1, max=65535),
    SettingDef("smtp_username", "Email", "SMTP username", "string", env.smtp_username,
               "The mailbox that sends the mail, e.g. ai.automation@aikyamcap.com."),
    SettingDef("smtp_password", "Email", "SMTP password", "secret", env.smtp_password,
               "Write-only: never sent back to the browser. Leave blank when saving "
               "to keep the current one."),
    SettingDef("smtp_from_name", "Email", "Default From name", "string", "Aikyam AI Team Tracker",
               "Shown as the sender when a mail is not sent on a specific person's behalf."),
    SettingDef("email_signature", "Email", "Email signature", "text", "AI Team",
               "Signs off every automated email - digests, request notifications and "
               "password resets. One line per line; leave blank for no signature."),

    # --- Weekly digest ------------------------------------------------------
    SettingDef("digest_enabled", "Weekly digest", "Send weekly digests", "bool", True,
               "Turns the whole scheduled email run on or off."),
    SettingDef("digest_day_of_week", "Weekly digest", "Day", "select", env.digest_cron_day_of_week, options=DAYS),
    SettingDef("digest_hour", "Weekly digest", "Hour (24h)", "int", env.digest_cron_hour, min=0, max=23),
    SettingDef("digest_minute", "Weekly digest", "Minute", "int", env.digest_cron_minute, min=0, max=59),
    SettingDef("digest_timezone", "Weekly digest", "Timezone", "string", env.digest_timezone,
               "IANA name, e.g. Asia/Kolkata. Schedule changes take effect immediately - no restart."),

    # --- Export -------------------------------------------------------------
    SettingDef("export_weeks", "Export", "Week columns in the export", "int", 4,
               "How many calendar weeks the Excel export shows, ending with the week "
               "we are in now. Each week is one column of project updates. A week "
               "starts on the day set under Weekly digest above, so the export and "
               "the digest always mean the same thing by 'this week'.",
               min=1, max=52),

    # --- AI -----------------------------------------------------------------
    SettingDef("ai_enabled", "AI", "Enable AI features", "bool", True,
               "Quick-Fill and Ask-the-Tracker. They fail soft when off or unconfigured."),
    SettingDef("ai_provider", "AI", "Language model provider", "select", "none",
               help=("'none' runs the assistant with no model at all - it answers the common "
                     "questions directly from the database, needs no API key and sends nothing "
                     "outside. 'anthropic' uses the Claude API key below for open-ended questions."),
               options=("none", "anthropic")),
    SettingDef("anthropic_api_key", "AI", "Anthropic API key", "secret", env.anthropic_api_key,
               "Write-only: never sent back to the browser once saved."),
    SettingDef("ai_model", "AI", "Model", "string", "claude-sonnet-4-5",
               "Change this to move to a newer model without touching code."),
    SettingDef("ai_max_tokens", "AI", "Max response tokens", "int", 800, min=100, max=8000),

    # --- Assistant ----------------------------------------------------------
    SettingDef("chatbot_enabled", "Assistant", "Show the assistant", "bool", True,
               "The floating chat button in the bottom corner of every screen."),
    SettingDef("chatbot_name", "Assistant", "Assistant name", "string", "Aikyam Assistant",
               "Shown at the top of the chat window and used by the assistant to introduce itself."),
    SettingDef("chatbot_greeting", "Assistant", "Greeting", "string",
               "Hi! I'm your AI assistant. How can I help you?",
               "The little message shown next to the button and at the top of a new chat."),
    SettingDef("chatbot_suggestions", "Assistant", "Suggested questions", "text",
               "Which projects are going on right now?\nWhich projects are completed?\nWhat's in the queue?",
               "One per line. Shown as tappable chips when a chat is empty."),
    SettingDef("chatbot_about", "Assistant", "About us (assistant knowledge)", "text",
               "We are the AI & Automation team. We build automation and AI tools for the "
               "business verticals - things like reporting automation, reconciliation and "
               "internal tools. To request work from us, browse the project queue first and "
               "then submit a service request with a BRD signed by your vertical head.",
               "Free text the assistant uses to answer 'who are you' / 'what do you do' style "
               "questions. Project data comes from the database automatically - this is only "
               "the background it cannot infer."),

    # --- Limits -------------------------------------------------------------
    SettingDef("max_brd_upload_mb", "Limits", "Max BRD upload size (MB)", "int", 10,
               help="Applies to the BRD attached to a service request.", min=1, max=100),
    SettingDef("max_logo_kb", "Limits", "Max logo size (KB)", "int", 512, min=16, max=4096),
    SettingDef("min_password_length", "Security", "Minimum password length", "int", 10,
               help="Applies when an admin creates a user or sets a new password.", min=6, max=64),
    SettingDef("login_max_attempts", "Security", "Failed logins before lockout", "int", 5,
               help="Counted per email address and per IP within the window below.", min=3, max=50),
    SettingDef("login_lockout_minutes", "Security", "Lockout window (minutes)", "int", 15, min=1, max=1440),
    SettingDef("password_reset_minutes", "Security", "Password reset link validity (minutes)", "int", 30,
               help="How long a forgot-password link keeps working.", min=5, max=1440),
    SettingDef("session_hours", "Limits", "Session length (hours)", "int",
               max(1, int(env.jwt_expire_minutes / 60)),
               help="How long a login stays valid before the user must sign in again.", min=1, max=720),
)

BY_KEY = {d.key: d for d in REGISTRY}
PUBLIC_KEYS = ("app_name", "org_name", "login_footer", "email_domain",
               "chatbot_enabled", "chatbot_name", "chatbot_greeting", "chatbot_suggestions")


# Characters a masked field is made of. A "password" consisting only of these
# is the mask itself, never a real credential.
_MASK_CHARS = set("*\u2022\u25cf\u00b7\u2219 ")


def _is_mask(value: str) -> bool:
    """True for "******", "••••••••" and friends.

    This is what broke outgoing mail once: the Settings form carried its own
    mask back on an unrelated save and it was stored as the SMTP password, so
    every email failed with "credentials were incorrect" and nothing said why.
    A credential made only of mask characters is never one somebody meant.
    """
    v = value.strip()
    return bool(v) and set(v) <= _MASK_CHARS


def _cast(defn: SettingDef, raw: str) -> Any:
    if defn.type == "int":
        try:
            return int(raw)
        except (TypeError, ValueError):
            return defn.default
    if defn.type == "bool":
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    return raw


def _default(defn: SettingDef) -> Any:
    """The fallback used when nothing is stored for this setting.

    Several defaults are seeded from .env (SMTP, the AI key, the digest
    timezone). Those are read from the settings object rather than the value
    frozen into the registry when this module was imported, so editing .env and
    restarting is enough - and so a test can blank one without rebuilding the
    registry. Keys with no matching .env field fall back to the literal.
    """
    return getattr(env, defn.key, defn.default)


def get_all(db: Session) -> dict[str, Any]:
    """Every setting resolved: stored value if present, otherwise the default."""
    stored = {row.key: row.value for row in db.query(AppSetting).all()}
    out: dict[str, Any] = {}
    for defn in REGISTRY:
        if defn.env_only:
            # The .env value always wins, whatever a stale row might say.
            out[defn.key] = _default(defn)
        elif defn.key in stored and stored[defn.key] != "":
            out[defn.key] = _cast(defn, stored[defn.key])
        else:
            out[defn.key] = _default(defn)
    return out


def get(db: Session, key: str) -> Any:
    defn = BY_KEY[key]
    if defn.env_only:
        return _default(defn)
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row is None or row.value == "":
        return _default(defn)
    return _cast(defn, row.value)


def set_many(db: Session, values: dict[str, Any], user_id: int | None = None) -> list[str]:
    """Writes the given settings and returns the keys that actually changed."""
    changed: list[str] = []
    for key, value in values.items():
        defn = BY_KEY.get(key)
        if defn is None:
            raise ValueError(f"Unknown setting: {key}")
        if defn.env_only:
            # Loud rather than silent: if the UI ever sends one of these it is a
            # bug, and quietly ignoring it would look like the save worked.
            raise ValueError(
                f"{defn.label} is set in backend/.env, not here. "
                "Edit the .env file and restart the backend."
            )
        # A blank secret means "leave the stored one alone", so an admin can save
        # the form without retyping passwords they never see. A masked one means
        # the same thing - see _is_mask.
        if defn.type == "secret" and (value is None or value == "" or _is_mask(str(value))):
            continue
        if defn.type == "bool":
            text = "true" if bool(value) else "false"
        else:
            text = "" if value is None else str(value)

        if defn.type == "int":
            try:
                n = int(text)
            except ValueError:
                raise ValueError(f"{defn.label} must be a whole number")
            if defn.min is not None and n < defn.min:
                raise ValueError(f"{defn.label} must be at least {defn.min}")
            if defn.max is not None and n > defn.max:
                raise ValueError(f"{defn.label} must be at most {defn.max}")
        if defn.type == "select" and text not in defn.options:
            raise ValueError(f"{defn.label} must be one of: {', '.join(defn.options)}")
        if defn.type == "string" and defn.key in ("app_name",) and not text.strip():
            raise ValueError("Application name cannot be empty")

        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row is None:
            row = AppSetting(key=key, value=text, updated_by_id=user_id)
            db.add(row)
            changed.append(key)
        elif row.value != text:
            row.value = text
            row.updated_by_id = user_id
            changed.append(key)
    db.commit()
    return changed
