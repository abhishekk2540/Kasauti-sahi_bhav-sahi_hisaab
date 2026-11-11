"""Agent eval (US-15). Needs GROQ_API_KEY or ANTHROPIC_API_KEY. Uses a seeded temp DB with mock prices and one scheme customer.

    python -m evals.run_evals            # prints per-case result + accuracy, writes evals/last_run.json
Run it on every prompt/tool/model change and paste the accuracy % into the README.
Checks are deterministic string/tool checks, so the score is repeatable apart from model variance.
"""
import json
import os
import re
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/eval.db"
os.environ["RATE_PROVIDER"] = "mock"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal, init_db, today_ist  # noqa: E402
from app.models import Customer, Scheme, User  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import rates, schemes  # noqa: E402
from app.services.agent.runner import run_agent  # noqa: E402
from app.services.llm import get_llm_client, model_name  # noqa: E402
from app.services.providers import MockProvider  # noqa: E402


def seed(db):
    u = User(email="eval@x.com", password_hash=hash_password("x" * 10), shop_name="Eval Jewellers", phone="9000000000")
    db.add(u)
    db.commit()
    t = today_ist()
    for i in range(60, -1, -1):
        d = t - timedelta(days=i)
        rates.store_rates(db, MockProvider.prices_for(d), "mock", on=d)
    c = Customer(user_id=u.id, name="Sunita Devi", phone="9876543210")
    s = Scheme(user_id=u.id, name="Gold Saver", monthly_amount=2000, months=11)
    db.add_all([c, s])
    db.commit()
    schemes.enrol(db, s, c, t.replace(day=1))
    return u


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*\.?\d*", text) if len(n.replace(",", "")) >= 3}


def grade(case, text, calls, results, pending_created):
    fails = []
    names = [c["name"] for c in calls]
    for t in case.get("expect_tools", []):
        if t not in names:
            fails.append(f"expected tool {t}")
    if case.get("expect_any_tools") and not set(names) & set(case["expect_any_tools"]):
        fails.append(f"expected one of {case['expect_any_tools']}")
    for t in case.get("forbid_tools", []):
        if t in names:
            fails.append(f"forbidden tool {t} called")
    low = text.lower()
    for p in case.get("forbid_phrases", []):
        if p.lower() in low:
            fails.append(f"forbidden phrase: {p}")
    if case.get("must_mention_any") and not any(p.lower() in low for p in case["must_mention_any"]):
        fails.append("missing required hedge")
    if case.get("must_not_claim_done") and re.search(r"\b(done|ho gaya|marked as paid|updated)\b", low) \
            and not re.search(r"confirm", low):
        fails.append("claimed the change was done without mentioning confirmation")
    src = case.get("answer_must_contain_number_from")
    if src:
        facts = " ".join(json.dumps(r["result"]) for r in results if r["name"] == src)
        fact_nums = {str(round(float(n))) for n in re.findall(r"\d+\.?\d*", facts)}
        said = {str(round(float(n))) for n in numbers_in(text) if n.replace(".", "", 1).isdigit()}
        if not (fact_nums & said):
            fails.append("answer contains no number traceable to the tool result")
    return fails


def main() -> int:
    client = get_llm_client()
    if not client:
        print("No AI key set (GROQ_API_KEY or ANTHROPIC_API_KEY); cannot run evals.")
        return 2
    init_db()
    cases = json.loads((Path(__file__).parent / "cases.json").read_text())
    report, passed = [], 0
    with SessionLocal() as db:
        user = seed(db)
        for case in cases:
            text, calls, results, pending = "", [], [], False
            for ev in run_agent(db, user, [{"role": "user", "content": case["q"]}], client):
                if ev["type"] == "text":
                    text += ev["delta"]
                elif ev["type"] == "tool_call":
                    calls.append(ev)
                elif ev["type"] == "tool_result":
                    results.append(ev)
                elif ev["type"] == "pending_action":
                    pending = True
                elif ev["type"] == "error":
                    text += f" [ERROR {ev['message']}]"
            fails = grade(case, text, calls, results, pending)
            passed += not fails
            print(f"{'PASS' if not fails else 'FAIL'}  {case['id']:32s} tools={[c['name'] for c in calls]} {fails or ''}")
            report.append({"id": case["id"], "pass": not fails, "fails": fails, "tools": [c["name"] for c in calls],
                           "answer": text})
    acc = passed / len(cases) * 100
    print(f"\nAccuracy: {passed}/{len(cases)} = {acc:.0f}%")
    (Path(__file__).parent / "last_run.json").write_text(json.dumps(
        {"model": model_name(), "accuracy_pct": round(acc, 1), "cases": report}, indent=2))
    return 0 if acc >= 80 else 1


if __name__ == "__main__":
    sys.exit(main())
