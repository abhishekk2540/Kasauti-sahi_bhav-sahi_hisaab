from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Customer, Enrolment, Reminder, Scheme, User
from ..schemas import EnrolIn, EnrolmentOut, PayIn, ReminderEdit, ReminderOut, SchemeIn, SchemeOut
from ..services import reminders as rem_svc
from ..services import schemes as svc
from ..services.notify import get_notifier

router = APIRouter(tags=["schemes"])


def _scheme(db: Session, user: User, sid: int) -> Scheme:
    s = db.get(Scheme, sid)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Scheme not found")
    return s


@router.get("/schemes", response_model=list[SchemeOut])
def list_schemes(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Scheme).where(Scheme.user_id == user.id).order_by(Scheme.id)).all()


@router.post("/schemes", response_model=SchemeOut, status_code=201)
def create_scheme(body: SchemeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = Scheme(user_id=user.id, **body.model_dump())
    db.add(s)
    db.commit()
    return s


@router.post("/schemes/{sid}/enrol", response_model=EnrolmentOut, status_code=201)
def enrol(sid: int, body: EnrolIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _scheme(db, user, sid)
    c = db.get(Customer, body.customer_id)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "Customer not found")
    if db.scalar(select(Enrolment.id).where(Enrolment.scheme_id == sid, Enrolment.customer_id == c.id)):
        raise HTTPException(409, "Customer already enrolled in this scheme")
    return svc.enrol(db, s, c, body.start_date)


@router.get("/schemes/{sid}/enrolments", response_model=list[EnrolmentOut])
def scheme_enrolments(sid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _scheme(db, user, sid)
    return db.scalars(select(Enrolment).where(Enrolment.scheme_id == sid).order_by(Enrolment.id)).all()


@router.get("/installments")
def installments(status: str | None = Query(None, pattern="^(pending|paid)$"),
                 month: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
                 overdue: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = svc.list_installments(db, user.id, status, month, overdue)
    return {"count": len(items), "items": [svc.describe(i) for i in items]}


@router.post("/installments/{iid}/pay")
def pay(iid: int, body: PayIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    inst = svc.get_installment(db, user.id, iid)
    if not inst:
        raise HTTPException(404, "Installment not found")
    try:
        svc.record_payment(db, inst, body.amount, body.paid_on)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return svc.describe(inst) | {"paid_at": inst.paid_at.isoformat(), "paid_amount": inst.paid_amount}


# ---- reminders (AI draft -> owner edits -> owner sends)
@router.post("/reminders/generate", response_model=list[ReminderOut])
def generate(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Drafts reminders for installments due soon, for this user only."""
    created = [r for r in rem_svc.create_due_reminders(db) if r.user_id == user.id]
    return created


@router.get("/reminders", response_model=list[ReminderOut])
def list_reminders(status: str | None = Query(None, pattern="^(draft|sent|failed|dismissed)$"),
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Reminder).where(Reminder.user_id == user.id)
    if status:
        q = q.where(Reminder.status == status)
    return db.scalars(q.order_by(Reminder.id.desc()).limit(100)).all()


def _rem(db: Session, user: User, rid: int) -> Reminder:
    r = db.get(Reminder, rid)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "Reminder not found")
    return r


@router.patch("/reminders/{rid}", response_model=ReminderOut)
def edit_reminder(rid: int, body: ReminderEdit, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = _rem(db, user, rid)
    if r.status == "sent":
        raise HTTPException(409, "Already sent")
    r.draft_text = body.draft_text
    db.commit()
    return r


@router.post("/reminders/{rid}/send", response_model=ReminderOut)
def send_reminder(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = _rem(db, user, rid)
    try:
        return rem_svc.send_reminder(db, r, get_notifier())
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.post("/reminders/{rid}/dismiss", response_model=ReminderOut)
def dismiss_reminder(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = _rem(db, user, rid)
    if r.status == "sent":
        raise HTTPException(409, "Already sent")
    r.status = "dismissed"
    db.commit()
    return r
