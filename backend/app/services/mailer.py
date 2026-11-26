"""Password-reset delivery. Sends by email (SMTP) and/or the user's linked Telegram chat.

SMTP settings (all optional): SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD, SMTP_FROM.
FRONTEND_URL is the public website URL used in the reset link (defaults to the first CORS origin).
Never raises: it runs as a background task and must not reveal whether an account exists.
"""
import logging
import os
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from ..config import get_settings
from .notify import get_notifier

log = logging.getLogger(__name__)


def frontend_url() -> str:
    url = os.getenv("FRONTEND_URL") or (get_settings().cors_origins or ["http://localhost:3000"])[0]
    return url.rstrip("/")


def reset_link(token: str) -> str:
    return f"{frontend_url()}/reset-password?token={quote(token)}"


def _body(link: str) -> str:
    return (
        "We received a request to reset your Kasauti password.\n\n"
        f"Open this link to choose a new password (valid for 30 minutes):\n{link}\n\n"
        "If you did not ask for this, you can ignore this message. Your password will not change."
    )


def _send_email(to: str, text: str) -> bool:
    host = os.getenv("SMTP_HOST")
    if not host:
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    user, password = os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    msg = EmailMessage()
    msg["Subject"] = "Reset your Kasauti password"
    msg["From"] = os.getenv("SMTP_FROM") or user or "no-reply@kasauti.local"
    msg["To"] = to
    msg.set_content(text)
    smtp_cls = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
    with smtp_cls(host, port, timeout=15) as smtp:
        if port != 465:
            smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)
    return True


def send_password_reset(email: str, telegram_chat_id: str | None, token: str) -> None:
    link = reset_link(token)
    text = _body(link)
    delivered = False
    try:
        delivered = _send_email(email, text)
    except Exception:
        log.exception("Password reset email failed")
    if telegram_chat_id and get_settings().telegram_bot_token:
        try:
            get_notifier().send(telegram_chat_id, text)
            delivered = True
        except Exception:
            log.exception("Password reset Telegram message failed")
    if not delivered:
        if get_settings().env == "production":
            log.warning("Password reset requested but no delivery channel is configured (set SMTP_HOST).")
        else:  # dev convenience only: never log the link in production
            log.info("[dev] password reset link for %s: %s", email, link)