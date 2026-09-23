import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.daily_review import summarize_day, format_markdown_report, format_executive_summary


def _trade(date_prefix, asset, side, quantity, price):
    return {"timestamp": f"{date_prefix}T12:00:00+00:00", "asset": asset, "side": side,
            "quantity": quantity, "price": price}


def _cycle(asset, action, classification="fresh_buy_cross", crossover_pct=1.0,
           timestamp="2026-09-23T12:00:00+00:00", **extra):
    return {"asset": asset, "classification": classification, "crossover_pct": crossover_pct,
            "action": action, "timestamp": timestamp, **extra}


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


def test_summarize_day_extracts_executed_entries_from_cycle_log():
    cycle_entries = [_cycle("PEPE", "executed", classification="fresh_sell_cross", crossover_pct=-2.5,
                             price=4.46e-06, quantity=1014198, notional=4.52, order_id="abc123")]
    summary = summarize_day(cycle_entries, [], "2026-09-23")
    assert len(summary["executed_entries"]) == 1
    assert summary["executed_entries"][0]["order_id"] == "abc123"


def test_format_executive_summary_explains_why_for_each_action_type():
    cycle_entries = [
        _cycle("PEPE", "executed", classification="fresh_sell_cross", crossover_pct=-2.5,
               timestamp="2026-09-23T15:10:58+00:00", notional=4.52),
        _cycle("BTC", "blocked_cooldown", timestamp="2026-09-23T16:00:00+00:00"),
        _cycle("SOL", "blocked_concurrent_cap", timestamp="2026-09-23T16:05:00+00:00"),
        _cycle("ETH", "blocked_aggregate_cap", timestamp="2026-09-23T16:10:00+00:00"),
        _cycle("DOGE", "blocked_volume", timestamp="2026-09-23T16:15:00+00:00"),
        _cycle("XLM", "excellent_watch", classification="excellent_watch",
               timestamp="2026-09-23T17:00:00+00:00"),
        _cycle("WIF", "recommended", crossover_pct=1.5, notional=250.0,
               timestamp="2026-09-23T17:30:00+00:00"),
        _cycle("MDLN", "protective_exit", classification=None, crossover_pct=None,
               reason="stop_loss", pnl_pct=-10.2, timestamp="2026-09-23T18:00:00+00:00"),
    ]
    summary = summarize_day(cycle_entries, [], "2026-09-23")
    exec_summary = format_executive_summary(summary)

    joined = "\n".join(exec_summary)
    assert "PEPE" in joined and "auto-executed, sold" in joined
    assert "BTC" in joined and "whipsaw cooldown" in joined
    assert "SOL" in joined and "max_concurrent_positions" in joined
    assert "ETH" in joined and "max_aggregate_position_pct" in joined
    assert "DOGE" in joined and "relative volume was below" in joined
    assert "XLM" in joined and "worth a look" in joined
    assert "WIF" in joined and "awaiting approval" in joined
    assert "MDLN" in joined and "stop-loss" in joined and "-10.20%" in joined

    # chronological order preserved
    assert exec_summary.index([l for l in exec_summary if "PEPE" in l][0]) < \
        exec_summary.index([l for l in exec_summary if "MDLN" in l][0])


def test_format_executive_summary_names_quiet_watchlist_assets():
    summary = summarize_day([_cycle("PEPE", "excellent_watch", classification="excellent_watch")],
                             [], "2026-09-23")
    exec_summary = format_executive_summary(summary, watchlist=["PEPE", "BTC", "ETH"])
    joined = "\n".join(exec_summary)
    assert "BTC, ETH" in joined
    assert "held throughout, unchanged" in joined


def test_format_executive_summary_quiet_day_with_no_watchlist_given():
    summary = summarize_day([], [], "2026-09-23")
    exec_summary = format_executive_summary(summary)
    assert exec_summary == ["- No signals of any kind were logged today - a fully quiet day "
                             "across the whole watchlist."]


def test_format_markdown_report_includes_executive_summary_section():
    summary = summarize_day([_cycle("PEPE", "excellent_watch", classification="excellent_watch")],
                             [], "2026-09-23")
    report = format_markdown_report(summary, watchlist=["PEPE", "BTC"])
    assert "## Executive summary" in report
    assert "PEPE" in report
    assert "BTC" in report
