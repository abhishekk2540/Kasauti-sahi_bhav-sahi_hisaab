from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Metal = Literal["gold", "silver"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth / profile
class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    shop_name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=20)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    email: str
    phone: str | None
    shop_name: str
    has_logo: bool = False
    telegram_linked: bool = False
    telegram_link: str | None = None


class ProfileUpdate(BaseModel):
    shop_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=20)


# ---- rates
class MarginIn(BaseModel):
    margin_percent: float = Field(default=0.0, ge=-50, le=100)
    making_per_gram: float = Field(default=0.0, ge=-100000, le=1000000)


class MarginOut(ORM):
    metal: str
    margin_percent: float
    making_per_gram: float


class MarginChangeOut(ORM):
    metal: str
    old_percent: float
    new_percent: float
    old_per_gram: float
    new_per_gram: float
    changed_at: datetime


# ---- customers
class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=20)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    opted_out: bool | None = None


class CustomerOut(ORM):
    id: int
    name: str
    phone: str
    opted_out: bool
    telegram_linked: bool = False
    telegram_link: str | None = None


# ---- alerts
class RuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    metal: Metal
    kind: Literal["below_avg_pct", "below_price"] = "below_avg_pct"
    window_days: Literal[7, 30] = 30
    threshold: float = Field(gt=0)
    audience: Literal["self", "customers"] = "self"
    cooldown_hours: int = Field(default=24, ge=1, le=24 * 30)
    active: bool = True


class RuleUpdate(BaseModel):
    name: str | None = None
    threshold: float | None = Field(default=None, gt=0)
    window_days: Literal[7, 30] | None = None
    audience: Literal["self", "customers"] | None = None
    cooldown_hours: int | None = Field(default=None, ge=1, le=24 * 30)
    active: bool | None = None


class RuleOut(ORM):
    id: int
    name: str
    metal: str
    kind: str
    window_days: int
    threshold: float
    audience: str
    cooldown_hours: int
    active: bool
    last_triggered_at: datetime | None


class DeliveryOut(ORM):
    id: int
    rule_id: int
    customer_id: int | None
    channel: str
    status: str
    message: str
    error: str | None
    created_at: datetime


# ---- schemes
class SchemeIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    monthly_amount: int = Field(gt=0, le=10_000_000)
    months: int = Field(default=11, ge=1, le=60)


class EnrolIn(BaseModel):
    customer_id: int
    start_date: date | None = None


class PayIn(BaseModel):
    amount: int | None = Field(default=None, gt=0)
    paid_on: date | None = None


class InstallmentOut(ORM):
    id: int
    number: int
    due_date: date
    amount: int
    status: str
    paid_at: date | None
    paid_amount: int | None


class EnrolmentOut(ORM):
    id: int
    customer_id: int
    start_date: date
    maturity_date: date
    installments: list[InstallmentOut]


class SchemeOut(ORM):
    id: int
    name: str
    monthly_amount: int
    months: int
    active: bool


class ReminderOut(ORM):
    id: int
    installment_id: int
    draft_text: str
    drafted_by: str
    status: str
    error: str | None
    created_at: datetime
    sent_at: datetime | None


class ReminderEdit(BaseModel):
    draft_text: str = Field(min_length=1, max_length=2000)


# ---- agent
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatIn(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
