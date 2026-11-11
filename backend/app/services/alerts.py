"""Runs alert rules (deterministic) and delivers notifications (US-06/07/08)."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DISCLAIMER
from ..db import utcnow
from ..models import AlertDelivery, AlertRule, Customer, User
from . import rates as rates_svc
from .notify import Notifier
from .rules import RuleResult, evaluate_rule


def evaluate_for_rule(db: Session, rule: AlertRule) -> tuple[RuleResult | None, object | None]:
    latest = rates_svc.latest_rate(db, rule.metal)
    if not latest:
        return None, None
    prior = rates_svc.prior_prices(db, rule.metal, latest.rate_date, rule.window_days)
    return evaluate_rule(rule.kind, rule.threshold, latest.price_per_gram, prior), latest


def compose_message(db: Session, user: User, rule: AlertRule, res: RuleResult) -> str:
    margin = rates_svc.get_margin(db, user.id, rule.metal)
    sell = rates_svc.selling_price(res.current, margin)
    disp, unit = rates_svc.to_display(rule.metal, sell)
    lines = [f"{user.shop_name} - {rule.metal.title()} rate alert", f"Today: Rs {disp:,.0f} per {unit}"]
    if res.avg is not None and res.pct_below is not None:
        direction = "below" if res.pct_below >= 0 else "above"
        lines.append(f"Market is {abs(res.pct_below):.1f}% {direction} its {rule.window_days}-day average.")
    if user.phone:
        lines.append(f"Contact: {user.shop_name}, {user.phone}")
    lines += ["", DISCLAIMER, "Send /stop to stop these messages."]
    return "\n".join(lines)


def _deliver(db: Session, notifier: Notifier, rule: AlertRule, user: User, chat_id: str | None,
             customer_id: int | None, text: str) -> None:
    if not chat_id:
        db.add(AlertDelivery(rule_id=rule.id, user_id=user.id, customer_id=customer_id,
                             channel=notifier.channel, status="skipped", message=text, error="no linked chat"))
        return
    try:
        notifier.send(chat_id, text)
        status, err = "sent", None
    except Exception as e:
        status, err = "failed", str(e)
    db.add(AlertDelivery(rule_id=rule.id, user_id=user.id, customer_id=customer_id,
                         channel=notifier.channel, status=status, message=text, error=err))


def run_rules(db: Session, notifier: Notifier) -> list[dict]:
    """Evaluate every active rule once. Returns a summary per rule."""
    summary = []
    rules = db.scalars(select(AlertRule).where(AlertRule.active.is_(True))).all()
    for rule in rules:
        user = db.get(User, rule.user_id)
        res, _ = evaluate_for_rule(db, rule)
        if res is None:
            summary.append({"rule_id": rule.id, "triggered": False, "reason": "no rates"})
            continue
        cooling = rule.last_triggered_at and utcnow() - rule.last_triggered_at < timedelta(hours=rule.cooldown_hours)
        if not res.triggered or cooling:
            summary.append({"rule_id": rule.id, "triggered": False,
                            "reason": "cooldown" if (res.triggered and cooling) else res.reason})
            continue
        text = compose_message(db, user, rule, res)
        if rule.audience == "self":
            _deliver(db, notifier, rule, user, user.telegram_chat_id, None, text)
        else:
            customers = db.scalars(select(Customer).where(Customer.user_id == user.id,
                                                          Customer.opted_out.is_(False))).all()
            for c in customers:
                _deliver(db, notifier, rule, user, c.telegram_chat_id, c.id, text)
        rule.last_triggered_at = utcnow()
        db.commit()
        summary.append({"rule_id": rule.id, "triggered": True, "reason": res.reason})
    return summary
