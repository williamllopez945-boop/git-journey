import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.position_state import PositionStateStore


def _new_store():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    return PositionStateStore(path=tmp)


def test_took_profit_defaults_false():
    store = _new_store()
    assert store.took_profit("PEPE") is False


def test_mark_took_profit_persists():
    store = _new_store()
    store.mark_took_profit("PEPE")
    assert store.took_profit("PEPE") is True


def test_reset_clears_flag():
    store = _new_store()
    store.mark_took_profit("PEPE")
    store.reset("PEPE")
    assert store.took_profit("PEPE") is False


def test_assets_tracked_independently():
    store = _new_store()
    store.mark_took_profit("PEPE")
    assert store.took_profit("PEPE") is True
    assert store.took_profit("DOGE") is False


def test_persists_across_instances():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    store1 = PositionStateStore(path=tmp)
    store1.mark_took_profit("SOL")

    store2 = PositionStateStore(path=tmp)
    assert store2.took_profit("SOL") is True
