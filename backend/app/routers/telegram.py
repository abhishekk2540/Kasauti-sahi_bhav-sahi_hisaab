"""Telegram webhook: links chats to users/customers via /start <u|c>_<token>, and handles /stop (opt-out)."""
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Customer, User
from ..services.notify import Notifier, get_notifier

router = APIRouter(tags=["telegram"])
log = logging.getLogger(__name__)


def handle_update(db: Session, update: dict, notifier: Notifier) -> str:
    msg = update.get("message") or {}
    chat_id = str((msg.get("chat") or {}).get("id") or "")
    text = (msg.get("text") or "").strip()
    if not chat_id or not text:
        return "ignored"

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        payload = parts[1] if len(parts) > 1 else ""
        kind, _, token = payload.partition("_")
        if kind == "u":
            u = db.scalar(select(User).where(User.link_token == token))
            if u:
                u.telegram_chat_id = chat_id
                db.commit()
                notifier.send(chat_id, f"Linked! You will get alerts for {u.shop_name} here.")
                return "linked_user"
        elif kind == "c":
            c = db.scalar(select(Customer).where(Customer.link_token == token))
            if c:
                c.telegram_chat_id, c.opted_out = chat_id, False
                db.commit()
                shop = db.get(User, c.user_id).shop_name
                notifier.send(chat_id, f"Namaste {c.name}! You will now get rate updates from {shop}. "
                                       "Send /stop any time to unsubscribe.")
                return "linked_customer"
        notifier.send(chat_id, "This link is invalid or expired.")
        return "invalid_link"

    if text.lower().startswith("/stop"):
        rows = db.scalars(select(Customer).where(Customer.telegram_chat_id == chat_id)).all()
        for c in rows:
            c.opted_out = True
        db.commit()
        notifier.send(chat_id, "You have been unsubscribed. Send /start with your shop's link to rejoin.")
        return "opted_out"
    return "ignored"


@router.post("/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(None),
                  db: Session = Depends(get_db)):
    secret = get_settings().telegram_webhook_secret
    if secret and not hmac.compare_digest(x_telegram_bot_api_secret_token or "", secret):
        raise HTTPException(403, "Bad secret")
    if not secret and get_settings().env == "production":
        raise HTTPException(503, "TELEGRAM_WEBHOOK_SECRET not configured")
    try:
        result = handle_update(db, await request.json(), get_notifier())
    except Exception:
        log.exception("telegram update failed")
        result = "error"  # always 200 so Telegram does not retry forever
    return {"ok": True, "result": result}
