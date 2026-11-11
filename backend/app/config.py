"""Central settings, read from environment variables."""
import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# Reads backend/.env if present. Real environment variables always win. Tests set KASAUTI_SKIP_DOTENV=1.
if not os.getenv("KASAUTI_SKIP_DOTENV"):
    load_dotenv()

DISCLAIMER = (
    "Rates are indicative only and not investment advice. "
    "Final price is set by the shop at the time of purchase."
)

_DEV_SECRET = "dev-secret-change-me"


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./kasauti.db")
    # Neon/Supabase/Railway hand out postgres:// or postgresql:// URLs; use psycopg v3.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@dataclass(frozen=True)
class Settings:
    env: str
    database_url: str
    jwt_secret: str
    jwt_expire_hours: int
    cors_origins: list[str]
    rate_provider: str  # "goldapi" | "mock"
    rate_adjust_gold_pct: float  # calibrate to Indian retail (import duty etc.)
    rate_adjust_silver_pct: float
    stale_after_hours: int
    llm_provider: str  # "groq" | "anthropic"
    groq_api_key: str | None
    groq_model: str
    anthropic_api_key: str | None
    anthropic_model: str
    telegram_bot_token: str | None
    telegram_bot_username: str | None
    telegram_webhook_secret: str | None
    reminder_days_before: int


@lru_cache
def get_settings() -> Settings:
    s = Settings(
        env=os.getenv("APP_ENV", "development"),
        database_url=_db_url(),
        jwt_secret=os.getenv("JWT_SECRET", _DEV_SECRET),
        jwt_expire_hours=int(os.getenv("JWT_EXPIRE_HOURS", "72")),
        cors_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()],
        rate_provider=os.getenv("RATE_PROVIDER", "goldapi"),
        rate_adjust_gold_pct=float(os.getenv("RATE_ADJUST_GOLD_PCT", "0")),
        rate_adjust_silver_pct=float(os.getenv("RATE_ADJUST_SILVER_PCT", "0")),
        stale_after_hours=int(os.getenv("STALE_AFTER_HOURS", "36")),
        llm_provider=(os.getenv("LLM_PROVIDER") or ("groq" if os.getenv("GROQ_API_KEY") else "anthropic")).lower(),
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_bot_username=os.getenv("TELEGRAM_BOT_USERNAME") or None,
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET") or None,
        reminder_days_before=int(os.getenv("REMINDER_DAYS_BEFORE", "3")),
    )
    if s.env == "production" and s.jwt_secret == _DEV_SECRET:
        raise RuntimeError("Set JWT_SECRET in production")
    return s
