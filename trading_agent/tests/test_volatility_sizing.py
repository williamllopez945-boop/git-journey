import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.volatility_sizing import realized_volatility, scaled_max_position_pct


def test_realized_volatility_zero_for_flat_series():
    assert realized_volatility([100.0] * 10) == 0.0


def test_realized_volatility_none_with_too_few_prices():
    assert realized_volatility([100.0]) is None
    assert realized_volatility([100.0, 101.0]) is None


def test_realized_volatility_higher_for_choppier_series():
    calm = [100, 101, 100, 101, 100, 101, 100, 101]
    volatile = [100, 130, 90, 140, 80, 150, 70, 160]
    assert realized_volatility(volatile) > realized_volatility(calm)


def test_realized_volatility_known_value():
    # Returns: +10%, -9.0909...%, +10% -> stdev of [10, -9.0909, 10]
    prices = [100, 110, 100, 110]
    vol = realized_volatility(prices)
    assert 10.5 < vol < 11.5  # sanity-bound rather than exact float match


def test_scaled_max_position_pct_equal_volatility_keeps_base():
    assert scaled_max_position_pct(2.0, 2.0, base_max_position_pct=0.05) == 0.05


def test_scaled_max_position_pct_never_scales_above_base():
    # Asset less volatile than benchmark -> still capped at base, not raised.
    assert scaled_max_position_pct(1.0, 2.0, base_max_position_pct=0.05) == 0.05


def test_scaled_max_position_pct_scales_down_for_higher_volatility():
    # Twice as volatile as the benchmark -> half the base allocation.
    result = scaled_max_position_pct(4.0, 2.0, base_max_position_pct=0.05)
    assert abs(result - 0.025) < 1e-9


def test_scaled_max_position_pct_falls_back_to_base_on_missing_data():
    assert scaled_max_position_pct(None, 2.0, base_max_position_pct=0.05) == 0.05
    assert scaled_max_position_pct(2.0, None, base_max_position_pct=0.05) == 0.05
    assert scaled_max_position_pct(0.0, 2.0, base_max_position_pct=0.05) == 0.05
    assert scaled_max_position_pct(2.0, 0.0, base_max_position_pct=0.05) == 0.05
