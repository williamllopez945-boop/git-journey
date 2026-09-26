import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.entry_filter import crossover_strength_pct, passes_threshold, confirmed_signal


def test_crossover_strength_pct_basic():
    assert crossover_strength_pct(110, 100) == 10.0
    assert crossover_strength_pct(90, 100) == 10.0


def test_passes_threshold_at_and_above_boundary():
    assert passes_threshold(101.0, 100.0, min_strength_pct=1.0) is True
    assert passes_threshold(100.99, 100.0, min_strength_pct=1.0) is False


def test_passes_threshold_zero_long_sma_is_false():
    assert passes_threshold(5.0, 0.0, min_strength_pct=1.0) is False


def test_confirmed_signal_holds_with_too_little_history():
    assert confirmed_signal([5], short_window=2, long_window=4) == "hold"
    assert confirmed_signal([], short_window=2, long_window=4) == "hold"


def test_confirmed_signal_holds_when_no_prior_crossover():
    prices = [1, 2, 3, 4, 5, 6, 7, 8]
    assert confirmed_signal(prices, short_window=2, long_window=4) == "hold"


def test_confirmed_signal_fires_one_bar_after_a_persisting_cross():
    # Raw crossover fires when the last bar is appended (see test_strategy's
    # explicit upward crossover fixture); confirmed_signal needs one more
    # bar where the bullish state still holds.
    crossed = [5, 5, 5, 5, 5, 9]
    assert confirmed_signal(crossed, short_window=2, long_window=4, min_strength_pct=0) == "hold"

    still_bullish = crossed + [9]  # one more bar, still above the long SMA
    assert confirmed_signal(still_bullish, short_window=2, long_window=4, min_strength_pct=0) == "buy"


def test_confirmed_signal_rejects_immediate_reversal():
    crossed = [5, 5, 5, 5, 5, 9]
    reversed_next_bar = crossed + [1]  # snaps back below the long SMA immediately
    assert confirmed_signal(reversed_next_bar, short_window=2, long_window=4, min_strength_pct=0) == "hold"


def test_confirmed_signal_downward_cross_symmetry():
    crossed_down = [5, 5, 5, 5, 5, 1]
    assert confirmed_signal(crossed_down, short_window=2, long_window=4, min_strength_pct=0) == "hold"

    still_bearish = crossed_down + [1]
    assert confirmed_signal(still_bearish, short_window=2, long_window=4, min_strength_pct=0) == "sell"


def test_confirmed_signal_strength_filter_can_still_reject():
    crossed = [5, 5, 5, 5, 5, 9]
    still_bullish = crossed + [9]
    # Passes with no strength requirement...
    assert confirmed_signal(still_bullish, short_window=2, long_window=4, min_strength_pct=0) == "buy"
    # ...but a very high bar rejects even a persisting move.
    assert confirmed_signal(still_bullish, short_window=2, long_window=4, min_strength_pct=50.0) == "hold"
