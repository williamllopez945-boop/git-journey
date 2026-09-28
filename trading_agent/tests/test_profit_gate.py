import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.profit_gate import blocks_sell_cross, gate_floor_should_force_exit


def test_disabled_when_threshold_is_none():
    assert blocks_sell_cross(90.0, 100.0, None) is False


def test_no_cost_basis_never_blocks():
    assert blocks_sell_cross(90.0, 0.0, 0.0) is False
    assert blocks_sell_cross(90.0, -5.0, 0.0) is False


def test_blocks_when_below_threshold():
    # -10% vs a 0% (breakeven) requirement - blocked.
    assert blocks_sell_cross(90.0, 100.0, 0.0) is True


def test_allows_when_at_or_above_threshold():
    # exactly breakeven clears a 0% requirement.
    assert blocks_sell_cross(100.0, 100.0, 0.0) is False
    # a real gain clears it too.
    assert blocks_sell_cross(110.0, 100.0, 0.0) is False


def test_negative_threshold_allows_a_bounded_loss():
    # -1% is within an allowed -2% band - not blocked.
    assert blocks_sell_cross(99.0, 100.0, -0.02) is False
    # -3% exceeds the allowed -2% band - blocked.
    assert blocks_sell_cross(97.0, 100.0, -0.02) is True


def test_floor_disabled_by_default_never_forces_exit():
    # Both floors None - held for a very long time, deep underwater -
    # still no force (pre-floor behavior).
    assert gate_floor_should_force_exit(50.0, 100.0, bars_since_blocked=10_000) is False


def test_floor_no_cost_basis_never_forces_exit():
    assert gate_floor_should_force_exit(90.0, 0.0, bars_since_blocked=100,
                                         max_hold_bars=1, price_floor_pct=0.01) is False


def test_time_floor_forces_exit_once_bars_reached():
    # 11 bars held, max_hold_bars=10 - forced.
    assert gate_floor_should_force_exit(95.0, 100.0, bars_since_blocked=11, max_hold_bars=10) is True
    # 9 bars held, max_hold_bars=10 - not yet.
    assert gate_floor_should_force_exit(95.0, 100.0, bars_since_blocked=9, max_hold_bars=10) is False
    # exactly at the threshold - forced (>=, not >).
    assert gate_floor_should_force_exit(95.0, 100.0, bars_since_blocked=10, max_hold_bars=10) is True


def test_price_floor_forces_exit_before_the_real_stop_loss():
    # -6% loss, price_floor_pct=0.05 (tighter than the real 10% stop-loss) - forced.
    assert gate_floor_should_force_exit(94.0, 100.0, bars_since_blocked=1, price_floor_pct=0.05) is True
    # -4% loss - within the 5% floor, not forced.
    assert gate_floor_should_force_exit(96.0, 100.0, bars_since_blocked=1, price_floor_pct=0.05) is False
    # exactly at the floor - forced (<=, not <).
    assert gate_floor_should_force_exit(95.0, 100.0, bars_since_blocked=1, price_floor_pct=0.05) is True


def test_either_floor_independently_can_force_exit():
    # Price floor not yet hit, but time floor is - forced.
    assert gate_floor_should_force_exit(99.0, 100.0, bars_since_blocked=5,
                                         max_hold_bars=5, price_floor_pct=0.20) is True
    # Time floor not yet hit, but price floor is - forced.
    assert gate_floor_should_force_exit(70.0, 100.0, bars_since_blocked=1,
                                         max_hold_bars=1000, price_floor_pct=0.20) is True
    # Neither hit - not forced.
    assert gate_floor_should_force_exit(99.0, 100.0, bars_since_blocked=1,
                                         max_hold_bars=1000, price_floor_pct=0.20) is False
