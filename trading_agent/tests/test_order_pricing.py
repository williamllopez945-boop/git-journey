import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.order_pricing import marketable_limit_price, DEFAULT_BUFFER_PCT


def test_buy_prices_above_the_ask():
    # Real BCH quote shape (2026-10-04 cycle): ask 322.01380958.
    price = marketable_limit_price("buy", bid=315.885255, ask=322.01380958)
    assert price > 322.01380958
    assert price == pytest.approx(322.01380958 * (1 + DEFAULT_BUFFER_PCT))


def test_sell_prices_below_the_bid():
    price = marketable_limit_price("sell", bid=315.885255, ask=322.01380958)
    assert price < 315.885255
    assert price == pytest.approx(315.885255 * (1 - DEFAULT_BUFFER_PCT))


def test_custom_buffer_pct_overrides_default():
    price = marketable_limit_price("buy", bid=100, ask=100, buffer_pct=0.01)
    assert price == pytest.approx(101.0)


def test_invalid_side_raises():
    with pytest.raises(ValueError):
        marketable_limit_price("hold", bid=100, ask=101)
