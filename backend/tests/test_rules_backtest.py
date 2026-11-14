import pytest

from app.services.backtest import run_backtest
from app.services.rules import evaluate_rule


def test_below_avg_triggers():
    prior = [100.0] * 10
    r = evaluate_rule("below_avg_pct", 3, 96.0, prior)
    assert r.triggered and r.pct_below == pytest.approx(4.0)


def test_below_avg_not_triggered_when_small_dip():
    assert not evaluate_rule("below_avg_pct", 3, 98.0, [100.0] * 10).triggered


def test_exact_threshold_triggers():
    assert evaluate_rule("below_avg_pct", 3, 97.0, [100.0] * 10).triggered


def test_not_enough_history_never_triggers():
    r = evaluate_rule("below_avg_pct", 1, 10.0, [100.0, 100.0])
    assert not r.triggered and "not enough history" in r.reason


def test_above_average_does_not_trigger():
    assert not evaluate_rule("below_avg_pct", 3, 110.0, [100.0] * 10).triggered


def test_below_price():
    assert evaluate_rule("below_price", 9000, 8999, []).triggered
    assert not evaluate_rule("below_price", 9000, 9001, []).triggered


def test_unknown_kind():
    with pytest.raises(ValueError):
        evaluate_rule("nope", 1, 1, [1, 1, 1])


def test_backtest_flat_prices_loses_to_nothing_equal():
    res = run_backtest([100.0] * 60, window=30)
    assert res["dip_rule"]["buys"] == 0
    assert res["dip_rule"]["grams"] == 0
    # with no dips, dip rule holds cash: 0% return vs autopay losing GST+spread
    assert res["dip_rule"]["return_pct"] == 0
    assert res["daily_autopay"]["return_pct"] < 0


def test_backtest_includes_costs_and_reports_loss_honestly():
    # steady uptrend: waiting for dips that never come -> dip rule should not "win" by magic
    prices = [100 + i for i in range(80)]
    res = run_backtest(prices, window=30, dip_pct=3)
    assert "WORSE" in res["verdict"] or "beat" in res["verdict"]
    assert res["assumptions"]["gst_pct"] == 3.0 and res["assumptions"]["spread_pct"] == 2.0
    assert res["daily_autopay"]["grams"] > 0


def test_backtest_needs_history():
    with pytest.raises(ValueError):
        run_backtest([100.0] * 10, window=30)


def test_banner_indian_grouping():
    from app.services.banner import inr_group

    assert [inr_group(x) for x in (0, 999, 1000, 87933.1, 107400, 1234567, 12345678)] == [
        "0", "999", "1,000", "87,933", "1,07,400", "12,34,567", "1,23,45,678"]


def test_banner_bundled_font_supports_rupee():
    from app.services.banner import _font

    font, ok = _font(40)
    assert ok is True
    assert font.getmask("\u20b9").getbbox() is not None


def test_sentry_is_noop_without_dsn_and_safe_with_one(monkeypatch):
    from app.observability import init_sentry

    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert init_sentry() is False
    monkeypatch.setenv("SENTRY_DSN", "https://abc@o0.ingest.sentry.io/0")
    assert init_sentry() is True  # init only, no network call
    import sentry_sdk

    assert sentry_sdk.get_client().options["send_default_pii"] is False
    assert sentry_sdk.get_client().options["max_request_body_size"] == "never"
    sentry_sdk.get_client().close()
