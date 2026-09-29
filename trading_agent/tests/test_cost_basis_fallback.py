import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.cost_basis_fallback import average_cost_basis_from_trade_log


def test_none_when_no_trades_for_asset():
    trade_log = [{"asset": "ETH", "side": "buy", "quantity": 1, "price": 100}]
    assert average_cost_basis_from_trade_log("BTC", trade_log) is None


def test_single_buy_returns_its_price():
    # Mirrors the real PEPE position: one buy, 1,014,198 units @ $0.00000494.
    trade_log = [{"asset": "PEPE", "side": "buy", "quantity": 1014198, "price": 4.94e-06}]
    assert average_cost_basis_from_trade_log("PEPE", trade_log) == pytest.approx(4.94e-06)


def test_multiple_buys_weighted_average():
    trade_log = [
        {"asset": "BTC", "side": "buy", "quantity": 1, "price": 100},
        {"asset": "BTC", "side": "buy", "quantity": 3, "price": 200},
    ]
    # (1*100 + 3*200) / 4 = 175
    assert average_cost_basis_from_trade_log("BTC", trade_log) == 175.0


def test_partial_sell_leaves_average_unchanged():
    trade_log = [
        {"asset": "BTC", "side": "buy", "quantity": 10, "price": 100},
        {"asset": "BTC", "side": "sell", "quantity": 4, "price": 150},
    ]
    # Selling doesn't change the average cost of what's left.
    assert average_cost_basis_from_trade_log("BTC", trade_log) == 100.0


def test_full_sell_returns_none():
    trade_log = [
        {"asset": "BTC", "side": "buy", "quantity": 10, "price": 100},
        {"asset": "BTC", "side": "sell", "quantity": 10, "price": 150},
    ]
    assert average_cost_basis_from_trade_log("BTC", trade_log) is None


def test_sell_exceeding_open_quantity_is_clamped_not_negative():
    trade_log = [
        {"asset": "BTC", "side": "buy", "quantity": 10, "price": 100},
        {"asset": "BTC", "side": "sell", "quantity": 15, "price": 150},
    ]
    assert average_cost_basis_from_trade_log("BTC", trade_log) is None


def test_re_entry_after_full_exit_uses_only_new_buys():
    trade_log = [
        {"asset": "BTC", "side": "buy", "quantity": 10, "price": 100},
        {"asset": "BTC", "side": "sell", "quantity": 10, "price": 150},
        {"asset": "BTC", "side": "buy", "quantity": 5, "price": 300},
    ]
    assert average_cost_basis_from_trade_log("BTC", trade_log) == 300.0


def test_other_assets_in_log_are_ignored():
    trade_log = [
        {"asset": "ETH", "side": "buy", "quantity": 100, "price": 2000},
        {"asset": "BTC", "side": "buy", "quantity": 1, "price": 90000},
        {"asset": "SOL", "side": "buy", "quantity": 50, "price": 100},
    ]
    assert average_cost_basis_from_trade_log("BTC", trade_log) == 90000.0


# --- Regression tests: 2026-09-29 audit (pnl_reconciliation_2026-09-29.md) ---
#
# A transfer-in "buy" entry (no real order behind it - see position_state.py's
# reconciliation pattern) carries whatever placeholder price was on hand at
# the time it was recorded. This module has no way to know that price is a
# placeholder rather than a real fill - it averages whatever `trade_log`
# gives it. DOGE and SOL both got stale placeholders on 2026-09-26 that were
# never reconciled against the real closing-sale realized gain once each
# position fully closed (SOL flagged in daily_logs/2026-09-27.md but never
# corrected; DOGE never checked at all) - silently understating realized
# loss by $92.72 (DOGE) and $60.69 (SOL) in every report since. These tests
# pin the CORRECTED trade histories (derived from get_pnl_trade_history's
# real realized_gain, same back-calculation as the existing VWAP-price
# corrections) so a future change to this module's averaging logic can't
# silently reintroduce a wrong answer for either real position.

def test_doge_transfer_in_plus_real_buy_matches_corrected_cost_basis():
    # 2026-09-26 transfer-in (corrected placeholder) + 2026-09-27 real
    # VWAP-corrected buy (already right, 2026-09-28 audit) - no sell yet.
    trade_log = [
        {"asset": "DOGE", "side": "buy", "quantity": 1129.12766834, "price": 0.180421},
        {"asset": "DOGE", "side": "buy", "quantity": 49.64, "price": 0.09873026},
    ]
    avg_cost = average_cost_basis_from_trade_log("DOGE", trade_log)
    assert avg_cost == pytest.approx(0.1769808578562045, rel=1e-9)


def test_doge_full_lifecycle_matches_robinhood_realized_pnl():
    # Full corrected DOGE history: transfer-in, real buy, real sell.
    # get_pnl_trade_history(span=all) reports realized_gain=-95.71 on this
    # exact sell - cross-check that the corrected trade_log reproduces it
    # (previously this computed -$2.99, a $92.72 understatement).
    trade_log = [
        {"asset": "DOGE", "side": "buy", "quantity": 1129.12766834, "price": 0.180421},
        {"asset": "DOGE", "side": "buy", "quantity": 49.64, "price": 0.09873026},
        {"asset": "DOGE", "side": "sell", "quantity": 1178.76, "price": 0.095787},
    ]
    avg_cost_before_sell = average_cost_basis_from_trade_log("DOGE", trade_log[:2])
    realized = (0.095787 - avg_cost_before_sell) * 1178.76
    assert realized == pytest.approx(-95.71, abs=0.01)

    # The real buy quantities (1129.12766834 + 49.64) sum to 0.00766834
    # more than the real sell quantity (1178.76) - a genuine float-precision
    # dust remainder on the transfer-in amount, same pattern already
    # documented for ETH elsewhere in this project (daily_logs/2026-09-27.md).
    # Not a fully closed position: a dust quantity remains at the unchanged
    # average cost, not None.
    avg_cost_after_sell = average_cost_basis_from_trade_log("DOGE", trade_log)
    assert avg_cost_after_sell == pytest.approx(avg_cost_before_sell, rel=1e-9)


def test_sol_transfer_in_matches_corrected_cost_basis():
    # 2026-09-26 transfer-in, corrected from the owner's since-superseded
    # $130.00/unit figure (daily_logs/2026-09-27.md flagged this as likely
    # wrong at the time; the trade_log entry itself was never fixed until
    # this audit).
    trade_log = [
        {"asset": "SOL", "side": "buy", "quantity": 1.66043295, "price": 166.549955},
    ]
    assert average_cost_basis_from_trade_log("SOL", trade_log) == pytest.approx(
        166.549955, rel=1e-9
    )


def test_sol_full_lifecycle_matches_robinhood_realized_pnl():
    # get_pnl_trade_history(span=all) reports realized_gain=-78.20 on the
    # real closing sell - cross-check the corrected trade_log reproduces it
    # (previously this computed -$17.51, a $60.69 understatement).
    trade_log = [
        {"asset": "SOL", "side": "buy", "quantity": 1.66043295, "price": 166.549955},
        {"asset": "SOL", "side": "sell", "quantity": 1.66043295, "price": 119.45380832},
    ]
    assert average_cost_basis_from_trade_log("SOL", trade_log) is None

    avg_cost_before_sell = average_cost_basis_from_trade_log("SOL", trade_log[:1])
    realized = (119.45380832 - avg_cost_before_sell) * 1.66043295
    assert realized == pytest.approx(-78.20, abs=0.01)


def test_re_entry_after_transfer_in_position_fully_exits():
    # Transfer-in, full exit (clean round numbers - see the dust note above
    # for why the real DOGE numbers don't cleanly zero out), then a fresh
    # real buy (re-entry) - the transfer-in's cost basis must not leak into
    # the new position, same guarantee as
    # test_re_entry_after_full_exit_uses_only_new_buys above, exercised with
    # a transfer-in-shaped first leg specifically.
    trade_log = [
        {"asset": "DOGE", "side": "buy", "quantity": 1000, "price": 0.18},
        {"asset": "DOGE", "side": "sell", "quantity": 1000, "price": 0.10},
        {"asset": "DOGE", "side": "buy", "quantity": 100, "price": 0.11},
    ]
    assert average_cost_basis_from_trade_log("DOGE", trade_log) == pytest.approx(0.11)
