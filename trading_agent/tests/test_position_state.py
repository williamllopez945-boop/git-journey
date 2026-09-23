import sys
import tempfile
from datetime import datetime, timedelta, timezone
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


def test_reset_clears_take_profit_flag():
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


def test_in_cooldown_defaults_false_with_no_exit_recorded():
    store = _new_store()
    assert store.in_cooldown("PEPE") is False


def test_record_exit_starts_cooldown():
    store = _new_store()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.record_exit("PEPE", cooldown_hours=12, now=now)
    assert store.in_cooldown("PEPE", now=now + timedelta(hours=1)) is True
    assert store.in_cooldown("PEPE", now=now + timedelta(hours=11, minutes=59)) is True


def test_cooldown_expires_after_configured_hours():
    store = _new_store()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.record_exit("PEPE", cooldown_hours=12, now=now)
    assert store.in_cooldown("PEPE", now=now + timedelta(hours=12)) is False
    assert store.in_cooldown("PEPE", now=now + timedelta(hours=24)) is False


def test_reset_does_not_clear_cooldown():
    store = _new_store()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.record_exit("PEPE", cooldown_hours=12, now=now)
    store.reset("PEPE")  # simulates the position fully closing right after
    assert store.in_cooldown("PEPE", now=now + timedelta(hours=1)) is True


def test_cooldown_tracked_independently_per_asset():
    store = _new_store()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.record_exit("PEPE", cooldown_hours=12, now=now)
    assert store.in_cooldown("PEPE", now=now + timedelta(hours=1)) is True
    assert store.in_cooldown("DOGE", now=now + timedelta(hours=1)) is False
