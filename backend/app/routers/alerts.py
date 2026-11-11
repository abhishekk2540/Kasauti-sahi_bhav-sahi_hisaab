from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import AlertDelivery, AlertRule, User
from ..schemas import DeliveryOut, RuleIn, RuleOut, RuleUpdate
from ..services import alerts as svc
from ..services.notify import Notifier, get_notifier

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _own(db: Session, user: User, rid: int) -> AlertRule:
    r = db.get(AlertRule, rid)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "Rule not found")
    return r


@router.get("/rules", response_model=list[RuleOut])
def list_rules(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(AlertRule).where(AlertRule.user_id == user.id).order_by(AlertRule.id)).all()


@router.post("/rules", response_model=RuleOut, status_code=201)
def create_rule(body: RuleIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.kind == "below_avg_pct" and body.threshold >= 100:
        raise HTTPException(422, "Percent threshold must be below 100")
    r = AlertRule(user_id=user.id, **body.model_dump())
    db.add(r)
    db.commit()
    return r


@router.patch("/rules/{rid}", response_model=RuleOut)
def update_rule(rid: int, body: RuleUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = _own(db, user, rid)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    db.commit()
    return r


@router.delete("/rules/{rid}", status_code=204)
def delete_rule(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = _own(db, user, rid)
    for d in db.scalars(select(AlertDelivery).where(AlertDelivery.rule_id == rid)):
        db.delete(d)
    db.delete(r)
    db.commit()


@router.post("/rules/{rid}/test")
def test_rule(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Dry run: shows what the rule would do right now. Sends nothing."""
    r = _own(db, user, rid)
    res, _ = svc.evaluate_for_rule(db, r)
    if res is None:
        raise HTTPException(409, "No rates available yet")
    return {"triggered": res.triggered, "reason": res.reason, "current_per_gram": round(res.current, 2),
            "avg_per_gram": round(res.avg, 2) if res.avg else None,
            "pct_below_avg": round(res.pct_below, 2) if res.pct_below is not None else None,
            "message_preview": svc.compose_message(db, user, r, res)}


@router.get("/deliveries", response_model=list[DeliveryOut])
def deliveries(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(AlertDelivery).where(AlertDelivery.user_id == user.id)
                      .order_by(AlertDelivery.created_at.desc(), AlertDelivery.id.desc()).limit(100)).all()
