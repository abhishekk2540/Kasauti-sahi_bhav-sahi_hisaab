"""Groq / OpenAI-compatible path, tested with a scripted fake that streams chunks like the real SDK does."""
import json
from types import SimpleNamespace as NS

from sqlalchemy import select

from app.models import Installment, User
from app.services.agent.runner import run_agent
from tests.conftest import seed_history
from tests.test_api import _enrolled


def _chunk(content=None, tool_calls=None):
    return NS(choices=[NS(delta=NS(content=content, tool_calls=tool_calls))])


def _tc(index, id=None, name=None, args=None):
    return NS(index=index, id=id, function=NS(name=name, arguments=args))


class FakeOpenAI:
    """steps: list of chunk lists, one per model turn. Records every request."""

    def __init__(self, steps):
        self.steps, self.calls = list(steps), []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.calls.append(json.loads(json.dumps(kw, default=str)))
        return iter(self.steps.pop(0))


def _user(db):
    return db.scalar(select(User))


def test_groq_tool_call_split_across_chunks_then_answer(client, auth, db):
    seed_history(db, 40)
    c = FakeOpenAI([
        [_chunk(tool_calls=[_tc(0, id="call_1", name="get_price", args="")]),
         _chunk(tool_calls=[_tc(0, args='{"metal": ')]),
         _chunk(tool_calls=[_tc(0, args='"gold"}')])],
        [_chunk("Aaj "), _chunk("gold ka bhav...")],
    ])
    evs = list(run_agent(db, _user(db), [{"role": "user", "content": "gold kitna hai?"}], c))
    assert [e["type"] for e in evs] == ["tool_call", "tool_result", "text", "text", "done"]
    assert evs[0]["input"] == {"metal": "gold"}
    assert "market_per_gram" in evs[1]["result"]
    second = c.calls[1]["messages"]
    assert second[0]["role"] == "system"
    assert second[-2]["tool_calls"][0]["function"]["arguments"] == '{"metal": "gold"}'
    assert second[-1]["role"] == "tool" and second[-1]["tool_call_id"] == "call_1"
    assert "market_per_gram" in second[-1]["content"]
    assert c.calls[0]["tools"][0]["type"] == "function" and c.calls[0]["stream"] is True


def test_groq_bad_json_args_become_tool_error_not_crash(client, auth, db):
    c = FakeOpenAI([[_chunk(tool_calls=[_tc(0, id="c1", name="get_price", args="{not json")])],
                    [_chunk("Dobara try karta hoon.")]])
    evs = list(run_agent(db, _user(db), [{"role": "user", "content": "x"}], c))
    res = [e for e in evs if e["type"] == "tool_result"][0]["result"]
    assert "error" in res and evs[-1]["type"] == "done"


def test_groq_never_writes_without_confirmation(client, auth, db):
    cid, sid, e = _enrolled(client, auth, db)
    iid = e["installments"][0]["id"]
    c = FakeOpenAI([[_chunk(tool_calls=[_tc(0, id="c1", name="propose_record_payment",
                                            args=json.dumps({"installment_id": iid}))])],
                    [_chunk("Confirm karein.")]])
    evs = list(run_agent(db, _user(db), [{"role": "user", "content": "mark paid"}], c))
    pa = [x for x in evs if x["type"] == "pending_action"]
    assert len(pa) == 1
    inst = db.get(Installment, iid)
    db.refresh(inst)
    assert inst.status == "pending"
    assert client.post(f"/agent/confirm/{pa[0]['id']}", headers=auth).status_code == 200


def test_groq_parallel_tool_calls(client, auth, db):
    seed_history(db, 40)
    c = FakeOpenAI([[_chunk(tool_calls=[_tc(0, id="a", name="get_price", args='{"metal":"gold"}'),
                                        _tc(1, id="b", name="get_price", args='{"metal":"silver"}')])],
                    [_chunk("Dono rates ready.")]])
    evs = list(run_agent(db, _user(db), [{"role": "user", "content": "gold aur silver"}], c))
    assert [e["result"]["metal"] for e in evs if e["type"] == "tool_result"] == ["gold", "silver"]
    tool_msgs = [m for m in c.calls[1]["messages"] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["a", "b"]


def test_groq_api_error_reported(client, auth, db):
    class Boom:
        chat = NS(completions=NS(create=lambda **k: (_ for _ in ()).throw(RuntimeError("401 invalid key"))))

    evs = list(run_agent(db, _user(db), [{"role": "user", "content": "x"}], Boom()))
    assert any(e["type"] == "error" and "401" in e["message"] for e in evs) and evs[-1]["type"] == "done"


def test_provider_selection(monkeypatch):
    from app import config
    from app.services import llm

    def fresh(**env):
        for k in ("LLM_PROVIDER", "GROQ_API_KEY", "ANTHROPIC_API_KEY", "GROQ_MODEL"):
            monkeypatch.delenv(k, raising=False)
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        config.get_settings.cache_clear()
        return config.get_settings()

    s = fresh(GROQ_API_KEY="gsk_x")
    assert s.llm_provider == "groq" and s.groq_model == "openai/gpt-oss-20b" and llm.model_name() == "openai/gpt-oss-20b"
    client = llm.get_llm_client()
    assert llm.is_openai_style(client) and "groq.com" in str(client.base_url)
    assert fresh(ANTHROPIC_API_KEY="k").llm_provider == "anthropic"
    assert fresh(GROQ_API_KEY="g", ANTHROPIC_API_KEY="a", LLM_PROVIDER="anthropic").llm_provider == "anthropic"
    fresh()
    assert llm.get_llm_client() is None
    config.get_settings.cache_clear()


def test_simple_complete_groq():
    from app.services import llm

    msg = NS(content="  Namaste, installment due hai.  ")
    c = NS(chat=NS(completions=NS(create=lambda **k: NS(choices=[NS(message=msg)]))))
    assert llm.simple_complete(c, "sys", "user") == "Namaste, installment due hai."
