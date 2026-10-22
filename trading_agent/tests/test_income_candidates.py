import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.income_candidates import spread_pct, filter_by_liquidity


def test_spread_pct_normal_quote():
    # bid 9.9, ask 10.1 -> spread 0.2, mid 10.0 -> 2%
    assert spread_pct(9.9, 10.1) == pytest.approx(0.02)


def test_spread_pct_missing_prices_returns_none():
    assert spread_pct(None, 10.0) is None
    assert spread_pct(10.0, None) is None


def test_spread_pct_non_positive_prices_returns_none():
    assert spread_pct(0.0, 10.0) is None
    assert spread_pct(-1.0, 10.0) is None
    assert spread_pct(10.0, 0.0) is None


def test_spread_pct_crossed_quote_returns_none():
    assert spread_pct(10.0, 9.0) is None
    assert spread_pct(10.0, 10.0) is None  # bid == ask treated as crossed/stale


def test_filter_by_liquidity_sorts_tightest_first():
    quotes = [
        {"symbol": "WIDE", "bid_price": 9.0, "ask_price": 11.0},   # spread ~20%
        {"symbol": "TIGHT", "bid_price": 9.95, "ask_price": 10.05}, # spread ~1%
    ]
    survivors = filter_by_liquidity(quotes, max_spread_pct=1.0)
    assert [row["symbol"] for row in survivors] == ["TIGHT", "WIDE"]


def test_filter_by_liquidity_excludes_above_threshold():
    quotes = [
        {"symbol": "LIQUID", "bid_price": 9.95, "ask_price": 10.05},
        {"symbol": "ILLIQUID", "bid_price": 9.0, "ask_price": 11.0},
    ]
    survivors = filter_by_liquidity(quotes, max_spread_pct=0.02)
    assert [row["symbol"] for row in survivors] == ["LIQUID"]


def test_filter_by_liquidity_drops_missing_or_crossed_rows():
    quotes = [
        {"symbol": "OK", "bid_price": 9.95, "ask_price": 10.05},
        {"symbol": "MISSING_ASK", "bid_price": 10.0, "ask_price": None},
        {"symbol": "CROSSED", "bid_price": 11.0, "ask_price": 10.0},
    ]
    survivors = filter_by_liquidity(quotes, max_spread_pct=1.0)
    assert [row["symbol"] for row in survivors] == ["OK"]


def test_filter_by_liquidity_attaches_spread_pct():
    quotes = [{"symbol": "A", "bid_price": 9.9, "ask_price": 10.1}]
    survivors = filter_by_liquidity(quotes, max_spread_pct=1.0)
    assert survivors[0]["spread_pct"] == pytest.approx(0.02)
    assert survivors[0]["symbol"] == "A"
