import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.wheel_state import (
    WheelStateStore, IDLE, CSP_OPEN, HOLDING_SHARES, COVERED_CALL_OPEN,
    next_state_after_csp_expiration, next_state_after_covered_call_expiration,
)


def test_next_state_after_csp_expiration():
    assert next_state_after_csp_expiration(assigned=True) == HOLDING_SHARES
    assert next_state_after_csp_expiration(assigned=False) == IDLE


def test_next_state_after_covered_call_expiration():
    assert next_state_after_covered_call_expiration(called_away=True) == IDLE
    assert next_state_after_covered_call_expiration(called_away=False) == HOLDING_SHARES


def _store():
    tmp = Path(tempfile.mkdtemp()) / "wheel_state.json"
    return WheelStateStore(path=tmp)


def test_new_symbol_starts_idle():
    store = _store()
    assert store.state("SOFI") == IDLE


def test_open_csp_sets_state_and_fields():
    store = _store()
    store.open_csp("SOFI", "opt-1", strike=15.0, expiration="2026-10-03",
                    premium_collected=42.0, quantity=1)
    assert store.state("SOFI") == CSP_OPEN
    rec = store.record("SOFI")
    assert rec["strike"] == 15.0
    assert rec["premium_collected"] == 42.0


def test_resolve_csp_otm_returns_to_idle_and_clears_fields():
    store = _store()
    store.open_csp("SOFI", "opt-1", strike=15.0, expiration="2026-10-03",
                    premium_collected=42.0, quantity=1)
    store.resolve_csp("SOFI", assigned=False)
    assert store.record("SOFI") == {"state": IDLE}


def test_resolve_csp_assigned_moves_to_holding_shares_with_cost_basis():
    store = _store()
    store.open_csp("SOFI", "opt-1", strike=15.0, expiration="2026-10-03",
                    premium_collected=42.0, quantity=1)
    store.resolve_csp("SOFI", assigned=True, cost_basis=14.58)
    assert store.state("SOFI") == HOLDING_SHARES
    rec = store.record("SOFI")
    assert rec["cost_basis"] == 14.58
    assert rec["premium_collected"] == 42.0


def test_open_covered_call_accumulates_premium():
    store = _store()
    store.open_csp("SOFI", "opt-1", strike=15.0, expiration="2026-10-03",
                    premium_collected=42.0, quantity=1)
    store.resolve_csp("SOFI", assigned=True, cost_basis=14.58)
    store.open_covered_call("SOFI", "opt-2", strike=16.0, expiration="2026-10-10",
                             premium_collected=20.0, quantity=1)
    rec = store.record("SOFI")
    assert rec["state"] == COVERED_CALL_OPEN
    assert rec["premium_collected"] == 62.0  # 42 (put) + 20 (call)


def test_resolve_covered_call_not_called_away_returns_to_holding_shares():
    store = _store()
    store.open_csp("SOFI", "opt-1", strike=15.0, expiration="2026-10-03",
                    premium_collected=42.0, quantity=1)
    store.resolve_csp("SOFI", assigned=True, cost_basis=14.58)
    store.open_covered_call("SOFI", "opt-2", strike=16.0, expiration="2026-10-10",
                             premium_collected=20.0, quantity=1)
    store.resolve_covered_call("SOFI", called_away=False)
    rec = store.record("SOFI")
    assert rec["state"] == HOLDING_SHARES
    assert rec["cost_basis"] == 14.58  # still held, still need the floor for the next call
    assert "option_id" not in rec


def test_resolve_covered_call_called_away_returns_to_idle_and_clears_everything():
    store = _store()
    store.open_csp("SOFI", "opt-1", strike=15.0, expiration="2026-10-03",
                    premium_collected=42.0, quantity=1)
    store.resolve_csp("SOFI", assigned=True, cost_basis=14.58)
    store.open_covered_call("SOFI", "opt-2", strike=16.0, expiration="2026-10-10",
                             premium_collected=20.0, quantity=1)
    store.resolve_covered_call("SOFI", called_away=True)
    assert store.state("SOFI") == IDLE
    assert store.record("SOFI") == {"state": IDLE}


def test_state_persists_across_store_instances():
    tmp = Path(tempfile.mkdtemp()) / "wheel_state.json"
    store1 = WheelStateStore(path=tmp)
    store1.open_csp("SOFI", "opt-1", strike=15.0, expiration="2026-10-03",
                     premium_collected=42.0, quantity=1)
    store2 = WheelStateStore(path=tmp)
    assert store2.state("SOFI") == CSP_OPEN
