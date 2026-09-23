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
    classification, crossover_pct = classify("BTC", sma10=110, sma30=100, pct_change=0.2, path=path, min_strength_pct=0.25)
    assert classification == "hold"
    assert crossover_pct == 10.0


def test_flip_alone_is_hold_pending_confirmation():
    path = _tmp_path()
    classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # bearish baseline
    classification, _ = classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)
    assert classification == "hold"  # flip just happened, not confirmed yet


def test_fresh_buy_cross_confirmed_after_second_cycle():
    path = _tmp_path()
    classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # bearish baseline
    classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # flip, pending
    classification, _ = classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # still bullish
    assert classification == "fresh_buy_cross"


def test_fresh_sell_cross_confirmed_after_second_cycle():
    path = _tmp_path()
    classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # bullish baseline
    classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # flip, pending
    classification, _ = classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # still bearish
    assert classification == "fresh_sell_cross"


def test_immediate_reversal_never_confirms():
    path = _tmp_path()
    classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # bearish baseline
    classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # flip up, pending
    classification, _ = classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # flips back down
    assert classification == "hold"  # whipsaw filtered, not fresh_sell_cross either (this is a new flip, now pending itself)


def test_confirmation_rejected_when_gap_too_weak():
    path = _tmp_path()
    classify("BTC", sma10=99.9, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # bearish baseline
    classify("BTC", sma10=100.05, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # flip up, pending
    classification, crossover_pct = classify("BTC", sma10=100.05, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)
    assert classification == "hold"  # persisted but crossover_pct (0.05%) is below the 0.25% bar
    assert crossover_pct < 0.25


def test_excellent_watch_on_large_crossover_without_flip():
    path = _tmp_path()
    classify("BTC", sma10=101, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # bullish baseline
    classification, crossover_pct = classify("BTC", sma10=110, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)
    assert classification == "excellent_watch"
    assert crossover_pct == 10.0


def test_excellent_watch_on_large_pct_change_without_flip():
    path = _tmp_path()
    classify("BTC", sma10=101, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)
    classification, _ = classify("BTC", sma10=101, sma30=100, pct_change=0.08, path=path, min_strength_pct=0.25)
    assert classification == "excellent_watch"


def test_hold_when_stable_and_below_thresholds():
    path = _tmp_path()
    classify("BTC", sma10=101, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)
    classification, _ = classify("BTC", sma10=101.5, sma30=100, pct_change=0.01, path=path, min_strength_pct=0.25)
    assert classification == "hold"


def test_assets_tracked_independently():
    path = _tmp_path()
    classify("BTC", sma10=95, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)
    classify("ETH", sma10=105, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)
    classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # BTC flip, pending
    classify("ETH", sma10=95, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)  # ETH flip, pending
    btc_class, _ = classify("BTC", sma10=105, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)
    eth_class, _ = classify("ETH", sma10=95, sma30=100, pct_change=0.0, path=path, min_strength_pct=0.25)
    assert btc_class == "fresh_buy_cross"
    assert eth_class == "fresh_sell_cross"
