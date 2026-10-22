import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.income_signals import rolling_range_position, classify_dip, near_support, classify_entry


def test_rolling_range_position_warmup_returns_none():
    closes = [10.0] * 5  # fewer than default lookback_days=20
    assert rolling_range_position(closes) is None


def test_rolling_range_position_flat_window_returns_none():
    closes = [10.0] * 25
    assert rolling_range_position(closes, lookback_days=20) is None


def test_rolling_range_position_today_at_low_is_zero():
    closes = [15.0] * 19 + [10.0]
    assert rolling_range_position(closes, lookback_days=20) == pytest.approx(0.0)


def test_rolling_range_position_today_at_high_is_one():
    closes = [5.0] * 19 + [15.0]
    assert rolling_range_position(closes, lookback_days=20) == pytest.approx(1.0)


def test_rolling_range_position_midpoint():
    closes = [10.0] * 9 + [20.0] * 10 + [15.0]
    assert rolling_range_position(closes, lookback_days=20) == pytest.approx(0.5)


def test_rolling_range_position_only_considers_trailing_window():
    # An older, wider range outside the lookback window must not affect the result.
    closes = [0.0, 100.0] + [10.0] * 9 + [20.0] * 10 + [15.0]
    position = rolling_range_position(closes, lookback_days=20)
    assert position == pytest.approx(0.5)


def test_classify_dip_below_threshold_is_dip_buy():
    closes = [15.0] * 19 + [10.0]  # today at the low -> position 0.0
    assert classify_dip(closes, lookback_days=20, entry_threshold=0.10) == "dip_buy"


def test_classify_dip_boundary_is_inclusive():
    # low=0.0, high=10.0, today=1.0 -> position exactly 0.10 -> dip_buy (<=, not <)
    closes = [0.0] * 10 + [10.0] * 9 + [1.0]
    assert classify_dip(closes, lookback_days=20, entry_threshold=0.10) == "dip_buy"


def test_classify_dip_above_threshold_is_hold():
    closes = [5.0] * 19 + [15.0]  # today at the high -> position 1.0
    assert classify_dip(closes, lookback_days=20, entry_threshold=0.10) == "hold"


def test_classify_dip_warmup_is_hold_not_blocked():
    closes = [10.0] * 5
    assert classify_dip(closes) == "hold"


def test_near_support_warmup_returns_none():
    closes = [10.0] * 10  # fewer than default lookback_days=60
    assert near_support(closes) is None


def test_near_support_at_the_low_is_true():
    closes = [20.0] * 59 + [10.0]  # today's close IS the 60-day low
    assert near_support(closes, lookback_days=60, tolerance_pct=0.03) is True


def test_near_support_boundary_is_inclusive():
    # support_level=100.0, today=103.0 -> exactly 3% above -> inclusive <=
    closes = [200.0] * 59 + [103.0]
    closes[0] = 100.0  # ensure the 100.0 low is inside the window
    assert near_support(closes, lookback_days=60, tolerance_pct=0.03) is True


def test_near_support_far_from_low_is_false():
    closes = [10.0] + [20.0] * 58 + [19.0]  # low=10.0, today=19.0 -> 90% above, not near
    assert near_support(closes, lookback_days=60, tolerance_pct=0.03) is False


def test_near_support_zero_or_negative_low_returns_none():
    closes = [0.0] * 60
    assert near_support(closes, lookback_days=60, tolerance_pct=0.03) is None


def test_classify_entry_requires_both_dip_and_support():
    # Bottom of the trailing 20-day window, but a much deeper low sits
    # earlier in the 60-day window - classify_dip alone would say
    # dip_buy, but near_support says no -> classify_entry must hold.
    closes = [100.0] * 10 + [5.0] + [50.0] * 48 + [40.0]
    assert classify_dip(closes, lookback_days=20, entry_threshold=0.10) == "dip_buy"
    assert near_support(closes, lookback_days=60, tolerance_pct=0.03) is False
    assert classify_entry(closes) == "hold"


def test_classify_entry_dip_buy_when_both_agree():
    closes = [20.0] * 59 + [10.0]  # today is both the 20-day and 60-day low
    assert classify_entry(closes) == "dip_buy"


def test_classify_entry_holds_when_dip_signal_absent_even_if_near_support():
    # Today is near the 60-day low, but NOT in the bottom 10% of the
    # trailing 20-day window (price has been drifting up for 20 days) -
    # classify_dip says hold, so classify_entry must hold too regardless
    # of the support check.
    closes = [10.0] * 40 + [10.0 + 0.45 * i for i in range(1, 21)]  # trending up, ends near 19.5
    assert classify_dip(closes, lookback_days=20, entry_threshold=0.10) == "hold"
    assert classify_entry(closes) == "hold"


def test_classify_entry_warmup_is_hold_not_blocked():
    closes = [15.0] * 19 + [10.0]  # enough for classify_dip (20), not for near_support (60)
    assert classify_dip(closes) == "dip_buy"
    assert classify_entry(closes) == "hold"
