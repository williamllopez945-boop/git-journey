import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.daily_review import summarize_day
from trading_agent.dashboard import build_dashboard, latest_backtest_note, main, render_html

DATE = "2026-10-05"
LIMITS = {"max_concurrent_positions": 5, "max_aggregate_position_pct": 0.60}
EXIT_RULES = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08}


def _cycle(asset, action, time="12:00:00", classification="fresh_buy_cross", crossover_pct=1.0, **extra):
    return {"timestamp": f"{DATE}T{time}+00:00", "asset": asset, "classification": classification,
            "crossover_pct": crossover_pct, "action": action, **extra}


def _trade(asset, side, quantity, price, time="12:00:00"):
    return {"timestamp": f"{DATE}T{time}+00:00", "asset": asset, "side": side,
            "quantity": quantity, "price": price}


def _view(cycle=(), trades=(), **kwargs):
    summary = summarize_day(list(cycle), list(trades), DATE)
    return build_dashboard(summary, LIMITS, dry_run=False, exit_rules=EXIT_RULES, **kwargs)


def _account(n_positions, each_value, portfolio_value=1000.0):
    return {"as_of": f"{DATE}T19:00:00+00:00", "portfolio_value": portfolio_value,
            "positions": [{"asset": f"A{i}", "market_value": each_value} for i in range(n_positions)]}


def test_quiet_day_needs_no_action():
    view = _view()
    assert view["status"] == "NO ACTION"
    assert view["caps"] is None
    assert view["tiles"]["account"] is None


def test_concurrent_cap_binding_is_the_headline():
    view = _view(account=_account(5, 50.0))
    assert view["status"] == "CAPS BINDING"
    assert view["caps"]["concurrent_binding"] is True
    assert view["caps"]["aggregate_binding"] is False
    assert "5 of 5 positions" in view["detail"]


def test_aggregate_cap_binding_uses_market_value_over_portfolio_value():
    view = _view(account=_account(2, 360.0))  # 720 / 1000 = 72% >= 60%
    assert view["caps"]["exposure_pct"] == pytest.approx(72.0)
    assert view["caps"]["aggregate_binding"] is True
    assert view["status"] == "CAPS BINDING"


def test_halt_outranks_caps_and_approvals():
    view = _view(cycle=[_cycle("IR", "recommended")], account=_account(6, 10.0), halted=True)
    assert view["status"] == "HALTED"


def test_pending_approval_when_caps_have_room():
    view = _view(cycle=[_cycle("IR", "recommended"), _cycle("ILMN", "recommended")],
                 account=_account(1, 10.0))
    assert view["status"] == "APPROVAL"
    assert view["pending_approval"] == 2
    assert view["headline"].startswith("2 orders are")


def test_timeline_places_marks_by_utc_time_of_day():
    view = _view(cycle=[
        _cycle("CRV", "executed", time="06:00:00"),
        _cycle("CRV", "executed", time="18:00:00", classification="fresh_sell_cross", reason="stop_loss"),
        _cycle("BTC", "blocked_concurrent_cap", time="12:00:00"),
        _cycle("ETH", "blocked_no_position", time="00:00:00"),
        _cycle("LIT", "excellent_watch", time="23:59:59", classification="excellent_watch"),
    ])
    rows = {r["row"]: r["marks"] for r in view["timeline"]}
    assert [(m["pct"], m["kind"]) for m in rows["Executed"]] == [(25.0, "executed"), (75.0, "protective")]
    assert sorted((m["pct"], m["kind"]) for m in rows["Blocked"]) == [(0.0, "gate"), (50.0, "cap")]
    assert rows["Watch"][0]["pct"] == 100.0
    assert view["tiles"]["protective"] == 1


def test_blocked_by_gate_sorted_and_scaled_to_the_largest():
    view = _view(cycle=[_cycle("A", "blocked_no_position")] * 4 + [_cycle("B", "blocked_cooldown")])
    gates = view["blocked_by_gate"]
    assert [(g["gate"], g["count"], g["width_pct"], g["is_cap"]) for g in gates] == [
        ("no_position", 4, 100, False), ("cooldown", 1, 25, True)]
    assert view["tiles"]["blocked_detail"] == "1 by caps or cooldown"


def test_executed_tile_uses_trade_log_not_cycle_log():
    view = _view(trades=[_trade("CRV", "buy", 160.74, 0.385935823), _trade("CRV", "sell", 160.74, 0.3652983)])
    assert view["tiles"]["executed"] == 2
    assert view["tiles"]["executed_detail"] == "1 buy · 1 sell · $120.75"


def test_research_is_one_item_per_asset_capped_at_four():
    entries = [{"asset": a, "summary": f"{a} note {i}"} for i, a in enumerate("ABACDEF")]
    view = _view(research_entries=entries)
    assert [(r["asset"], r["summary"]) for r in view["research"]] == [
        ("A", "A note 0"), ("B", "B note 1"), ("C", "C note 3"), ("D", "D note 4")]


def test_render_escapes_logged_text_and_shows_dry_run_badge():
    summary = summarize_day([], [], DATE)
    view = build_dashboard(summary, LIMITS, dry_run=True, exit_rules=EXIT_RULES,
                           research_entries=[{"asset": "X<script>", "summary": "a & b"}])
    page = render_html(view)
    assert page.startswith("<!doctype html>")
    assert "X&lt;script&gt;" in page and "<script>" not in page
    assert "a &amp; b" in page
    assert "DRY_RUN = True" in page
    assert "stop 4% · take 8%" in page


def test_render_with_caps_draws_over_cap_slots():
    page = render_html(_view(account=_account(6, 10.0)))
    assert page.count('class="slot over"') == 1
    assert "6 / 5" in page


def test_latest_backtest_note_uses_newest_dated_file_and_first_heading(tmp_path):
    assert latest_backtest_note(tmp_path) is None
    (tmp_path / "backtest_2026-09-23.md").write_text("# Old\n", encoding="utf-8")
    (tmp_path / "backtest_2026-10-02_vpoc.md").write_text("intro\n## VPOC evaluation\n", encoding="utf-8")
    assert latest_backtest_note(tmp_path) == {"file": "backtest_2026-10-02_vpoc.md", "title": "VPOC evaluation"}


def _fixture_files(tmp_path):
    cycle_log = tmp_path / "cycle_log.json"
    state = tmp_path / "state.json"
    research = tmp_path / "research_log.json"
    cycle_log.write_text(json.dumps([_cycle("IR", "recommended"),
                                     {**_cycle("OLD", "executed"), "timestamp": "2026-10-04T12:00:00+00:00"}]),
                         encoding="utf-8")
    state.write_text(json.dumps({"date": DATE, "halted": False, "trade_log": []}), encoding="utf-8")
    research.write_text(json.dumps([{"timestamp": f"{DATE}T08:00:00+00:00", "asset": "TWLO",
                                     "source_type": "news", "summary": "Downgrade."}]), encoding="utf-8")
    return cycle_log, state, research


def test_cli_writes_html_and_leaves_inputs_untouched(tmp_path):
    cycle_log, state, research = _fixture_files(tmp_path)
    account = tmp_path / "account.json"
    account.write_text(json.dumps(_account(2, 100.0)), encoding="utf-8")
    before = {p: p.read_bytes() for p in (cycle_log, state, research, account)}
    out = tmp_path / "dashboard.html"

    main(["--date", DATE, "--out", str(out), "--cycle-log", str(cycle_log), "--state", str(state),
          "--research-log", str(research), "--account-file", str(account), "--backtest-dir", str(tmp_path)])

    page = out.read_text(encoding="utf-8")
    assert "1 order is waiting for your approval." in page
    assert "Downgrade." in page
    assert "OLD" not in page  # other days excluded
    assert {p: p.read_bytes() for p in before} == before


def test_cli_refuses_to_overwrite_a_runtime_file(tmp_path):
    cycle_log, state, research = _fixture_files(tmp_path)
    before = state.read_bytes()
    with pytest.raises(SystemExit):
        main(["--date", DATE, "--out", str(state), "--cycle-log", str(cycle_log), "--state", str(state),
              "--research-log", str(research)])
    with pytest.raises(SystemExit):
        main(["--date", DATE, "--out", str(tmp_path / "x.json"), "--cycle-log", str(cycle_log),
              "--state", str(state), "--research-log", str(research)])
    assert state.read_bytes() == before


def test_cli_handles_missing_runtime_files(tmp_path):
    out = tmp_path / "d.html"
    main(["--date", DATE, "--out", str(out), "--cycle-log", str(tmp_path / "none.json"),
          "--state", str(tmp_path / "none2.json"), "--research-log", str(tmp_path / "none3.json"),
          "--backtest-dir", str(tmp_path)])
    assert "No owner action needed today." in out.read_text(encoding="utf-8")
