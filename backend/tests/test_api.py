import io
from datetime import timedelta

from PIL import Image
from sqlalchemy import select

from app.db import today_ist
from app.models import AlertDelivery, Customer, Installment, User
from app.routers.telegram import handle_update
from app.services import alerts as alerts_svc
from app.services import rates as rates_svc
from app.services import reminders as rem_svc
from app.services import schemes as schemes_svc
from tests.conftest import seed_history


class FakeNotifier:
    channel = "fake"

    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def send(self, chat_id, text):
        if self.fail:
            raise RuntimeError("telegram down")
        self.sent.append((chat_id, text))


# ---------- auth / profile (US-01)
def test_signup_login_me(client, auth):
    assert client.post("/auth/signup", json={"email": "raj@example.com", "password": "Password1!",
                                              "confirm_password": "Password1!", "name": "x", "phone": "9000000002"}).status_code == 409
    assert client.post("/auth/login", json={"email": "raj@example.com", "password": "Wrongpass1!"}).status_code == 401
    tok = client.post("/auth/login", json={"email": "RAJ@example.com", "password": "Password1!"}).json()
    me = client.get("/me", headers={"Authorization": f"Bearer {tok['access_token']}"}).json()
    assert me["shop_name"] == "Raj Jewellers" and me["has_logo"] is False


def test_signup_password_validation(client):
    base = {"email": "new@example.com", "name": "New Shop", "phone": "9000000003"}
    weak = {**base, "password": "abc1234", "confirm_password": "abc1234"}
    mismatch = {**base, "password": "Password1!", "confirm_password": "Password2!"}
    assert client.post("/auth/signup", json=weak).status_code == 422
    assert client.post("/auth/signup", json=mismatch).status_code == 422


def test_requires_auth(client):
    assert client.get("/me").status_code == 401
    assert client.get("/customers").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_logo_upload_validation(client, auth):
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), "red").save(buf, "PNG")
    r = client.put("/me/logo", files={"file": ("l.png", buf.getvalue(), "image/png")}, headers=auth)
    assert r.status_code == 200 and r.json()["has_logo"]
    assert client.get("/me/logo", headers=auth).headers["content-type"] == "image/png"
    bad = client.put("/me/logo", files={"file": ("l.png", b"not an image", "image/png")}, headers=auth)
    assert bad.status_code == 400


# ---------- rates, margins, banner (US-02/03/04/16)
def test_rates_and_staleness_and_failure_keeps_last(client, auth, db):
    assert client.post("/rates/refresh", headers=auth).json()["ok"] is True
    t = client.get("/rates/today", headers=auth).json()
    assert t["rates"]["gold"]["display_unit"] == "10g" and t["rates"]["silver"]["display_unit"] == "kg"
    assert "not investment advice" in t["disclaimer"]
    assert t["rates"]["gold"]["stale"] is False

    class Boom:
        name = "boom"

        def fetch(self):
            raise RuntimeError("api down")

    before = rates_svc.latest_rate(db, "gold").price_per_gram
    res = rates_svc.fetch_and_store(db, Boom())
    assert res["ok"] is False
    assert rates_svc.latest_rate(db, "gold").price_per_gram == before  # last known rate retained


def test_margin_applied_and_logged(client, auth, db):
    seed_history(db, 10)
    base = client.get("/rates/today", headers=auth).json()["rates"]["gold"]
    client.put("/margins/gold", json={"margin_percent": 2, "making_per_gram": 50}, headers=auth)
    after = client.get("/rates/today", headers=auth).json()["rates"]["gold"]
    assert after["selling_per_gram"] == round(base["market_per_gram"] * 1.02 + 50, 2)
    assert after["market_per_gram"] == base["market_per_gram"]
    log = client.get("/margins/log", headers=auth).json()
    assert len(log) == 1 and log[0]["new_percent"] == 2 and log[0]["old_percent"] == 0


def test_banner_png(client, auth, db):
    assert client.get("/banner.png", headers=auth).status_code == 409  # no rates yet
    seed_history(db, 5)
    r = client.get("/banner.png", headers=auth)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    img = Image.open(io.BytesIO(r.content))
    assert img.size == (1080, 1080)


# ---------- customers (US-05)
def test_customer_crud_search_isolation(client, auth, auth2):
    c = client.post("/customers", json={"name": "Sunita Devi", "phone": "9876543210"}, headers=auth).json()
    client.post("/customers", json={"name": "Amit", "phone": "9000000001"}, headers=auth)
    assert [x["name"] for x in client.get("/customers?q=sunita", headers=auth).json()] == ["Sunita Devi"]
    assert client.get("/customers", headers=auth2).json() == []
    assert client.patch(f"/customers/{c['id']}", json={"name": "Hack"}, headers=auth2).status_code == 404
    assert client.patch(f"/customers/{c['id']}", json={"opted_out": True}, headers=auth).json()["opted_out"]
    assert client.delete(f"/customers/{c['id']}", headers=auth).status_code == 204


def test_customer_rejects_invalid_phone(client, auth):
    assert client.post("/customers", json={"name": "Invalid", "phone": "kumar"}, headers=auth).status_code == 422


# ---------- alerts (US-06/07/08)
def _dip_today(db, pct):
    """History at a flat 9000 gold, then today is `pct`% lower."""
    t = today_ist()
    for i in range(40, 0, -1):
        rates_svc.store_rates(db, {"gold": 9000.0, "silver": 110.0}, "test", on=t - timedelta(days=i))
    rates_svc.store_rates(db, {"gold": 9000.0 * (1 - pct / 100), "silver": 110.0}, "test", on=t)


def test_rule_fires_once_cooldown_and_customer_optout(client, auth, db):
    _dip_today(db, 5)
    me = db.scalar(select(User))
    me.telegram_chat_id = "owner1"
    c1 = client.post("/customers", json={"name": "A", "phone": "1111111"}, headers=auth).json()
    c2 = client.post("/customers", json={"name": "B", "phone": "2222222"}, headers=auth).json()
    c3 = client.post("/customers", json={"name": "C", "phone": "3333333"}, headers=auth).json()
    for cid, chat in ((c1["id"], "ca"), (c2["id"], "cb"), (c3["id"], "cc")):
        db.get(Customer, cid).telegram_chat_id = chat
    db.get(Customer, c2["id"]).opted_out = True
    db.commit()

    rule = client.post("/alerts/rules", json={"name": "gold dip", "metal": "gold", "threshold": 3,
                                              "audience": "customers"}, headers=auth).json()
    self_rule = client.post("/alerts/rules", json={"name": "mine", "metal": "gold", "threshold": 3}, headers=auth).json()

    n = FakeNotifier()
    out = alerts_svc.run_rules(db, n)
    assert all(o["triggered"] for o in out)
    chats = sorted(c for c, _ in n.sent)
    assert chats == ["ca", "cc", "owner1"]  # opted-out B skipped
    msg = n.sent[0][1]
    assert "5.0% below its 30-day average" in msg and "not investment advice" in msg and "/stop" in msg

    n2 = FakeNotifier()
    out2 = alerts_svc.run_rules(db, n2)  # immediately again -> cooldown
    assert n2.sent == [] and all(o["reason"] == "cooldown" for o in out2)
    d = client.get("/alerts/deliveries", headers=auth).json()
    assert len(d) == 3 and all(x["status"] == "sent" for x in d)
    assert rule["id"] and self_rule["id"]


def test_rule_not_triggered_without_dip_and_failure_recorded(client, auth, db):
    _dip_today(db, 1)
    client.post("/alerts/rules", json={"name": "r", "metal": "gold", "threshold": 3}, headers=auth)
    n = FakeNotifier()
    assert alerts_svc.run_rules(db, n)[0]["triggered"] is False and n.sent == []

    _dip_today(db, 6)
    db.scalar(select(User)).telegram_chat_id = "owner1"
    db.commit()
    alerts_svc.run_rules(db, FakeNotifier(fail=True))
    d = db.scalars(select(AlertDelivery)).all()
    assert d[0].status == "failed" and "telegram down" in d[0].error


def test_rule_test_endpoint_sends_nothing(client, auth, db):
    _dip_today(db, 5)
    rid = client.post("/alerts/rules", json={"name": "r", "metal": "gold", "threshold": 3}, headers=auth).json()["id"]
    r = client.post(f"/alerts/rules/{rid}/test", headers=auth).json()
    assert r["triggered"] and r["pct_below_avg"] == 5.0 and "Raj Jewellers" in r["message_preview"]
    assert db.scalars(select(AlertDelivery)).all() == []


def test_rule_validation(client, auth):
    assert client.post("/alerts/rules", json={"name": "r", "metal": "gold", "threshold": 150}, headers=auth).status_code == 422
    assert client.post("/alerts/rules", json={"name": "r", "metal": "copper", "threshold": 3}, headers=auth).status_code == 422


# ---------- telegram linking
def test_telegram_link_and_stop(client, auth, db):
    cid = client.post("/customers", json={"name": "A", "phone": "1111111"}, headers=auth).json()["id"]
    n = FakeNotifier()
    cust = db.get(Customer, cid)
    assert handle_update(db, {"message": {"chat": {"id": 55}, "text": f"/start c_{cust.link_token}"}}, n) == "linked_customer"
    db.refresh(cust)
    assert cust.telegram_chat_id == "55"
    assert handle_update(db, {"message": {"chat": {"id": 55}, "text": "/stop"}}, n) == "opted_out"
    db.refresh(cust)
    assert cust.opted_out
    assert handle_update(db, {"message": {"chat": {"id": 1}, "text": "/start c_bogus"}}, n) == "invalid_link"
    owner = db.scalar(select(User))
    assert handle_update(db, {"message": {"chat": {"id": 7}, "text": f"/start u_{owner.link_token}"}}, n) == "linked_user"


# ---------- schemes (US-09/10)
def _enrolled(client, auth, db, start=None):
    cid = client.post("/customers", json={"name": "Sunita", "phone": "1111111"}, headers=auth).json()["id"]
    sid = client.post("/schemes", json={"name": "Gold Saver", "monthly_amount": 2000}, headers=auth).json()["id"]
    body = {"customer_id": cid}
    if start:
        body["start_date"] = start.isoformat()
    r = client.post(f"/schemes/{sid}/enrol", json=body, headers=auth)
    assert r.status_code == 201, r.text
    return cid, sid, r.json()


def test_scheme_enrol_pay_maturity(client, auth, db):
    cid, sid, e = _enrolled(client, auth, db, start=today_ist().replace(day=1))
    assert len(e["installments"]) == 11
    assert e["installments"][0]["due_date"] == e["start_date"]
    assert e["maturity_date"] == schemes_svc.add_months(today_ist().replace(day=1), 11).isoformat()
    assert client.post(f"/schemes/{sid}/enrol", json={"customer_id": cid}, headers=auth).status_code == 409
    iid = e["installments"][0]["id"]
    p = client.post(f"/installments/{iid}/pay", json={}, headers=auth).json()
    assert p["status"] == "paid" and p["paid_amount"] == 2000
    assert client.post(f"/installments/{iid}/pay", json={}, headers=auth).status_code == 409
    pend = client.get("/installments?status=pending", headers=auth).json()
    assert pend["count"] == 10
    assert client.delete(f"/customers/{cid}", headers=auth).status_code == 409


def test_add_months_month_end():
    from datetime import date

    assert schemes_svc.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert schemes_svc.add_months(date(2026, 3, 15), 11) == date(2027, 2, 15)


def test_scheme_isolation(client, auth, auth2, db):
    cid, sid, e = _enrolled(client, auth, db)
    iid = e["installments"][0]["id"]
    assert client.post(f"/installments/{iid}/pay", json={}, headers=auth2).status_code == 404
    assert client.post(f"/schemes/{sid}/enrol", json={"customer_id": cid}, headers=auth2).status_code == 404
    assert client.get("/installments", headers=auth2).json()["count"] == 0


def test_reminders_draft_edit_send(client, auth, db):
    cid, sid, e = _enrolled(client, auth, db, start=today_ist() + timedelta(days=3))
    created = client.post("/reminders/generate", headers=auth).json()
    assert len(created) == 1 and created[0]["drafted_by"] == "template" and created[0]["status"] == "draft"
    assert client.post("/reminders/generate", headers=auth).json() == []  # no duplicates
    rid = created[0]["id"]
    n = FakeNotifier()
    r = db.get(rem_svc.Reminder, rid)
    try:
        rem_svc.send_reminder(db, r, n)
        raise AssertionError("should require linked telegram")
    except ValueError as ex:
        assert "not linked" in str(ex)
    db.get(Customer, cid).telegram_chat_id = "99"
    db.commit()
    edited = client.patch(f"/reminders/{rid}", json={"draft_text": "Edited text"}, headers=auth).json()
    assert edited["draft_text"] == "Edited text"
    fresh = db.get(rem_svc.Reminder, rid)
    db.refresh(fresh)  # API edited it via a different session
    rem_svc.send_reminder(db, fresh, n)
    assert n.sent == [("99", "Edited text")]
    assert client.patch(f"/reminders/{rid}", json={"draft_text": "x"}, headers=auth).status_code == 409


def test_reminder_respects_optout(client, auth, db):
    cid, sid, e = _enrolled(client, auth, db, start=today_ist() + timedelta(days=3))
    rem_svc.create_due_reminders(db)
    c = db.get(Customer, cid)
    c.telegram_chat_id, c.opted_out = "9", True
    db.commit()
    r = db.scalars(select(rem_svc.Reminder)).first()
    try:
        rem_svc.send_reminder(db, r, FakeNotifier())
        raise AssertionError("opted-out customer must not be messaged")
    except ValueError as ex:
        assert "opted out" in str(ex)


# ---------- dashboard / backtest (US-13/14)
def test_dashboard_and_backtest(client, auth, db):
    seed_history(db, 100)
    d = client.get("/dashboard?days=30", headers=auth).json()
    assert len(d["charts"]["gold"]) >= 30 and "customers" in d["counts"] and d["disclaimer"]
    b = client.get("/backtest?metal=gold", headers=auth).json()
    assert b["assumptions"]["gst_pct"] == 3.0 and b["verdict"]
    assert client.get("/backtest?metal=gold&window=90", headers=auth).status_code in (200, 409)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
