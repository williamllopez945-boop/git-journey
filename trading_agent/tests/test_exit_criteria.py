import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.exit_criteria import check_exit, TAKE_PROFIT_SELL_FRACTION


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


def test_trailing_stop_disabled_by_default_after_take_profit():
    # take_profit already taken, price has pulled back from a peak but is
    # still well above the original entry-basis stop-loss - with no
    # trailing_stop_pct passed (module default is None), nothing fires,
    # matching pre-2026-09-24 behavior exactly.
    reason, fraction = check_exit(current_price=120, avg_cost_basis=100, take_profit_already_taken=True,
                                   peak_price_since_take_profit=150)
    assert reason is None
    assert fraction == 0.0


def test_trailing_stop_fires_on_pullback_from_peak():
    # Peak was 150, a 10% trailing stop means anything at/below 135 exits.
    reason, fraction = check_exit(current_price=134, avg_cost_basis=100, take_profit_already_taken=True,
                                   peak_price_since_take_profit=150, trailing_stop_pct=0.10)
    assert reason == "trailing_stop"
    assert fraction == 1.0


def test_trailing_stop_exact_threshold_triggers():
    reason, fraction = check_exit(current_price=135, avg_cost_basis=100, take_profit_already_taken=True,
                                   peak_price_since_take_profit=150, trailing_stop_pct=0.10)
    assert reason == "trailing_stop"
    assert fraction == 1.0


def test_trailing_stop_does_not_fire_within_band_of_peak():
    reason, fraction = check_exit(current_price=140, avg_cost_basis=100, take_profit_already_taken=True,
                                   peak_price_since_take_profit=150, trailing_stop_pct=0.10)
    assert reason is None
    assert fraction == 0.0


def test_trailing_stop_never_checked_before_take_profit_taken():
    # Even with trailing_stop_pct set, it's irrelevant until take-profit has
    # actually fired once - the ordinary take_profit path still governs.
    reason, fraction = check_exit(current_price=116, avg_cost_basis=100, take_profit_already_taken=False,
                                   peak_price_since_take_profit=200, trailing_stop_pct=0.10)
    assert reason == "take_profit"


def test_original_stop_loss_still_checked_first_even_after_take_profit():
    # A sharp reversal straight through the original entry-basis stop-loss
    # should still exit as "stop_loss", not "trailing_stop" - it's checked
    # unconditionally before the take-profit/trailing branch.
    reason, fraction = check_exit(current_price=89, avg_cost_basis=100, take_profit_already_taken=True,
                                   peak_price_since_take_profit=150, trailing_stop_pct=0.10)
    assert reason == "stop_loss"
    assert fraction == 1.0


def test_trailing_stop_ignored_without_a_peak_price():
    # trailing_stop_pct set but the caller never supplied a peak (e.g. a
    # position that took profit before this feature existed) - inert, not
    # an error. Price is above the entry-basis stop-loss so nothing else
    # fires either.
    reason, fraction = check_exit(current_price=120, avg_cost_basis=100, take_profit_already_taken=True,
                                   trailing_stop_pct=0.10)
    assert reason is None
    assert fraction == 0.0


def test_overrides_replace_module_defaults():
    # 5% stop-loss instead of the default 10% - a 6% drop now triggers.
    reason, fraction = check_exit(current_price=94, avg_cost_basis=100, take_profit_already_taken=False,
                                   stop_loss_pct=0.05)
    assert reason == "stop_loss"

    # 20% take-profit instead of the default 15% - a 16% gain no longer triggers.
    reason, fraction = check_exit(current_price=116, avg_cost_basis=100, take_profit_already_taken=False,
                                   take_profit_pct=0.20)
    assert reason is None

    # Custom sell fraction is honored.
    reason, fraction = check_exit(current_price=116, avg_cost_basis=100, take_profit_already_taken=False,
                                   take_profit_sell_fraction=0.5)
    assert reason == "take_profit"
    assert fraction == 0.5
