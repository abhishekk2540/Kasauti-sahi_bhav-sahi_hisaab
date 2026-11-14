from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

_settings = get_settings()
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}

engine = create_engine(_settings.database_url, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

IST = timezone(timedelta(hours=5, minutes=30))


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Naive UTC timestamp (all DateTime columns store naive UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today_ist() -> date:
    return datetime.now(IST).date()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "clerk_user_id" in columns:
        with engine.begin() as connection:
            connection.execute(text("DROP INDEX IF EXISTS ix_users_clerk_user_id"))
            connection.execute(text("ALTER TABLE users DROP COLUMN clerk_user_id"))
