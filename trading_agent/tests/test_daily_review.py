import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.daily_review import summarize_day, format_markdown_report


def _trade(date_prefix, asset, side, quantity, price):
    return {"timestamp": f"{date_prefix}T12:00:00+00:00", "asset": asset, "side": side,
            "quantity": quantity, "price": price}


def _cycle(asset, action, classification="fresh_buy_cross", crossover_pct=1.0, **extra):
    return {"asset": asset, "classification": classification, "crossover_pct": crossover_pct,
            "action": action, **extra}


def test_summarize_day_counts_executed_trades_for_the_date_only():
    trade_log = [
        _trade("2026-09-23", "BTC", "buy", 0.01, 100),
        _trade("2026-09-23", "BTC", "sell", 0.005, 110),
        _trade("2026-09-22", "ETH", "buy", 1, 2000),  # different day, excluded
    ]
    summary = summarize_day([], trade_log, "2026-09-23")
    assert summary["num_executed"] == 2
    assert summary["num_buys"] == 1
    assert summary["num_sells"] == 1
    assert summary["total_notional"] == 0.01 * 100 + 0.005 * 110


def test_summarize_day_buckets_blocked_entries_by_gate():
    cycle_entries = [
        _cycle("BTC", "blocked_cooldown"),
        _cycle("ETH", "blocked_cooldown"),
        _cycle("SOL", "blocked_aggregate_cap"),
    ]
    summary = summarize_day(cycle_entries, [], "2026-09-23")
    assert summary["num_blocked"] == 3
    assert summary["blocked_by_gate"] == {"blocked_cooldown": 2, "blocked_aggregate_cap": 1}


def test_summarize_day_counts_recommended_excellent_watch_and_protective_exits():
    cycle_entries = [
        _cycle("BTC", "recommended"),
        _cycle("ETH", "excellent_watch", classification="excellent_watch"),
        _cycle("PEPE", "protective_exit", classification=None, crossover_pct=None, reason="stop_loss"),
    ]
    summary = summarize_day(cycle_entries, [], "2026-09-23")
    assert summary["num_recommended_pending"] == 1
    assert summary["num_excellent_watch"] == 1
    assert summary["num_protective_exits"] == 1
    assert summary["protective_exit_entries"][0]["reason"] == "stop_loss"


def test_summarize_day_empty_inputs_are_inert():
    summary = summarize_day([], [], "2026-09-23")
    assert summary["num_executed"] == 0
    assert summary["num_blocked"] == 0
    assert summary["blocked_by_gate"] == {}
    assert summary["total_notional"] == 0


def test_format_markdown_report_includes_date_and_counts():
    summary = summarize_day(
        [_cycle("BTC", "blocked_cooldown")],
        [_trade("2026-09-23", "ETH", "buy", 1, 2000)],
        "2026-09-23",
    )
    report = format_markdown_report(summary)
    assert "2026-09-23" in report
    assert "1 total" in report  # executed trades count
    assert "blocked_cooldown: 1" in report


def test_format_markdown_report_includes_notes_section_when_given():
    summary = summarize_day([], [], "2026-09-23")
    report = format_markdown_report(summary, notes="Cooldown blocked 5 signals today - worth revisiting.")
    assert "Observations / possible improvements" in report
    assert "Cooldown blocked 5 signals today" in report


def test_format_markdown_report_omits_notes_section_when_absent():
    summary = summarize_day([], [], "2026-09-23")
    report = format_markdown_report(summary)
    assert "Observations / possible improvements" not in report
