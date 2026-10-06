import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.income_exit import check_income_exit


def test_zero_or_negative_cost_basis_returns_none():
    assert check_income_exit(10.0, 0.0, False) == (None, 0.0)
    assert check_income_exit(10.0, -5.0, False) == (None, 0.0)


def test_stop_loss_fires_at_threshold():
    # 15% default stop_loss_pct: cost 10.0, price 8.5 -> -15% exactly
    reason, fraction = check_income_exit(8.5, 10.0, False)
    assert (reason, fraction) == ("stop_loss", 1.0)


def test_stop_loss_does_not_fire_just_above_threshold():
    reason, fraction = check_income_exit(8.51, 10.0, False)
    assert reason is None


def test_stop_loss_checked_before_trim_even_if_trim_conditions_also_hold():
    # Construct a case where price is far below cost (stop-loss territory);
    # trim logic must never run first.
    reason, fraction = check_income_exit(5.0, 10.0, trim_already_taken=False)
    assert reason == "stop_loss"
    assert fraction == 1.0


def test_trim_fires_at_threshold():
    # 10% default trim_trigger_pct: cost 10.0, price 11.0 -> +10% exactly
    reason, fraction = check_income_exit(11.0, 10.0, False)
    assert (reason, fraction) == ("trim", 0.50)


def test_trim_does_not_fire_twice():
    reason, fraction = check_income_exit(11.0, 10.0, trim_already_taken=True)
    assert (reason, fraction) == (None, 0.0)


def test_no_exit_in_between_bands():
    reason, fraction = check_income_exit(10.2, 10.0, False)
    assert (reason, fraction) == (None, 0.0)


def test_custom_thresholds_override_defaults():
    reason, fraction = check_income_exit(
        9.0, 10.0, False, stop_loss_pct=0.05, trim_trigger_pct=0.20, trim_sell_fraction=0.25,
    )
    assert (reason, fraction) == ("stop_loss", 1.0)

    reason, fraction = check_income_exit(
        12.0, 10.0, False, stop_loss_pct=0.05, trim_trigger_pct=0.20, trim_sell_fraction=0.25,
    )
    assert (reason, fraction) == ("trim", 0.25)
