from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DISCLAIMER
from ..db import get_db, today_ist
from ..deps import current_user
from ..models import MarginChange, User
from ..schemas import MarginChangeOut, MarginIn, MarginOut, Metal
from ..services import rates as svc
from ..services.banner import render_banner

router = APIRouter(tags=["rates"])


@router.get("/rates/today")
def rates_today(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Latest stored rates with 7/30-day comparison. `stale` is true when the last fetch is old (US-02)."""
    return {"disclaimer": DISCLAIMER,
            "rates": {m: svc.rate_snapshot(db, user.id, m) for m in svc.METALS}}


@router.get("/rates/history")
def rates_history(metal: Metal, days: int = Query(30, ge=1, le=365), user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    margin = svc.get_margin(db, user.id, metal)
    return {"metal": metal, "disclaimer": DISCLAIMER, "points": [
        {"date": r.rate_date.isoformat(), "market_per_gram": round(r.price_per_gram, 2),
         "selling_per_gram": round(svc.selling_price(r.price_per_gram, margin), 2)}
        for r in svc.history(db, metal, days)]}


@router.post("/rates/refresh")
def refresh(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Manual fetch. On failure the last known rate is kept and the response says so."""
    return svc.fetch_and_store(db)


@router.get("/margins", response_model=list[MarginOut])
def list_margins(user: User = Depends(current_user), db: Session = Depends(get_db)):
    out = []
    for m in svc.METALS:
        s = svc.get_margin(db, user.id, m)
        out.append(MarginOut(metal=m, margin_percent=s.margin_percent if s else 0.0,
                             making_per_gram=s.making_per_gram if s else 0.0))
    return out


@router.put("/margins/{metal}", response_model=MarginOut)
def put_margin(metal: Metal, body: MarginIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = svc.set_margin(db, user.id, metal, body.margin_percent, body.making_per_gram)
    return MarginOut(metal=metal, margin_percent=m.margin_percent, making_per_gram=m.making_per_gram)


@router.get("/margins/log", response_model=list[MarginChangeOut])
def margin_log(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(MarginChange).where(MarginChange.user_id == user.id)
                      .order_by(MarginChange.changed_at.desc(), MarginChange.id.desc()).limit(100)).all()


@router.get("/banner.png")
def banner(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rates = {}
    for m in svc.METALS:
        snap = svc.rate_snapshot(db, user.id, m)
        if snap:
            rates[m] = (snap["display_price"], snap["display_unit"])
    if not rates:
        raise HTTPException(409, "No rates available yet. Run a refresh first.")
    png = render_banner(user.shop_name, rates, today_ist(), logo=user.logo, phone=user.phone)
    return Response(png, media_type="image/png",
                    headers={"Content-Disposition": f'inline; filename="rates-{today_ist()}.png"'})
