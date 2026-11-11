from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import DISCLAIMER
from ..db import get_db, today_ist, utcnow
from ..deps import current_user
from ..models import AlertDelivery, AlertRule, Customer, Enrolment, Installment, Scheme, User
from ..services import rates as rates_svc
from ..services import schemes as schemes_svc
from ..services.backtest import run_backtest

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(days: int = Query(30, ge=7, le=90), user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Everything the dashboard needs in one call (US-13): chart series, counts, recent activity."""
    today = today_ist()
    active_schemes = db.scalar(select(func.count(Scheme.id)).where(Scheme.user_id == user.id, Scheme.active.is_(True)))
    enrolments = db.scalar(select(func.count(Enrolment.id)).join(Scheme).where(Scheme.user_id == user.id))
    pending = db.scalars(select(Installment).join(Enrolment).join(Scheme)
                         .where(Scheme.user_id == user.id, Installment.status == "pending")).all()
    overdue = [i for i in pending if i.due_date < today]
    recent = db.scalars(select(AlertDelivery).where(AlertDelivery.user_id == user.id)
                        .order_by(AlertDelivery.created_at.desc(), AlertDelivery.id.desc()).limit(10)).all()
    charts = {}
    for m in rates_svc.METALS:
        margin = rates_svc.get_margin(db, user.id, m)
        charts[m] = [{"date": r.rate_date.isoformat(), "selling_per_gram": round(rates_svc.selling_price(
            r.price_per_gram, margin), 2)} for r in rates_svc.history(db, m, days)]
    return {
        "disclaimer": DISCLAIMER,
        "rates": {m: rates_svc.rate_snapshot(db, user.id, m) for m in rates_svc.METALS},
        "charts": charts,
        "counts": {
            "customers": db.scalar(select(func.count(Customer.id)).where(Customer.user_id == user.id)),
            "active_schemes": active_schemes, "enrolments": enrolments,
            "pending_installments": len(pending), "overdue_installments": len(overdue),
            "overdue_amount": sum(i.amount for i in overdue),
            "active_rules": db.scalar(select(func.count(AlertRule.id)).where(
                AlertRule.user_id == user.id, AlertRule.active.is_(True))),
        },
        "recent_alerts": [{"id": d.id, "rule_id": d.rule_id, "status": d.status, "channel": d.channel,
                           "created_at": d.created_at.isoformat() + "Z"} for d in recent],
    }


@router.get("/backtest")
def backtest(metal: str = Query("gold", pattern="^(gold|silver)$"), daily_amount: float = Query(100, gt=0),
             dip_pct: float = Query(3.0, gt=0, lt=50), window: int = Query(30, ge=7, le=90),
             gst_pct: float = Query(3.0, ge=0, le=28), spread_pct: float = Query(2.0, ge=0, le=20),
             user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Dip rule vs daily autopay on stored history. Reports honestly even if the rule loses."""
    from fastapi import HTTPException

    rows = rates_svc.history(db, metal, 3650)
    try:
        result = run_backtest([r.price_per_gram for r in rows], daily_amount, dip_pct, window, gst_pct, spread_pct)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"metal": metal, "from": rows[0].rate_date.isoformat(), "to": rows[-1].rate_date.isoformat(), **result}
