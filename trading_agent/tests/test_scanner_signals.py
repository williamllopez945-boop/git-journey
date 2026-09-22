import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.scanner_signals import classify


def _tmp_path():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    return tmp


def test_first_observation_is_hold_regardless_of_state():
    path = _tmp_path()
    classification, crossover_pct = classify("BTC", sma10=110, sma30=100, pct_change=0.2, path=path)
    assert classification == "hold"
    assert crossover_pct == 10.0


def test_fresh_buy_cross_when_state_flips_bullish():
    path = _tmp_path()
    classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path)  # bearish baseline
    classification, _ = classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path)
    assert classification == "fresh_buy_cross"


def test_fresh_sell_cross_when_state_flips_bearish():
    path = _tmp_path()
    classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path)  # bullish baseline
    classification, _ = classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path)
    assert classification == "fresh_sell_cross"


def test_excellent_watch_on_large_crossover_without_flip():
    path = _tmp_path()
    classify("BTC", sma10=101, sma30=100, pct_change=0.0, path=path)  # bullish baseline
    classification, crossover_pct = classify("BTC", sma10=110, sma30=100, pct_change=0.0, path=path)
    assert classification == "excellent_watch"
    assert crossover_pct == 10.0


def test_excellent_watch_on_large_pct_change_without_flip():
    path = _tmp_path()
    classify("BTC", sma10=101, sma30=100, pct_change=0.0, path=path)
    classification, _ = classify("BTC", sma10=101, sma30=100, pct_change=0.08, path=path)
    assert classification == "excellent_watch"


def test_hold_when_stable_and_below_thresholds():
    path = _tmp_path()
    classify("BTC", sma10=101, sma30=100, pct_change=0.0, path=path)
    classification, _ = classify("BTC", sma10=101.5, sma30=100, pct_change=0.01, path=path)
    assert classification == "hold"


def test_assets_tracked_independently():
    path = _tmp_path()
    classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path)
    classify("ETH", sma10=105, sma30=100, pct_change=0.0, path=path)
    btc_class, _ = classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path)
    eth_class, _ = classify("ETH", sma10=95, sma30=100, pct_change=0.0, path=path)
    assert btc_class == "fresh_buy_cross"
    assert eth_class == "fresh_sell_cross"
