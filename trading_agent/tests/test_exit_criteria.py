import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.exit_criteria import check_exit


def test_no_action_within_bands():
    reason, fraction = check_exit(current_price=105, avg_cost_basis=100, take_profit_already_taken=False)
    assert reason is None
    assert fraction == 0.0


def test_stop_loss_triggers_full_exit():
    # 100 -> 89 is a 11% drop, past the 10% stop-loss
    reason, fraction = check_exit(current_price=89, avg_cost_basis=100, take_profit_already_taken=False)
    assert reason == "stop_loss"
    assert fraction == 1.0


def test_stop_loss_exact_threshold_triggers():
    reason, fraction = check_exit(current_price=90, avg_cost_basis=100, take_profit_already_taken=False)
    assert reason == "stop_loss"
    assert fraction == 1.0


def test_take_profit_triggers_partial_exit():
    # 100 -> 116 is a 16% gain, past the 15% take-profit
    reason, fraction = check_exit(current_price=116, avg_cost_basis=100, take_profit_already_taken=False)
    assert reason == "take_profit"
    assert fraction == 0.80


def test_take_profit_does_not_retrigger_once_taken():
    reason, fraction = check_exit(current_price=120, avg_cost_basis=100, take_profit_already_taken=True)
    assert reason is None
    assert fraction == 0.0


def test_zero_or_negative_cost_basis_is_inert():
    assert check_exit(current_price=100, avg_cost_basis=0, take_profit_already_taken=False) == (None, 0.0)
    assert check_exit(current_price=100, avg_cost_basis=-5, take_profit_already_taken=False) == (None, 0.0)
