import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.rsi_filter import rsi, passes_rsi_filter


def test_rsi_none_when_insufficient_history():
    assert rsi([100.0] * 10, period=14) is None


def test_rsi_100_when_no_losses():
    # Strictly rising over the whole window -> no losses -> RSI = 100.
    prices = [100.0 + i for i in range(15)]
    assert rsi(prices, period=14) == 100.0


def test_rsi_0_when_no_gains():
    # Strictly falling over the whole window -> no gains -> RSI = 0.
    prices = [100.0 - i for i in range(15)]
    assert rsi(prices, period=14) == 0.0


def test_rsi_50_when_gains_equal_losses():
    # Alternating +2/-2 changes -> equal average gain and loss -> RSI = 50.
    prices = [100.0]
    for i in range(14):
        prices.append(prices[-1] + (2 if i % 2 == 0 else -2))
    assert rsi(prices, period=14) == 50.0


def test_passes_rsi_filter_true_when_not_enough_history():
    assert passes_rsi_filter([100.0] * 5, period=14) is True


def test_passes_rsi_filter_blocks_overbought():
    prices = [100.0 + i for i in range(15)]  # RSI 100
    assert passes_rsi_filter(prices, period=14, overbought_pct=70) is False


def test_passes_rsi_filter_allows_below_threshold():
    prices = [100.0 - i for i in range(15)]  # RSI 0
    assert passes_rsi_filter(prices, period=14, overbought_pct=70) is True
