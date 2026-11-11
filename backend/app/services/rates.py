import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import today_ist, utcnow
from ..models import MarginChange, MarginSetting, Rate
from .providers import PriceProvider, get_provider
from .rules import moving_average, pct_below_avg

log = logging.getLogger(__name__)
METALS = ("gold", "silver")


def store_rates(db: Session, prices: dict[str, float], source: str, on: date | None = None) -> None:
    d = on or today_ist()
    for metal, price in prices.items():
        row = db.scalar(select(Rate).where(Rate.metal == metal, Rate.rate_date == d))
        if row:
            row.price_per_gram, row.source, row.fetched_at = price, source, utcnow()
        else:
            db.add(Rate(metal=metal, rate_date=d, price_per_gram=price, source=source, fetched_at=utcnow()))
    db.commit()


def fetch_and_store(db: Session, provider: PriceProvider | None = None) -> dict:
    """Never raises: on failure the last known rate stays in the DB (US-02)."""
    provider = provider or get_provider()
    try:
        prices = provider.fetch()
        store_rates(db, prices, provider.name)
        return {"ok": True, "source": provider.name, "prices": prices}
    except Exception as e:  # network, parse, bad data
        db.rollback()
        log.warning("rate fetch failed: %s", e)
        return {"ok": False, "source": provider.name, "error": str(e)}


def latest_rate(db: Session, metal: str) -> Rate | None:
    return db.scalar(select(Rate).where(Rate.metal == metal).order_by(Rate.rate_date.desc()).limit(1))


def history(db: Session, metal: str, days: int) -> list[Rate]:
    since = today_ist() - timedelta(days=days)
    return list(
        db.scalars(select(Rate).where(Rate.metal == metal, Rate.rate_date >= since).order_by(Rate.rate_date))
    )


def prior_prices(db: Session, metal: str, before: date, window_days: int) -> list[float]:
    """Daily prices in [before - window, before - 1]."""
    rows = db.scalars(
        select(Rate.price_per_gram).where(
            Rate.metal == metal, Rate.rate_date < before, Rate.rate_date >= before - timedelta(days=window_days)
        )
    )
    return list(rows)


def is_stale(rate: Rate) -> bool:
    age = utcnow() - rate.fetched_at
    return age > timedelta(hours=get_settings().stale_after_hours)


def get_margin(db: Session, user_id: int, metal: str) -> MarginSetting | None:
    return db.scalar(select(MarginSetting).where(MarginSetting.user_id == user_id, MarginSetting.metal == metal))


def selling_price(base: float, margin: MarginSetting | None) -> float:
    if not margin:
        return base
    return base * (1 + margin.margin_percent / 100) + margin.making_per_gram


def set_margin(db: Session, user_id: int, metal: str, margin_percent: float, making_per_gram: float) -> MarginSetting:
    m = get_margin(db, user_id, metal)
    old_p, old_g = (m.margin_percent, m.making_per_gram) if m else (0.0, 0.0)
    if not m:
        m = MarginSetting(user_id=user_id, metal=metal)
        db.add(m)
    m.margin_percent, m.making_per_gram = margin_percent, making_per_gram
    db.add(MarginChange(
        user_id=user_id, metal=metal, old_percent=old_p, new_percent=margin_percent,
        old_per_gram=old_g, new_per_gram=making_per_gram,
    ))
    db.commit()
    return m


def to_display(metal: str, per_gram: float) -> tuple[float, str]:
    """Indian convention: gold per 10 g, silver per kg."""
    return (per_gram * 10, "10g") if metal == "gold" else (per_gram * 1000, "kg")


def rate_snapshot(db: Session, user_id: int | None, metal: str) -> dict | None:
    """Latest rate with 7/30-day comparison, margin applied if a user is given."""
    r = latest_rate(db, metal)
    if not r:
        return None
    margin = get_margin(db, user_id, metal) if user_id else None
    sell = selling_price(r.price_per_gram, margin)
    disp, unit = to_display(metal, sell)
    out = {
        "metal": metal,
        "market_per_gram": round(r.price_per_gram, 2),
        "selling_per_gram": round(sell, 2),
        "display_price": round(disp, 2),
        "display_unit": unit,
        "rate_date": r.rate_date.isoformat(),
        "as_of": r.fetched_at.isoformat() + "Z",
        "source": r.source,
        "stale": is_stale(r),
    }
    for w in (7, 30):
        prior = prior_prices(db, metal, r.rate_date, w)
        avg = moving_average(prior) if len(prior) >= 3 else None
        pct = pct_below_avg(r.price_per_gram, avg)
        out[f"avg_{w}d"] = round(avg, 2) if avg else None
        out[f"pct_below_avg_{w}d"] = round(pct, 2) if pct is not None else None
    return out
