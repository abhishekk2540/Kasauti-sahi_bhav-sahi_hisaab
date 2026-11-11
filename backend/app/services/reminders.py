"""Scheme payment reminders: AI-drafted, editable, sent only after the jeweller approves (US-10)."""
import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import today_ist, utcnow
from ..models import Installment, Reminder, User
from . import schemes as schemes_svc
from .llm import get_llm_client, simple_complete
from .notify import Notifier

log = logging.getLogger(__name__)


def template_text(shop: str, customer: str, scheme: str, number: int, amount: int, due: date) -> str:
    return (f"Namaste {customer}, {shop} ki {scheme} ki installment #{number} (Rs {amount:,}) "
            f"{due.strftime('%d %b %Y')} ko due hai. Kripya samay par jama karein. Dhanyavaad!")


def draft_text(shop: str, customer: str, scheme: str, number: int, amount: int, due: date) -> tuple[str, str]:
    """Returns (text, drafted_by). Falls back to a template if the LLM is unavailable."""
    fallback = template_text(shop, customer, scheme, number, amount, due)
    client = get_llm_client()
    if not client:
        return fallback, "template"
    try:
        text = simple_complete(
            client,
            ("You write short, polite WhatsApp/Telegram payment reminders for an Indian jewellery shop's "
             "savings scheme. Use simple Hinglish, 2-3 sentences, no emojis overload. Use ONLY the facts "
             "given. Do not promise discounts or anything else. Output the message text only."),
            (f"Shop: {shop}\nCustomer: {customer}\nScheme: {scheme}\nInstallment number: {number}\n"
             f"Amount: Rs {amount}\nDue date: {due.isoformat()}"),
            max_tokens=400)  # gpt-oss spends some tokens on hidden reasoning
        return (text, "ai") if text else (fallback, "template")
    except Exception as e:
        log.warning("AI reminder draft failed, using template: %s", e)
        return fallback, "template"


def create_due_reminders(db: Session, days_before: int | None = None, on: date | None = None) -> list[Reminder]:
    """Create draft reminders for pending installments due in exactly N days (skips ones already drafted)."""
    days = get_settings().reminder_days_before if days_before is None else days_before
    target = (on or today_ist()) + timedelta(days=days)
    insts = db.scalars(select(Installment).where(Installment.status == "pending", Installment.due_date == target)).all()
    created = []
    for inst in insts:
        if db.scalar(select(Reminder.id).where(Reminder.installment_id == inst.id)):
            continue
        e = inst.enrolment
        owner = db.get(User, e.scheme.user_id)
        text, by = draft_text(owner.shop_name, e.customer.name, e.scheme.name, inst.number, inst.amount, inst.due_date)
        r = Reminder(user_id=owner.id, installment_id=inst.id, draft_text=text, drafted_by=by)
        db.add(r)
        created.append(r)
    db.commit()
    return created


def send_reminder(db: Session, reminder: Reminder, notifier: Notifier) -> Reminder:
    if reminder.status == "sent":
        raise ValueError("Reminder already sent")
    customer = reminder.installment.enrolment.customer
    if customer.opted_out:
        raise ValueError("Customer has opted out")
    if not customer.telegram_chat_id:
        raise ValueError("Customer has not linked Telegram yet")
    try:
        notifier.send(customer.telegram_chat_id, reminder.draft_text)
        reminder.status, reminder.sent_at, reminder.error = "sent", utcnow(), None
    except Exception as e:
        reminder.status, reminder.error = "failed", str(e)
    db.commit()
    return reminder
