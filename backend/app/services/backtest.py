"""Honest backtest: dip-rule buying vs plain daily autopay on stored history (US-14).

Both strategies get the same total budget (daily_amount per day) and pay the same GST + dealer spread per purchase,
so the only difference is *timing*. Dip strategy accumulates cash and spends the whole pot when price is at least
`dip_pct` below the prior `window`-day average. Unspent cash at the end counts as cash (no interest).
"""
from dataclasses import dataclass, asdict

from .rules import MIN_POINTS


@dataclass
class StrategyResult:
    name: str
    budget: float
    spent: float
    unspent_cash: float
    grams: float
    avg_cost_per_gram: float | None
    final_value: float  # grams * last market price + unspent cash
    return_pct: float  # final_value vs budget, after GST + spread
    buys: int


def _buy(amount: float, price: float, gst_pct: float, spread_pct: float) -> float:
    """Grams obtained for a rupee amount after GST and dealer spread."""
    return (amount / (1 + gst_pct / 100)) / (price * (1 + spread_pct / 100))


def _summarise(name, budget, spent, cash, grams, last_price, buys) -> StrategyResult:
    value = grams * last_price + cash
    return StrategyResult(
        name=name, budget=round(budget, 2), spent=round(spent, 2), unspent_cash=round(cash, 2),
        grams=round(grams, 4), avg_cost_per_gram=round(spent / grams, 2) if grams else None,
        final_value=round(value, 2), return_pct=round((value / budget - 1) * 100, 2), buys=buys,
    )


def run_backtest(prices: list[float], daily_amount: float = 100.0, dip_pct: float = 3.0, window: int = 30,
                 gst_pct: float = 3.0, spread_pct: float = 2.0) -> dict:
    if len(prices) < window + 10:
        raise ValueError(f"Need at least {window + 10} days of history, have {len(prices)}")
    last = prices[-1]

    # A: daily autopay
    g_a = sum(_buy(daily_amount, p, gst_pct, spread_pct) for p in prices)
    budget = daily_amount * len(prices)
    a = _summarise("daily_autopay", budget, budget, 0.0, g_a, last, len(prices))

    # B: dip rule
    pot = grams = spent = 0.0
    buys = 0
    for i, p in enumerate(prices):
        pot += daily_amount
        prior = prices[max(0, i - window):i]
        if len(prior) >= MIN_POINTS and p <= (sum(prior) / len(prior)) * (1 - dip_pct / 100):
            grams += _buy(pot, p, gst_pct, spread_pct)
            spent += pot
            pot = 0.0
            buys += 1
    b = _summarise("dip_rule", budget, spent, pot, grams, last, buys)

    diff = round(b.return_pct - a.return_pct, 2)
    if diff > 0:
        verdict = f"Dip rule beat daily autopay by {diff} percentage points on this history."
    elif diff < 0:
        verdict = f"Dip rule did WORSE than daily autopay by {abs(diff)} percentage points on this history."
    else:
        verdict = "Both strategies performed the same on this history."
    return {
        "assumptions": {"daily_amount": daily_amount, "dip_pct": dip_pct, "window_days": window,
                        "gst_pct": gst_pct, "spread_pct": spread_pct, "days": len(prices),
                        "note": "Past results do not predict future prices. Not investment advice."},
        "daily_autopay": asdict(a), "dip_rule": asdict(b), "verdict": verdict,
    }
