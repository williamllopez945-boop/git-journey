import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.cycle_log import CycleLogStore


def _tmp_path():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()
    return tmp


def test_record_creates_file_and_entry():
    store = CycleLogStore(path=_tmp_path())
    store.record("BTC", "fresh_buy_cross", 1.23, "executed", price=100, quantity=0.01)
    entries = store._load()
    assert len(entries) == 1
    assert entries[0]["asset"] == "BTC"
    assert entries[0]["action"] == "executed"
    assert entries[0]["price"] == 100
    assert entries[0]["quantity"] == 0.01


def test_record_appends_without_overwriting():
    store = CycleLogStore(path=_tmp_path())
    store.record("BTC", "fresh_buy_cross", 1.0, "executed")
    store.record("ETH", "fresh_sell_cross", -2.0, "recommended")
    entries = store._load()
    assert len(entries) == 2
    assert [e["asset"] for e in entries] == ["BTC", "ETH"]


def test_entries_for_date_filters_by_utc_day():
    store = CycleLogStore(path=_tmp_path())
    store.record("BTC", "fresh_buy_cross", 1.0, "executed",
                  now=datetime(2026, 9, 22, 23, 59, tzinfo=timezone.utc))
    store.record("ETH", "fresh_sell_cross", -1.0, "blocked_cooldown",
                  now=datetime(2026, 9, 23, 0, 1, tzinfo=timezone.utc))
    store.record("SOL", "excellent_watch", 5.0, "excellent_watch",
                  now=datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc))

    day_22 = store.entries_for_date("2026-09-22")
    day_23 = store.entries_for_date("2026-09-23")
    assert [e["asset"] for e in day_22] == ["BTC"]
    assert [e["asset"] for e in day_23] == ["ETH", "SOL"]


def test_entries_for_date_empty_when_no_matches():
    store = CycleLogStore(path=_tmp_path())
    store.record("BTC", "fresh_buy_cross", 1.0, "executed")
    assert store.entries_for_date("2020-01-01") == []


def test_extra_kwargs_are_freeform_per_action():
    store = CycleLogStore(path=_tmp_path())
    store.record("PEPE", None, None, "protective_exit", reason="stop_loss", pnl_pct=-10.2)
    entries = store._load()
    assert entries[0]["reason"] == "stop_loss"
    assert entries[0]["pnl_pct"] == -10.2
