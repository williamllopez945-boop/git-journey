import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.risk_manager import RiskManager

LIMITS = {
    "max_position_pct": 0.05,
    "daily_loss_limit_pct": 0.03,
    "max_trades_per_day": 3,
    "auto_execute_max_usd": 5.0,
}


def _new_manager():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
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


def test_circuit_breaker_halts_past_daily_loss_limit():
    rm = _new_manager()
    rm.start_of_day(equity=10_000)
    assert rm.check_circuit_breaker(current_equity=9_800) is False  # 2% down
    assert rm.check_circuit_breaker(current_equity=9_600) is True  # 4% down
    assert not rm.can_trade()


def test_can_auto_execute_at_or_under_threshold():
    rm = _new_manager()
    assert rm.can_auto_execute(5.0) is True
    assert rm.can_auto_execute(2.50) is True


def test_can_auto_execute_over_threshold():
    rm = _new_manager()
    assert rm.can_auto_execute(5.01) is False
    assert rm.can_auto_execute(25.0) is False


def test_can_auto_execute_defaults_to_false_without_configured_limit():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    rm = RiskManager({"max_position_pct": 0.05, "daily_loss_limit_pct": 0.03, "max_trades_per_day": 3}, state_path=tmp)
    assert rm.can_auto_execute(0.01) is False


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
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    limits = dict(LIMITS, max_concurrent_positions=5)
    rm = RiskManager(limits, state_path=tmp)
    assert rm.can_open_new_position(open_position_count=4) is True
    assert rm.can_open_new_position(open_position_count=5) is False
    assert rm.can_open_new_position(open_position_count=6) is False


def test_can_open_new_position_none_value_means_uncapped():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    limits = dict(LIMITS, max_concurrent_positions=None)
    rm = RiskManager(limits, state_path=tmp)
    assert rm.can_open_new_position(open_position_count=1000) is True


def test_position_size_ignores_aggregate_cap_when_not_configured():
    rm = _new_manager()  # LIMITS has no max_aggregate_position_pct key
    # per-asset cap alone: 5% of 10,000 = 500 -> 5 units at price 100
    assert rm.position_size(10_000, price=100, total_open_position_value=9_000) == 5.0


def test_position_size_clamped_by_aggregate_cap():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    limits = dict(LIMITS, max_position_pct=0.50, max_aggregate_position_pct=0.50)
    rm = RiskManager(limits, state_path=tmp)
    # portfolio $10,000, aggregate cap 50% = $5,000, already $4,800 deployed
    # -> only $200 of aggregate room left, even though the per-asset cap
    # (50% = $5,000) would otherwise allow far more.
    assert rm.position_size(10_000, price=100, total_open_position_value=4_800) == 2.0


def test_position_size_zero_when_aggregate_cap_already_reached():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    limits = dict(LIMITS, max_position_pct=0.50, max_aggregate_position_pct=0.50)
    rm = RiskManager(limits, state_path=tmp)
    assert rm.position_size(10_000, price=100, total_open_position_value=5_000) == 0.0
    assert rm.position_size(10_000, price=100, total_open_position_value=6_000) == 0.0


def test_day_rollover_resets_daily_counters_but_keeps_trade_log():
    # Simulate yesterday's state on disk, including a real trade.
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
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


def test_position_size_aggregate_override_replaces_configured_value():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    limits = dict(LIMITS, max_position_pct=0.50, max_aggregate_position_pct=0.50)
    rm = RiskManager(limits, state_path=tmp)
    # override down to 10% aggregate ($1,000), already $900 deployed -> $100 room
    assert rm.position_size(10_000, price=100, total_open_position_value=900,
                             max_aggregate_pct=0.10) == 1.0
