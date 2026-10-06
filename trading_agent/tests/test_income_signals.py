import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.income_signals import rolling_range_position, classify_dip


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
