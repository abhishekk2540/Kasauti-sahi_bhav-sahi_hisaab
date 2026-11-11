"""Agent tools. Every tool is scoped to the calling user and returns plain JSON.

Read tools return DB facts. The only write path is `propose_record_payment`, which creates a PendingAction;
the data changes only when the user confirms via POST /agent/confirm/{id}  (US-11: never change data silently).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Customer, Enrolment, PendingAction, Scheme, User
from .. import rates as rates_svc
from .. import schemes as schemes_svc
from ..reminders import template_text

TOOLS = [
    {
        "name": "get_price",
        "description": "Latest stored gold or silver rate: market and the shop's selling price, plus comparison "
                       "with the 7-day and 30-day average. Use for any question about today's price.",
        "input_schema": {"type": "object", "properties": {"metal": {"type": "string", "enum": ["gold", "silver"]}},
                         "required": ["metal"]},
    },
    {
        "name": "get_price_movement",
        "description": "Price movement over the last N days from stored data: start, end, change %, high, low. "
                       "Use to explain why/how the price moved. Never explain movement without calling this.",
        "input_schema": {"type": "object", "properties": {
            "metal": {"type": "string", "enum": ["gold", "silver"]},
            "days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 7}}, "required": ["metal"]},
    },
    {
        "name": "list_pending_payments",
        "description": "Scheme installments that are still pending. Optionally filter by month (YYYY-MM) or only "
                       "overdue ones. Use for 'kiski payment pending hai' type questions.",
        "input_schema": {"type": "object", "properties": {
            "month": {"type": "string", "description": "YYYY-MM, optional"},
            "overdue_only": {"type": "boolean", "default": False}}},
    },
    {
        "name": "customer_scheme_status",
        "description": "Look up a customer by (part of) name and return their scheme enrolments and installment status.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
    {
        "name": "draft_reminder",
        "description": "Draft (do NOT send) a payment reminder message for one installment. Returns text only.",
        "input_schema": {"type": "object", "properties": {"installment_id": {"type": "integer"}},
                         "required": ["installment_id"]},
    },
    {
        "name": "propose_record_payment",
        "description": "Propose marking an installment as paid. This does NOT change anything: it creates a pending "
                       "action the shop owner must confirm in the app. Tell the user it awaits their confirmation.",
        "input_schema": {"type": "object", "properties": {
            "installment_id": {"type": "integer"},
            "amount": {"type": "integer", "description": "Rupees paid; defaults to the installment amount"}},
            "required": ["installment_id"]},
    },
]


def get_price(db: Session, user: User, metal: str) -> dict:
    snap = rates_svc.rate_snapshot(db, user.id, metal)
    return snap or {"error": f"No {metal} rate stored yet"}


def get_price_movement(db: Session, user: User, metal: str, days: int = 7) -> dict:
    rows = rates_svc.history(db, metal, days)
    if len(rows) < 2:
        return {"error": "Not enough stored history for this period", "points": len(rows)}
    prices = [r.price_per_gram for r in rows]
    hi = max(rows, key=lambda r: r.price_per_gram)
    lo = min(rows, key=lambda r: r.price_per_gram)
    return {
        "metal": metal, "days_requested": days, "points": len(rows),
        "from_date": rows[0].rate_date.isoformat(), "to_date": rows[-1].rate_date.isoformat(),
        "start_per_gram": round(prices[0], 2), "end_per_gram": round(prices[-1], 2),
        "change_pct": round((prices[-1] - prices[0]) / prices[0] * 100, 2),
        "high_per_gram": round(hi.price_per_gram, 2), "high_date": hi.rate_date.isoformat(),
        "low_per_gram": round(lo.price_per_gram, 2), "low_date": lo.rate_date.isoformat(),
    }


def list_pending_payments(db: Session, user: User, month: str | None = None, overdue_only: bool = False) -> dict:
    try:
        insts = schemes_svc.list_installments(db, user.id, status="pending", month=month, overdue_only=overdue_only)
    except ValueError:
        return {"error": "month must be YYYY-MM"}
    items = [schemes_svc.describe(i) for i in insts[:50]]
    return {"count": len(insts), "shown": len(items), "total_amount": sum(i.amount for i in insts), "items": items}


def customer_scheme_status(db: Session, user: User, name: str) -> dict:
    custs = db.scalars(select(Customer).where(Customer.user_id == user.id, Customer.name.ilike(f"%{name}%"))).all()
    if not custs:
        return {"error": f"No customer matching '{name}'"}
    out = []
    for c in custs[:5]:
        ens = db.scalars(select(Enrolment).join(Scheme).where(Enrolment.customer_id == c.id,
                                                              Scheme.user_id == user.id)).all()
        out.append({"customer": c.name, "phone": c.phone, "enrolments": [{
            "scheme": e.scheme.name, "maturity_date": e.maturity_date.isoformat(),
            "paid": sum(1 for i in e.installments if i.status == "paid"),
            "pending": [schemes_svc.describe(i) for i in e.installments if i.status == "pending"][:3],
            "total_installments": len(e.installments)} for e in ens]})
    return {"matches": out}


def draft_reminder(db: Session, user: User, installment_id: int) -> dict:
    inst = schemes_svc.get_installment(db, user.id, installment_id)
    if not inst:
        return {"error": "Installment not found"}
    e = inst.enrolment
    return {"installment_id": inst.id, "draft": template_text(user.shop_name, e.customer.name, e.scheme.name,
                                                              inst.number, inst.amount, inst.due_date),
            "sent": False}


def propose_record_payment(db: Session, user: User, installment_id: int, amount: int | None = None) -> dict:
    inst = schemes_svc.get_installment(db, user.id, installment_id)
    if not inst:
        return {"error": "Installment not found"}
    if inst.status == "paid":
        return {"error": "Installment is already paid"}
    paid = amount or inst.amount
    summary = (f"Mark installment #{inst.number} of {inst.enrolment.customer.name} "
               f"({inst.enrolment.scheme.name}) as paid: Rs {paid:,}")
    pa = PendingAction(user_id=user.id, action="record_payment",
                       payload={"installment_id": inst.id, "amount": paid}, summary=summary)
    db.add(pa)
    db.commit()
    return {"requires_confirmation": True, "pending_action_id": pa.id, "summary": summary,
            "note": "Nothing has been changed yet. The owner must confirm."}


def execute_pending(db: Session, user: User, action_id: str) -> dict:
    pa = db.get(PendingAction, action_id)
    if not pa or pa.user_id != user.id:
        raise LookupError("Action not found")
    if pa.status != "pending":
        raise ValueError(f"Action already {pa.status}")
    if pa.action == "record_payment":
        inst = schemes_svc.get_installment(db, user.id, pa.payload["installment_id"])
        if not inst:
            raise LookupError("Installment no longer exists")
        schemes_svc.record_payment(db, inst, pa.payload.get("amount"))
    pa.status = "confirmed"
    db.commit()
    return {"status": "confirmed", "summary": pa.summary}


REGISTRY = {
    "get_price": get_price,
    "get_price_movement": get_price_movement,
    "list_pending_payments": list_pending_payments,
    "customer_scheme_status": customer_scheme_status,
    "draft_reminder": draft_reminder,
    "propose_record_payment": propose_record_payment,
}


def call_tool(db: Session, user: User, name: str, args: dict) -> dict:
    fn = REGISTRY.get(name)
    if not fn:
        return {"error": f"Unknown tool {name}"}
    try:
        return fn(db, user, **(args or {}))
    except TypeError as e:  # model passed bad arguments
        return {"error": f"Bad arguments: {e}"}
    except Exception as e:
        return {"error": str(e)}
