"""Price providers. Each returns INR per gram for 24K gold and fine silver.

GoldApiProvider converts international spot (USD/troy oz) to INR/gram. Spot excludes Indian import duty,
GST and local premium, so use RATE_ADJUST_*_PCT to calibrate to what jewellers actually quote.
"""
import hashlib
import math
from datetime import date
from typing import Protocol

import httpx

from ..config import get_settings

TROY_OZ_GRAMS = 31.1034768


class PriceProvider(Protocol):
    name: str

    def fetch(self) -> dict[str, float]: ...


class GoldApiProvider:
    name = "goldapi"
    SPOT_URL = "https://api.gold-api.com/price/{symbol}"  # {"price": <USD per troy oz>, ...}
    FX_URL = "https://open.er-api.com/v6/latest/USD"  # {"rates": {"INR": ...}}

    def fetch(self) -> dict[str, float]:
        s = get_settings()
        with httpx.Client(timeout=10) as c:
            fx = c.get(self.FX_URL)
            fx.raise_for_status()
            usd_inr = float(fx.json()["rates"]["INR"])
            out = {}
            for metal, symbol, adj in (
                ("gold", "XAU", s.rate_adjust_gold_pct),
                ("silver", "XAG", s.rate_adjust_silver_pct),
            ):
                r = c.get(self.SPOT_URL.format(symbol=symbol))
                r.raise_for_status()
                usd_oz = float(r.json()["price"])
                out[metal] = usd_oz * usd_inr / TROY_OZ_GRAMS * (1 + adj / 100)
        if any(v <= 0 for v in out.values()):
            raise ValueError("Provider returned non-positive price")
        return out


class MockProvider:
    """Deterministic synthetic prices (dev/tests only). NOT real market data."""
    name = "mock"
    BASE = {"gold": 9000.0, "silver": 110.0}

    def __init__(self, on: date | None = None):
        self.on = on

    def fetch(self) -> dict[str, float]:
        from ..db import today_ist

        return self.prices_for(self.on or today_ist())

    @classmethod
    def prices_for(cls, d: date) -> dict[str, float]:
        n = d.toordinal()
        out = {}
        for metal, base in cls.BASE.items():
            h = int(hashlib.sha256(f"{metal}{n}".encode()).hexdigest()[:6], 16) / 0xFFFFFF  # 0..1
            wave = math.sin(n / 9.0) * 0.03
            out[metal] = round(base * (1 + wave + (h - 0.5) * 0.02), 2)
        return out


def get_provider() -> PriceProvider:
    return MockProvider() if get_settings().rate_provider == "mock" else GoldApiProvider()
