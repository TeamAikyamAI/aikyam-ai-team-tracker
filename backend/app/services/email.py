"""SMTP sending for weekly digests and service-request notifications.

Uses one shared automation mailbox: the real person's name goes in the From
display name and Reply-To, so replies land with the actual person - no
Microsoft Graph / admin-consent dependency.

All SMTP configuration is read live from admin settings on every send, so
changing the mailbox in the Settings screen takes effect on the next email
without a restart.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from sqlalchemy.orm import Session

from app.services import settings as cfg

_log = logging.getLogger("aikyam.email")


def send_email(
    db: Session,
    to: list[str],
    subject: str,
    html_body: str,
    reply_to: str | None = None,
    cc: list[str] | None = None,
    from_display_name: str | None = None,
    raise_on_error: bool = False,
) -> bool:
    """Send one email. Returns True if it went, False if it did not.

    A failure here must never take down the request that triggered it. Sending
    mail is a side effect of the real work: a password reset token is already
    issued, a service request is already saved, a digest still has other people
    to reach. Letting an SMTP error escape turned all of those into a 500 for
    the user even though their action had succeeded - and, for a service
    request, made them think the submission was lost when it was not.

    So the failure is logged loudly and swallowed. ``raise_on_error=True`` is
    for Admin > Settings > Send test email, whose entire job is to tell an
    admin exactly why the mailbox is not working.
    """
    host = cfg.get(db, "smtp_host")
    if not host:
        _log.warning("email skipped - SMTP not configured", extra={"extra_fields": {"to": to, "cc": cc, "subject": subject}})
        return False

    port = cfg.get(db, "smtp_port")
    username = cfg.get(db, "smtp_username")
    password = cfg.get(db, "smtp_password")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((from_display_name or cfg.get(db, "smtp_from_name"), username))
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(html_body, "html"))

    all_recipients = to + (cc or [])
    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(username, all_recipients, msg.as_string())
    except Exception as exc:
        _log.error(
            "email failed",
            extra={"extra_fields": {
                "to": to, "cc": cc or [], "subject": subject,
                "error": f"{type(exc).__name__}: {exc}",
            }},
        )
        if raise_on_error:
            raise
        return False

    _log.info("email sent", extra={"extra_fields": {"to": to, "cc": cc or [], "subject": subject}})
    return True
