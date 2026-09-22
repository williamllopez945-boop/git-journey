import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.risk_manager import RiskManager

LIMITS = {
    "max_position_pct": 0.05,
    "daily_loss_limit_pct": 0.03,
    "max_trades_per_day": 3,
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
