import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.strategy import sma_crossover_signal


def test_hold_when_not_enough_history():
    assert sma_crossover_signal([1, 2, 3], short_window=2, long_window=5) == "hold"


def test_explicit_upward_crossover():
    # short SMA(2) crosses above long SMA(4) on the final bar.
    prices = [5, 5, 5, 5, 5, 9]
    assert sma_crossover_signal(prices, short_window=2, long_window=4) == "buy"


def test_explicit_downward_crossover():
    prices = [5, 5, 5, 5, 5, 1]
    assert sma_crossover_signal(prices, short_window=2, long_window=4) == "sell"


def test_hold_when_no_crossover():
    prices = [1, 2, 3, 4, 5, 6, 7, 8]
    assert sma_crossover_signal(prices, short_window=2, long_window=4) == "hold"
