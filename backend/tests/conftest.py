import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

os.environ["KASAUTI_SKIP_DOTENV"] = "1"
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["RATE_PROVIDER"] = "mock"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine, today_ist  # noqa: E402
from app.main import app  # noqa: E402
from app.services.providers import MockProvider  # noqa: E402
from app.services.rates import store_rates  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    from app import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture
def client():
    return TestClient(app)


def seed_history(db, days=60, override_today: dict | None = None):
    """Mock prices for the last `days` days, ending today. override_today replaces today's prices."""
    t = today_ist()
    for i in range(days, -1, -1):
        d = t - timedelta(days=i)
        prices = MockProvider.prices_for(d)
        if i == 0 and override_today:
            prices = override_today
        store_rates(db, prices, "mock", on=d)


@pytest.fixture
def auth(client):
    r = client.post("/auth/signup", json={"email": "Raj@Example.com", "password": "Password1!",
                                           "confirm_password": "Password1!", "name": "Raj Jewellers", "phone": "9999900000"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth2(client):
    r = client.post("/auth/signup", json={"email": "other@example.com", "password": "Password1!",
                                           "confirm_password": "Password1!", "name": "Other Shop", "phone": "9000000001"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
