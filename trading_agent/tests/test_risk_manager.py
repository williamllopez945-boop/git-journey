import os
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.risk_manager import RiskManager
from trading_agent.cost_basis_fallback import average_cost_basis_from_trade_log

LIMITS = {
    "max_position_pct": 0.05,
    "daily_loss_limit_pct": 0.03,
    "max_trades_per_day": 3,
    "auto_execute_max_pct": 0.05,
}


def _new_manager():
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
    tmp.unlink()  # start with no existing state file
    return RiskManager(LIMITS, state_path=tmp)


def test_position_size_respects_max_position_pct():
    rm = _new_manager()
    # portfolio $10,000, max 5% => $500 cap, price $100 => 5 units
    assert rm.position_size(portfolio_value=10_000, price=100) == 5.0


def test_position_size_accounts_for_existing_holding():
    rm = _new_manager()
    # already holding $400 of the $500 cap => only $100 of room left
    assert rm.position_size(10_000, price=100, current_position_value=400) == 1.0


def test_can_trade_respects_daily_trade_cap():
    rm = _new_manager()
    for _ in range(LIMITS["max_trades_per_day"]):
        assert rm.can_trade()
        rm.record_trade("BTC", "buy", 1, 100)
    assert not rm.can_trade()


def test_protective_trade_does_not_consume_a_daily_slot():
    # 2026-09-28 owner request: stop-loss/take-profit exits are
    # "non-negotiable trades that will execute and does not count
    # towards our daily trades."
    rm = _new_manager()
    for _ in range(LIMITS["max_trades_per_day"]):
        rm.record_trade("BTC", "sell", 1, 100, protective=True)
    # every slot is still open - none of those protective exits counted
    assert rm.can_trade()
    assert rm.state["trades_today"] == 0
    # trade_log still records them, for cost-basis/daily-review purposes
    assert len(rm.state["trade_log"]) == LIMITS["max_trades_per_day"]


def test_protective_trade_still_logs_alongside_ordinary_trades():
    rm = _new_manager()
    rm.record_trade("BTC", "buy", 1, 100)  # ordinary - counts
    rm.record_trade("BTC", "sell", 1, 90, protective=True)  # protective - doesn't
    assert rm.state["trades_today"] == 1
    assert len(rm.state["trade_log"]) == 2


def test_circuit_breaker_halts_past_daily_loss_limit():
    rm = _new_manager()
    rm.start_of_day(equity=10_000)
    assert rm.check_circuit_breaker(current_equity=9_800) is False  # 2% down
    assert rm.check_circuit_breaker(current_equity=9_600) is True  # 4% down
    assert not rm.can_trade()


def test_can_auto_execute_at_or_under_threshold():
    rm = _new_manager()
    # auto_execute_max_pct=0.05, portfolio $100 -> $5 threshold
    assert rm.can_auto_execute(5.0, portfolio_value=100) is True
    assert rm.can_auto_execute(2.50, portfolio_value=100) is True


def test_can_auto_execute_over_threshold():
    rm = _new_manager()
    assert rm.can_auto_execute(5.01, portfolio_value=100) is False
    assert rm.can_auto_execute(25.0, portfolio_value=100) is False


def test_can_auto_execute_scales_with_portfolio_value():
    rm = _new_manager()
    # same order notional, larger portfolio -> threshold rises with it
    assert rm.can_auto_execute(50.0, portfolio_value=1_000) is True
    assert rm.can_auto_execute(50.0, portfolio_value=100) is False


def test_can_auto_execute_defaults_to_false_without_configured_limit():
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
    tmp.unlink()
    rm = RiskManager({"max_position_pct": 0.05, "daily_loss_limit_pct": 0.03, "max_trades_per_day": 3}, state_path=tmp)
    assert rm.can_auto_execute(0.01, portfolio_value=1_000_000) is False


def test_position_size_override_replaces_configured_cap():
    rm = _new_manager()
    # configured cap is 5% ($500 of $10,000); override to 1% ($100)
    assert rm.position_size(10_000, price=100, max_position_pct=0.01) == 1.0


def test_position_size_without_override_uses_configured_cap():
    rm = _new_manager()
    assert rm.position_size(10_000, price=100) == rm.position_size(10_000, price=100, max_position_pct=None)


def test_can_open_new_position_uncapped_when_not_configured():
    rm = _new_manager()  # LIMITS has no max_concurrent_positions key
    assert rm.can_open_new_position(open_position_count=1000) is True


def test_can_open_new_position_respects_configured_cap():
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
    tmp.unlink()
    limits = dict(LIMITS, max_concurrent_positions=5)
    rm = RiskManager(limits, state_path=tmp)
    assert rm.can_open_new_position(open_position_count=4) is True
    assert rm.can_open_new_position(open_position_count=5) is False
    assert rm.can_open_new_position(open_position_count=6) is False


def test_can_open_new_position_none_value_means_uncapped():
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
    tmp.unlink()
    limits = dict(LIMITS, max_concurrent_positions=None)
    rm = RiskManager(limits, state_path=tmp)
    assert rm.can_open_new_position(open_position_count=1000) is True


def test_position_size_ignores_aggregate_cap_when_not_configured():
    rm = _new_manager()  # LIMITS has no max_aggregate_position_pct key
    # per-asset cap alone: 5% of 10,000 = 500 -> 5 units at price 100
    assert rm.position_size(10_000, price=100, total_open_position_value=9_000) == 5.0


def test_position_size_clamped_by_aggregate_cap():
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
    tmp.unlink()
    limits = dict(LIMITS, max_position_pct=0.50, max_aggregate_position_pct=0.50)
    rm = RiskManager(limits, state_path=tmp)
    # portfolio $10,000, aggregate cap 50% = $5,000, already $4,800 deployed
    # -> only $200 of aggregate room left, even though the per-asset cap
    # (50% = $5,000) would otherwise allow far more.
    assert rm.position_size(10_000, price=100, total_open_position_value=4_800) == 2.0


def test_position_size_zero_when_aggregate_cap_already_reached():
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
    tmp.unlink()
    limits = dict(LIMITS, max_position_pct=0.50, max_aggregate_position_pct=0.50)
    rm = RiskManager(limits, state_path=tmp)
    assert rm.position_size(10_000, price=100, total_open_position_value=5_000) == 0.0
    assert rm.position_size(10_000, price=100, total_open_position_value=6_000) == 0.0


def test_day_rollover_resets_daily_counters_but_keeps_trade_log():
    # Simulate yesterday's state on disk, including a real trade.
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
    stale_state = {
        "date": "2000-01-01",  # guaranteed not today
        "starting_equity": 10_000.0,
        "trades_today": 2,
        "halted": True,
        "trade_log": [
            {"timestamp": "2000-01-01T12:00:00+00:00", "asset": "PEPE",
             "side": "buy", "quantity": 1000, "price": 0.001},
        ],
    }
    tmp.write_text(json.dumps(stale_state))

    rm = RiskManager(LIMITS, state_path=tmp)
    # Day-scoped fields reset for the new day.
    assert rm.state["trades_today"] == 0
    assert rm.state["halted"] is False
    assert rm.state["starting_equity"] is None
    # Trade history is NOT day-scoped - it must survive the rollover, or
    # a position bought yesterday and exited today loses its cost basis
    # (cost_basis_fallback.py needs this history across day boundaries).
    assert rm.state["trade_log"] == stale_state["trade_log"]


def test_trade_log_survives_restart_with_correct_cost_basis_still_derivable():
    # 2026-09-29 audit regression: it's not enough for trade_log to survive
    # a restart/day-rollover as a raw list (test_day_rollover_resets_daily_
    # counters_but_keeps_trade_log above already checks that) - a real
    # consumer (cost_basis_fallback.py, feeding live protective-exit checks)
    # must still derive the correct cost basis from what comes back. Uses
    # the corrected real DOGE transfer-in + real-buy history
    # (pnl_reconciliation_2026-09-29.md) as the fixture, bought "yesterday",
    # recovered via a restart across a UTC day boundary, with no sell yet
    # (position still open going into today).
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    tmp = Path(name)
    stale_state = {
        "date": "2000-01-01",
        "starting_equity": 500.0,
        "trades_today": 1,
        "halted": False,
        "trade_log": [
            {"timestamp": "2000-01-01T16:31:49+00:00", "asset": "DOGE",
             "side": "buy", "quantity": 1129.12766834, "price": 0.180421},
            {"timestamp": "2000-01-01T14:10:54+00:00", "asset": "DOGE",
             "side": "buy", "quantity": 49.64, "price": 0.09873026},
        ],
    }
    tmp.write_text(json.dumps(stale_state))

    rm = RiskManager(LIMITS, state_path=tmp)  # simulates a restart into a new UTC day
    avg_cost = average_cost_basis_from_trade_log("DOGE", rm.state["trade_log"])
    assert avg_cost == pytest.approx(0.1769808578562045, rel=1e-9)


def test_can_auto_execute_absorbs_float_noise_at_the_cap_boundary():
    # 2026-09-29 live finding (LIT, $91.25): position_size() then
    # quantity * price for the actual order notional can land a few ulps
    # on the wrong side of portfolio_value * auto_execute_max_pct, purely
    # from float division-then-multiplication not exactly inverting - not
    # a real overage. A correctly-sized order must not be forced into
    # manual review over noise this small.
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    tmp = Path(name)
    tmp.unlink()
    # Matches the real RISK_LIMITS values in play for this finding (both
    # 0.2, as in config.py) - can_auto_execute reads auto_execute_max_pct
    # directly, so it must match the max_position_pct used to size the order.
    rm = RiskManager(dict(LIMITS, max_position_pct=0.2, auto_execute_max_pct=0.2), state_path=tmp)
    portfolio_value = 456.265899864762
    price = 4.4173
    qty = rm.position_size(portfolio_value, price, total_open_position_value=88.825899864762,
                            max_aggregate_pct=0.6)
    notional = qty * price
    cap = portfolio_value * 0.2
    assert notional > cap  # reproduces the float-noise overshoot itself
    assert rm.can_auto_execute(notional, portfolio_value) is True


def test_can_auto_execute_still_rejects_a_real_overage():
    rm = _new_manager()
    # $1 over a $500 cap is a real overage, not float noise - must still block.
    assert rm.can_auto_execute(501.0, 10_000) is False


def test_position_size_aggregate_override_replaces_configured_value():
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
    tmp.unlink()
    limits = dict(LIMITS, max_position_pct=0.50, max_aggregate_position_pct=0.50)
    rm = RiskManager(limits, state_path=tmp)
    # override down to 10% aggregate ($1,000), already $900 deployed -> $100 room
    assert rm.position_size(10_000, price=100, total_open_position_value=900,
                             max_aggregate_pct=0.10) == 1.0
