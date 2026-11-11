from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Customer, User
from ..schemas import CustomerIn, CustomerOut, CustomerUpdate
from ..services.notify import deep_link

router = APIRouter(prefix="/customers", tags=["customers"])


def _out(c: Customer) -> CustomerOut:
    return CustomerOut(id=c.id, name=c.name, phone=c.phone, opted_out=c.opted_out,
                       telegram_linked=bool(c.telegram_chat_id), telegram_link=deep_link("c", c.link_token))


def _own(db: Session, user: User, cid: int) -> Customer:
    c = db.get(Customer, cid)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "Customer not found")
    return c


@router.get("", response_model=list[CustomerOut])
def list_customers(q: str | None = Query(None, max_length=60), user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    stmt = select(Customer).where(Customer.user_id == user.id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Customer.name.ilike(like), Customer.phone.ilike(like)))
    return [_out(c) for c in db.scalars(stmt.order_by(Customer.name))]


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(body: CustomerIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = Customer(user_id=user.id, name=body.name, phone=body.phone)
    db.add(c)
    db.commit()
    return _out(c)


@router.patch("/{cid}", response_model=CustomerOut)
def update_customer(cid: int, body: CustomerUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = _own(db, user, cid)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    return _out(c)


@router.delete("/{cid}", status_code=204)
def delete_customer(cid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..models import Enrolment

    c = _own(db, user, cid)
    if db.scalar(select(Enrolment.id).where(Enrolment.customer_id == cid)):
        raise HTTPException(409, "Customer is enrolled in a scheme; cannot delete (opt them out instead)")
    db.delete(c)
    db.commit()
