"""Daily job, run by cron / GitHub Actions:  python -m app.jobs daily

1) fetch + store rates  2) evaluate alert rules (deterministic)  3) draft scheme reminders for the owner to review.
Safe to run twice a day: rates upsert per day, alerts have a cooldown, reminders are created once per installment.
"""
import json
import sys

from .db import SessionLocal, init_db
from .services import alerts, rates, reminders
from .services.notify import get_notifier


def run_daily() -> dict:
    init_db()
    with SessionLocal() as db:
        fetch = rates.fetch_and_store(db)
        rules = alerts.run_rules(db, get_notifier())
        drafted = reminders.create_due_reminders(db)
    return {"fetch": fetch, "rules": rules, "reminders_drafted": len(drafted)}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if cmd != "daily":
        sys.exit(f"unknown command {cmd}")
    result = run_daily()
    print(json.dumps(result, default=str, indent=2))
    sys.exit(0 if result["fetch"]["ok"] else 1)  # non-zero so the cron run shows red when the price API is down
