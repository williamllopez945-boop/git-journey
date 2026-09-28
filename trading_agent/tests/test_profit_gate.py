import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.profit_gate import blocks_sell_cross


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
