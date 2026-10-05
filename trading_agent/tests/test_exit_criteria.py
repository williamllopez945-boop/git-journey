import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.exit_criteria import check_exit, TAKE_PROFIT_PCT, TAKE_PROFIT_SELL_FRACTION


def test_no_action_within_bands():
    reason, fraction = check_exit(current_price=105, avg_cost_basis=100, take_profit_already_taken=False)
    assert reason is None
    assert fraction == 0.0


def test_stop_loss_triggers_full_exit():
    # 100 -> 95 is a 5% drop, past the 4% stop-loss
    reason, fraction = check_exit(current_price=95, avg_cost_basis=100, take_profit_already_taken=False)
    assert reason == "stop_loss"
    assert fraction == 1.0


def test_stop_loss_exact_threshold_triggers():
    reason, fraction = check_exit(current_price=96, avg_cost_basis=100, take_profit_already_taken=False)
    assert reason == "stop_loss"
    assert fraction == 1.0


def test_take_profit_triggers_partial_exit():
    # 100 -> 109 is a 9% gain, past the 8% take-profit
    reason, fraction = check_exit(current_price=109, avg_cost_basis=100, take_profit_already_taken=False)
    assert reason == "take_profit"
    assert fraction == TAKE_PROFIT_SELL_FRACTION


def test_take_profit_does_not_retrigger_once_taken():
    reason, fraction = check_exit(current_price=120, avg_cost_basis=100, take_profit_already_taken=True)
    assert reason is None
    assert fraction == 0.0


def test_zero_or_negative_cost_basis_is_inert():
    assert check_exit(current_price=100, avg_cost_basis=0, take_profit_already_taken=False) == (None, 0.0)
    assert check_exit(current_price=100, avg_cost_basis=-5, take_profit_already_taken=False) == (None, 0.0)


def test_default_take_profit_sell_fraction_is_70_percent():
    # Locks in the tuned default explicitly (backtest_2026-09-23.md) so an
    # accidental change to the constant is caught, not just self-compared.
    assert TAKE_PROFIT_SELL_FRACTION == 0.70


def test_default_take_profit_pct_is_8_percent():
    # Locks in the tuned default explicitly
    # (backtest_2026-09-28_gate_floor_and_tighter_stops.md) so an
    # accidental change to the constant is caught, not just self-compared.
    assert TAKE_PROFIT_PCT == 0.08


def test_original_stop_loss_still_checked_first_even_after_take_profit():
    # A sharp reversal straight through the entry-basis stop-loss should
    # still exit as "stop_loss" even once take-profit has already fired -
    # it's checked unconditionally before the take-profit-taken branch.
    reason, fraction = check_exit(current_price=89, avg_cost_basis=100, take_profit_already_taken=True)
    assert reason == "stop_loss"
    assert fraction == 1.0


def test_overrides_replace_module_defaults():
    # 5% stop-loss instead of the default 4% - a 6% drop now triggers.
    reason, fraction = check_exit(current_price=94, avg_cost_basis=100, take_profit_already_taken=False,
                                   stop_loss_pct=0.05)
    assert reason == "stop_loss"

    # 25% take-profit instead of the default 8% - a 21% gain no longer triggers.
    reason, fraction = check_exit(current_price=121, avg_cost_basis=100, take_profit_already_taken=False,
                                   take_profit_pct=0.25)
    assert reason is None

    # Custom sell fraction is honored.
    reason, fraction = check_exit(current_price=121, avg_cost_basis=100, take_profit_already_taken=False,
                                   take_profit_sell_fraction=0.5)
    assert reason == "take_profit"
    assert fraction == 0.5
