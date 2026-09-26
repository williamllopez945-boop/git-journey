import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.watchlist_review import rank_by_crossover_strength, trailing_trade_pnl


def _row(ticker, sma10, sma30, **extra_cols):
    return {"ticker": ticker, "columns": {"Symbol": ticker, "SMA 10 (1h)": str(sma10),
                                           "SMA 30 (1h)": str(sma30), **extra_cols}}


def test_rank_sorts_by_absolute_crossover_strength_descending():
    rows = [
        _row("BTC", 101, 100),   # +1.0%
        _row("ETH", 90, 100),    # -10.0%
        _row("SOL", 105, 100),   # +5.0%
    ]
    ranked = rank_by_crossover_strength(rows)
    assert [r["ticker"] for r in ranked] == ["ETH", "SOL", "BTC"]


def test_rank_attaches_signed_crossover_pct():
    rows = [_row("BTC", 90, 100)]
    ranked = rank_by_crossover_strength(rows)
    assert ranked[0]["crossover_pct"] == pytest.approx(-10.0)


def test_rank_excludes_listed_tickers():
    rows = [_row("BTC", 101, 100), _row("DOGE", 200, 100)]
    ranked = rank_by_crossover_strength(rows, exclude=("DOGE",))
    assert [r["ticker"] for r in ranked] == ["BTC"]


def test_rank_skips_rows_missing_sma_columns():
    rows = [{"ticker": "NEW", "columns": {"Symbol": "NEW"}}, _row("BTC", 101, 100)]
    ranked = rank_by_crossover_strength(rows)
    assert [r["ticker"] for r in ranked] == ["BTC"]


def test_rank_skips_zero_sma30():
    rows = [_row("ZERO", 5, 0), _row("BTC", 101, 100)]
    ranked = rank_by_crossover_strength(rows)
    assert [r["ticker"] for r in ranked] == ["BTC"]


def test_rank_falls_back_to_symbol_column_when_ticker_empty():
    rows = [{"ticker": "", "columns": {"Symbol": "BTC", "SMA 10 (1h)": "101", "SMA 30 (1h)": "100"}}]
    ranked = rank_by_crossover_strength(rows)
    assert len(ranked) == 1


def test_pnl_none_when_asset_never_traded():
    trade_log = [{"asset": "ETH", "side": "buy", "quantity": 1, "price": 100}]
    assert trailing_trade_pnl("BTC", trade_log) is None


def test_pnl_realized_only_from_a_profitable_sell():
    trade_log = [
        {"asset": "BTC", "side": "buy", "quantity": 10, "price": 100},
        {"asset": "BTC", "side": "sell", "quantity": 10, "price": 150},
    ]
    assert trailing_trade_pnl("BTC", trade_log) == pytest.approx(500.0)


def test_pnl_realized_only_from_a_losing_sell():
    trade_log = [
        {"asset": "BTC", "side": "buy", "quantity": 10, "price": 100},
        {"asset": "BTC", "side": "sell", "quantity": 10, "price": 80},
    ]
    assert trailing_trade_pnl("BTC", trade_log) == pytest.approx(-200.0)


def test_pnl_unrealized_component_needs_current_price():
    trade_log = [{"asset": "BTC", "side": "buy", "quantity": 10, "price": 100}]
    assert trailing_trade_pnl("BTC", trade_log) == pytest.approx(0.0)
    assert trailing_trade_pnl("BTC", trade_log, current_price=120) == pytest.approx(200.0)


def test_pnl_combines_realized_and_unrealized():
    trade_log = [
        {"asset": "BTC", "side": "buy", "quantity": 10, "price": 100},
        {"asset": "BTC", "side": "sell", "quantity": 4, "price": 150},
    ]
    # Realized: 4 * (150 - 100) = 200. Remaining 6 @ cost 100, priced at 120: 6 * 20 = 120.
    assert trailing_trade_pnl("BTC", trade_log, current_price=120) == pytest.approx(320.0)


def test_pnl_sell_exceeding_open_quantity_is_clamped():
    trade_log = [
        {"asset": "BTC", "side": "buy", "quantity": 10, "price": 100},
        {"asset": "BTC", "side": "sell", "quantity": 15, "price": 150},
    ]
    # Only 10 units were ever open, so only 10 count as sold.
    assert trailing_trade_pnl("BTC", trade_log) == pytest.approx(500.0)


def test_pnl_ignores_other_assets():
    trade_log = [
        {"asset": "ETH", "side": "buy", "quantity": 100, "price": 2000},
        {"asset": "BTC", "side": "buy", "quantity": 1, "price": 90000},
    ]
    assert trailing_trade_pnl("BTC", trade_log, current_price=95000) == pytest.approx(5000.0)
