"""SQLAlchemy models. Money in ledger tables is whole rupees (int); market rates are INR/gram floats."""
import secrets
from datetime import date, datetime

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


def _token() -> str:
    return secrets.token_urlsafe(12)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shop_name: Mapped[str] = mapped_column(String(120))
    logo: Mapped[bytes | None] = mapped_column(LargeBinary)
    logo_mime: Mapped[str | None] = mapped_column(String(40))
    telegram_chat_id: Mapped[str | None] = mapped_column(String(40))
    link_token: Mapped[str] = mapped_column(String(32), default=_token, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Rate(Base):
    """One row per metal per day: INR per gram (24K gold / fine silver), market rate before shop margin."""
    __tablename__ = "rates"
    __table_args__ = (UniqueConstraint("metal", "rate_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    metal: Mapped[str] = mapped_column(String(10), index=True)
    rate_date: Mapped[date] = mapped_column(Date, index=True)
    price_per_gram: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(30))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MarginSetting(Base):
    __tablename__ = "margin_settings"
    __table_args__ = (UniqueConstraint("user_id", "metal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    metal: Mapped[str] = mapped_column(String(10))
    margin_percent: Mapped[float] = mapped_column(Float, default=0.0)
    making_per_gram: Mapped[float] = mapped_column(Float, default=0.0)


class MarginChange(Base):
    __tablename__ = "margin_changes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    metal: Mapped[str] = mapped_column(String(10))
    old_percent: Mapped[float] = mapped_column(Float)
    new_percent: Mapped[float] = mapped_column(Float)
    old_per_gram: Mapped[float] = mapped_column(Float)
    new_per_gram: Mapped[float] = mapped_column(Float)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str] = mapped_column(String(20))
    telegram_chat_id: Mapped[str | None] = mapped_column(String(40))
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    link_token: Mapped[str] = mapped_column(String(32), default=_token, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    metal: Mapped[str] = mapped_column(String(10))
    kind: Mapped[str] = mapped_column(String(20))  # below_avg_pct | below_price
    window_days: Mapped[int] = mapped_column(Integer, default=30)  # 7 or 30
    threshold: Mapped[float] = mapped_column(Float)  # percent, or INR/gram for below_price
    audience: Mapped[str] = mapped_column(String(12), default="self")  # self | customers
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"
    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    channel: Mapped[str] = mapped_column(String(20), default="telegram")
    status: Mapped[str] = mapped_column(String(12))  # sent | failed | skipped
    message: Mapped[str] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Scheme(Base):
    __tablename__ = "schemes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    monthly_amount: Mapped[int] = mapped_column(Integer)  # rupees
    months: Mapped[int] = mapped_column(Integer, default=11)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    enrolments: Mapped[list["Enrolment"]] = relationship(back_populates="scheme")


class Enrolment(Base):
    __tablename__ = "enrolments"
    __table_args__ = (UniqueConstraint("scheme_id", "customer_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    maturity_date: Mapped[date] = mapped_column(Date)
    scheme: Mapped[Scheme] = relationship(back_populates="enrolments")
    customer: Mapped[Customer] = relationship()
    installments: Mapped[list["Installment"]] = relationship(
        back_populates="enrolment", order_by="Installment.number", cascade="all, delete-orphan"
    )


class Installment(Base):
    __tablename__ = "installments"
    id: Mapped[int] = mapped_column(primary_key=True)
    enrolment_id: Mapped[int] = mapped_column(ForeignKey("enrolments.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)  # pending | paid
    paid_at: Mapped[date | None] = mapped_column(Date)
    paid_amount: Mapped[int | None] = mapped_column(Integer)
    enrolment: Mapped[Enrolment] = relationship(back_populates="installments")


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    installment_id: Mapped[int] = mapped_column(ForeignKey("installments.id"), index=True)
    draft_text: Mapped[str] = mapped_column(Text)
    drafted_by: Mapped[str] = mapped_column(String(10))  # ai | template
    status: Mapped[str] = mapped_column(String(10), default="draft")  # draft | sent | failed | dismissed
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    installment: Mapped[Installment] = relationship()


class PendingAction(Base):
    """A write proposed by the AI agent. Nothing happens until the user confirms."""
    __tablename__ = "pending_actions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_token)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending | confirmed | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
