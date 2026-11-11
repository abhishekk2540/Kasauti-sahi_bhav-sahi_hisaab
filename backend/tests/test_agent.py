"""Agent tests use a scripted fake LLM client, so they test OUR loop, tools and safety rules, not the model."""
import json
from types import SimpleNamespace as NS

from sqlalchemy import select

from app.db import today_ist
from app.models import Installment, PendingAction, User
from app.services.agent import tools
from app.services.agent.runner import run_agent
from tests.conftest import seed_history
from tests.test_api import _enrolled


class FakeStream:
    def __init__(self, text, content, stop):
        self.text_stream, self._final = iter(text), NS(content=content, stop_reason=stop)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self._final


class ScriptedClient:
    """Each script step = (text_chunks, [tool_use dicts]). Records what the model was sent."""

    def __init__(self, steps):
        self.steps, self.calls = list(steps), []
        self.messages = NS(stream=self._stream)

    def _stream(self, **kw):
        self.calls.append(kw)
        text, tool_uses = self.steps.pop(0)
        content = [NS(type="text", text="".join(text))] + [
            NS(type="tool_use", id=f"tu{i}", name=t[0], input=t[1]) for i, t in enumerate(tool_uses)]
        return FakeStream(text, content, "tool_use" if tool_uses else "end_turn")


def _user(db):
    return db.scalar(select(User))


def test_agent_streams_tool_call_and_result(client, auth, db):
    seed_history(db, 40)
    c = ScriptedClient([([], [("get_price", {"metal": "gold"})]), (["Aaj ", "gold ", "ka bhav..."], [])])
    evs = list(run_agent(db, _user(db), [{"role": "user", "content": "gold kitna hai?"}], c))
    types = [e["type"] for e in evs]
    assert types == ["tool_call", "tool_result", "text", "text", "text", "done"]
    assert evs[0]["name"] == "get_price"
    assert evs[1]["result"]["metal"] == "gold" and "market_per_gram" in evs[1]["result"]
    # tool result was fed back to the model as JSON from the DB
    sent = c.calls[1]["messages"][-1]["content"][0]
    assert sent["type"] == "tool_result" and "market_per_gram" in sent["content"]


def test_agent_never_changes_data_without_confirmation(client, auth, db):
    cid, sid, e = _enrolled(client, auth, db)
    iid = e["installments"][0]["id"]
    c = ScriptedClient([([], [("propose_record_payment", {"installment_id": iid})]), (["Confirm karein."], [])])
    evs = list(run_agent(db, _user(db), [{"role": "user", "content": "Sunita ki payment mark karo"}], c))
    pa = [e for e in evs if e["type"] == "pending_action"]
    assert len(pa) == 1
    inst = db.get(Installment, iid)
    db.refresh(inst)
    assert inst.status == "pending"  # NOT changed yet

    # confirming via the API is the only thing that changes it
    r = client.post(f"/agent/confirm/{pa[0]['id']}", headers=auth)
    assert r.status_code == 200
    db.refresh(inst)
    assert inst.status == "paid"
    assert client.post(f"/agent/confirm/{pa[0]['id']}", headers=auth).status_code == 409  # not replayable


def test_cancel_and_cross_user_confirm_blocked(client, auth, auth2, db):
    cid, sid, e = _enrolled(client, auth, db)
    iid = e["installments"][0]["id"]
    out = tools.propose_record_payment(db, _user(db), iid)
    aid = out["pending_action_id"]
    assert client.post(f"/agent/confirm/{aid}", headers=auth2).status_code == 404
    assert client.post(f"/agent/cancel/{aid}", headers=auth).json()["status"] == "cancelled"
    assert client.post(f"/agent/confirm/{aid}", headers=auth).status_code == 409
    assert db.get(Installment, iid).status == "pending"


def test_tools_are_user_scoped(client, auth, auth2, db):
    cid, sid, e = _enrolled(client, auth, db)
    other = db.scalars(select(User).where(User.email == "other@example.com")).one()
    assert tools.list_pending_payments(db, other)["count"] == 0
    assert tools.customer_scheme_status(db, other, "Sunita").get("error")
    assert tools.draft_reminder(db, other, e["installments"][0]["id"]).get("error")
    assert tools.propose_record_payment(db, other, e["installments"][0]["id"]).get("error")


def test_tool_errors_do_not_crash_loop(client, auth, db):
    c = ScriptedClient([([], [("get_price", {"metal": "gold"}), ("nonexistent", {}), ("get_price", {"bad": 1})]),
                        (["Rate abhi available nahi hai."], [])])
    evs = list(run_agent(db, _user(db), [{"role": "user", "content": "x"}], c))
    results = [e["result"] for e in evs if e["type"] == "tool_result"]
    assert all("error" in r for r in results) and evs[-1]["type"] == "done"


def test_pending_payments_tool_month_filter(client, auth, db):
    _enrolled(client, auth, db, start=today_ist().replace(day=1))
    m = today_ist().strftime("%Y-%m")
    res = tools.list_pending_payments(db, _user(db), month=m)
    assert res["count"] == 1 and res["items"][0]["customer"] == "Sunita" and res["total_amount"] == 2000
    assert "error" in tools.list_pending_payments(db, _user(db), month="bogus")


def test_agent_without_api_key_reports_cleanly(client, auth):
    r = client.post("/agent/chat", json={"messages": [{"role": "user", "content": "hi"}]}, headers=auth)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = [json.loads(l[6:]) for l in r.text.split("\n\n") if l.startswith("data: ")]
    assert events[0]["type"] == "error" and events[-1]["type"] == "done"


def test_chat_endpoint_validates(client, auth):
    assert client.post("/agent/chat", json={"messages": []}, headers=auth).status_code == 422
    r = client.post("/agent/chat", json={"messages": [{"role": "assistant", "content": "hi"}]}, headers=auth)
    assert r.status_code == 422
    assert client.post("/agent/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 401


def test_agent_step_limit(client, auth, db):
    c = ScriptedClient([([], [("get_price", {"metal": "gold"})])] * 10)
    evs = list(run_agent(db, _user(db), [{"role": "user", "content": "loop"}], c))
    assert any(e["type"] == "error" and "too many" in e["message"] for e in evs)
