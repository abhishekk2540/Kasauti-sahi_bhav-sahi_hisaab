"""11-month savings scheme ledger (US-09)."""
import calendar
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..db import today_ist
from ..models import Customer, Enrolment, Installment, Scheme


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def enrol(db: Session, scheme: Scheme, customer: Customer, start: date | None = None) -> Enrolment:
    """Creates the enrolment plus one installment per month. First installment is due on the start date."""
    start = start or today_ist()
    e = Enrolment(scheme_id=scheme.id, customer_id=customer.id, start_date=start,
                  maturity_date=add_months(start, scheme.months))
    for n in range(scheme.months):
        e.installments.append(Installment(number=n + 1, due_date=add_months(start, n), amount=scheme.monthly_amount))
    db.add(e)
    db.commit()
    return e


def record_payment(db: Session, inst: Installment, amount: int | None = None, paid_on: date | None = None) -> Installment:
    if inst.status == "paid":
        raise ValueError("Installment already paid")
    inst.status = "paid"
    inst.paid_at = paid_on or today_ist()
    inst.paid_amount = amount if amount is not None else inst.amount
    db.commit()
    return inst


def _base_query(user_id: int):
    return (
        select(Installment)
        .join(Enrolment).join(Scheme)
        .options(joinedload(Installment.enrolment).joinedload(Enrolment.customer),
                 joinedload(Installment.enrolment).joinedload(Enrolment.scheme))
        .where(Scheme.user_id == user_id)
    )


def get_installment(db: Session, user_id: int, installment_id: int) -> Installment | None:
    return db.scalar(_base_query(user_id).where(Installment.id == installment_id))


def list_installments(db: Session, user_id: int, status: str | None = None,
                      month: str | None = None, overdue_only: bool = False) -> list[Installment]:
    q = _base_query(user_id)
    if status:
        q = q.where(Installment.status == status)
    if month:  # "YYYY-MM"
        y, m = (int(x) for x in month.split("-"))
        q = q.where(Installment.due_date >= date(y, m, 1),
                    Installment.due_date <= date(y, m, calendar.monthrange(y, m)[1]))
    if overdue_only:
        q = q.where(Installment.status == "pending", Installment.due_date < today_ist())
    return list(db.scalars(q.order_by(Installment.due_date, Installment.id)).unique())


def describe(inst: Installment) -> dict:
    e = inst.enrolment
    return {
        "installment_id": inst.id, "customer": e.customer.name, "customer_phone": e.customer.phone,
        "scheme": e.scheme.name, "number": inst.number, "of": e.scheme.months,
        "due_date": inst.due_date.isoformat(), "amount": inst.amount, "status": inst.status,
        "overdue": inst.status == "pending" and inst.due_date < today_ist(),
    }
