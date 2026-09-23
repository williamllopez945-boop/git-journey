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
