import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.position_state import PositionStateStore


def _new_store():
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
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
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
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


def test_hours_since_gate_blocked_defaults_none_when_never_blocked():
    store = _new_store()
    assert store.hours_since_gate_blocked("PEPE") is None


def test_mark_gate_blocked_starts_the_clock():
    store = _new_store()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.mark_gate_blocked("PEPE", now=now)
    assert store.hours_since_gate_blocked("PEPE", now=now + timedelta(hours=5)) == 5.0


def test_mark_gate_blocked_is_a_noop_once_already_set():
    # Mirrors backtest.py's blocked_since_index "if None" guard - a signal
    # blocked for several consecutive cycles keeps the ORIGINAL timestamp.
    store = _new_store()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.mark_gate_blocked("PEPE", now=now)
    store.mark_gate_blocked("PEPE", now=now + timedelta(hours=3))
    assert store.hours_since_gate_blocked("PEPE", now=now + timedelta(hours=5)) == 5.0


def test_clear_gate_blocked_resets_to_none():
    store = _new_store()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.mark_gate_blocked("PEPE", now=now)
    store.clear_gate_blocked("PEPE")
    assert store.hours_since_gate_blocked("PEPE", now=now + timedelta(hours=1)) is None


def test_clear_gate_blocked_is_a_noop_when_never_blocked():
    store = _new_store()
    store.clear_gate_blocked("PEPE")  # should not raise
    assert store.hours_since_gate_blocked("PEPE") is None


def test_gate_blocked_tracked_independently_per_asset():
    store = _new_store()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.mark_gate_blocked("PEPE", now=now)
    assert store.hours_since_gate_blocked("PEPE", now=now + timedelta(hours=1)) == 1.0
    assert store.hours_since_gate_blocked("DOGE", now=now + timedelta(hours=1)) is None


def test_gate_blocked_persists_across_instances():
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # Windows cannot unlink an open file.
    tmp = Path(name)
    tmp.unlink()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store1 = PositionStateStore(path=tmp)
    store1.mark_gate_blocked("SOL", now=now)

    store2 = PositionStateStore(path=tmp)
    assert store2.hours_since_gate_blocked("SOL", now=now + timedelta(hours=2)) == 2.0
