from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "1.1.0"

# Placeholder secrets that must never reach a running server.
_WEAK_SECRETS = {"", "dev-secret-change-me", "change-this-to-a-long-random-string", "changeme", "secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # No default on purpose. A fallback here means a missing .env silently runs
    # the whole app against the wrong database, which is exactly what happened
    # once - migrations and data quietly went to a local SQLite file instead of
    # Postgres. Better to refuse to start and say so.
    database_url: str = ""

    # "production" (default) refuses weak secrets; "development" only warns.
    app_env: str = "production"

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "Aikyam AI Team Tracker"

    anthropic_api_key: str = ""

    digest_cron_day_of_week: str = "mon"
    digest_cron_hour: int = 9
    digest_cron_minute: int = 0
    digest_timezone: str = "Asia/Kolkata"

    upload_dir: str = "./uploads"

    frontend_origin: str = "http://localhost:5180"

    # Production plumbing - all optional, all with safe defaults.
    run_scheduler: bool = True          # set 0 on every worker but one if you ever scale out
    log_format: str = "json"            # json | text
    log_level: str = "INFO"
    static_dir: str = "../frontend/dist"  # built SPA; served by the backend when the folder exists
    trust_proxy_headers: bool = False   # True behind Caddy/nginx so client IPs are logged correctly


settings = Settings()

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL is not set.\n\n"
        "Copy backend/.env.example to backend/.env and set DATABASE_URL to your\n"
        "Postgres database, for example:\n"
        "  DATABASE_URL=postgresql+psycopg2://postgres:YOURPASSWORD@localhost:5432/aikyam_ai_tracker\n"
    )

if settings.jwt_secret.strip() in _WEAK_SECRETS or len(settings.jwt_secret) < 32:
    _msg = (
        "JWT_SECRET is missing or too weak (it must be a random string of at least 32 characters).\n"
        "Generate one and put it in backend/.env:\n"
        "  python -c \"import secrets; print(secrets.token_urlsafe(48))\"\n"
        "  JWT_SECRET=<paste the output here>\n"
        "Changing it later signs everyone out, nothing else."
    )
    if settings.app_env.lower().startswith("dev"):
        print(f"[config] WARNING: {_msg}")
    else:
        raise RuntimeError(_msg)
