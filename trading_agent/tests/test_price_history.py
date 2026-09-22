import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.price_history import PriceHistoryStore


def _new_store(max_bars=500):
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    return PriceHistoryStore(path=tmp, max_bars=max_bars)


def test_record_and_get_closes_preserves_order():
    store = _new_store()
    store.record("BTC", 100.0, "t1")
    store.record("BTC", 101.5, "t2")
    store.record("BTC", 99.0, "t3")
    assert store.get_closes("BTC") == [100.0, 101.5, 99.0]


def test_get_closes_empty_for_unknown_asset():
    store = _new_store()
    assert store.get_closes("ETH") == []


def test_record_dedups_same_timestamp():
    store = _new_store()
    store.record("BTC", 100.0, "t1")
    store.record("BTC", 999.0, "t1")  # same cycle re-run, must not double-record
    assert store.get_closes("BTC") == [100.0]


def test_record_trims_to_max_bars():
    store = _new_store(max_bars=3)
    for i in range(5):
        store.record("BTC", float(i), f"t{i}")
    assert store.get_closes("BTC") == [2.0, 3.0, 4.0]


def test_persists_across_instances():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    store1 = PriceHistoryStore(path=tmp)
    store1.record("SOL", 50.0, "t1")

    store2 = PriceHistoryStore(path=tmp)
    assert store2.get_closes("SOL") == [50.0]
