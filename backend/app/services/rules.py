"""Deterministic alert rule engine. No LLM involved anywhere in here (US-08)."""
from dataclasses import dataclass

MIN_POINTS = 3  # need at least this many prior days to compute a meaningful average


@dataclass
class RuleResult:
    triggered: bool
    current: float
    avg: float | None
    pct_below: float | None  # positive = current is below the average
    reason: str


def moving_average(prices: list[float]) -> float | None:
    return sum(prices) / len(prices) if prices else None


def pct_below_avg(current: float, avg: float | None) -> float | None:
    if not avg:
        return None
    return (avg - current) / avg * 100


def evaluate_rule(kind: str, threshold: float, current: float, prior_prices: list[float]) -> RuleResult:
    """`prior_prices` = daily prices of the window *before* today (today excluded)."""
    avg = moving_average(prior_prices) if len(prior_prices) >= MIN_POINTS else None
    pct = pct_below_avg(current, avg)

    if kind == "below_price":
        hit = current <= threshold
        reason = f"current {current:.2f} {'<=' if hit else '>'} target {threshold:.2f}"
        return RuleResult(hit, current, avg, pct, reason)

    if kind == "below_avg_pct":
        if avg is None:
            return RuleResult(False, current, None, None, f"not enough history (need {MIN_POINTS}+ days)")
        hit = pct >= threshold
        reason = f"{pct:.2f}% below average, threshold {threshold:.2f}%"
        return RuleResult(hit, current, avg, pct, reason)

    raise ValueError(f"unknown rule kind: {kind}")
