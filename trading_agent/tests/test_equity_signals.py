import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.equity_signals import (
    sma_pair, relative_volume, pct_change_from_quote, whole_share_quantity,
)


def test_sma_pair_returns_none_below_long_window():
    closes = [1.0] * 29
    assert sma_pair(closes) == (None, None)


def test_sma_pair_computes_both_windows():
    closes = list(range(1, 31))  # 1..30, oldest to newest
    sma10, sma30 = sma_pair(closes)
    assert sma10 == pytest.approx(sum(range(21, 31)) / 10)
    assert sma30 == pytest.approx(sum(range(1, 31)) / 30)


def test_sma_pair_uses_only_the_most_recent_bars():
    closes = [0.0] * 20 + list(range(1, 31))
    sma10, sma30 = sma_pair(closes)
    assert sma10 == pytest.approx(sum(range(21, 31)) / 10)
    assert sma30 == pytest.approx(sum(range(1, 31)) / 30)


def test_relative_volume_none_when_not_enough_history():
    volumes = [100] * 14  # needs period+1 = 15
    assert relative_volume(volumes) is None


def test_relative_volume_ratio_of_current_over_preceding_average():
    volumes = [100] * 14 + [200]
    assert relative_volume(volumes) == pytest.approx(2.0)


def test_relative_volume_zero_average_returns_none():
    volumes = [0] * 14 + [50]
    assert relative_volume(volumes) is None


def test_pct_change_from_quote_computes_fractional_change():
    assert pct_change_from_quote(110.0, 100.0) == pytest.approx(0.10)
    assert pct_change_from_quote(90.0, 100.0) == pytest.approx(-0.10)


def test_pct_change_from_quote_none_when_no_previous_close():
    assert pct_change_from_quote(110.0, 0.0) is None
    assert pct_change_from_quote(110.0, None) is None


def test_whole_share_quantity_floors_a_fractional_sizing():
    # PANW 2026-09-29: $92.03 sized to 0.24132974184236916 shares - a
    # marketable limit order (the equity execution policy) can't place
    # that fractional quantity, so it must floor to a whole share.
    assert whole_share_quantity(0.24132974184236916) == 0.0


def test_whole_share_quantity_floors_never_rounds_up():
    assert whole_share_quantity(1.9999) == 1.0
    assert whole_share_quantity(2.0) == 2.0
    assert whole_share_quantity(2.0001) == 2.0


def test_whole_share_quantity_zero_when_even_one_share_is_too_expensive():
    # Sub-one-share sizing means the caller should present the signal as
    # a recommendation rather than auto-execute a market order to force
    # the fractional quantity through.
    assert whole_share_quantity(0.0) == 0.0
