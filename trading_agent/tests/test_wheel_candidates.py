import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.wheel_candidates import rank_by_wheel_fit, pick_strike_by_delta, pick_strike_by_otm_pct


def _row(ticker, last, iv, avg_options_volume=1000, open_interest=1000):
    return {"ticker": ticker, "columns": {
        "Symbol": ticker, "Last": str(last), "Implied volatility": str(iv),
        "Average options volume": str(avg_options_volume), "Open interest": str(open_interest),
    }}


def test_rank_sorts_by_iv_descending():
    rows = [_row("A", 10, 0.30), _row("B", 10, 0.55), _row("C", 10, 0.40)]
    ranked = rank_by_wheel_fit(rows, max_collateral_per_contract=10000)
    assert [r["ticker"] for r in ranked] == ["B", "C", "A"]


def test_rank_filters_out_collateral_over_budget():
    rows = [_row("CHEAP", 5, 0.40), _row("EXPENSIVE", 500, 0.60)]
    # EXPENSIVE needs 100*500 = $50,000 collateral, way over budget
    ranked = rank_by_wheel_fit(rows, max_collateral_per_contract=1000)
    assert [r["ticker"] for r in ranked] == ["CHEAP"]


def test_rank_attaches_collateral_per_contract():
    rows = [_row("A", 12.50, 0.40)]
    ranked = rank_by_wheel_fit(rows, max_collateral_per_contract=10000)
    assert ranked[0]["collateral_per_contract"] == pytest.approx(1250.0)


def test_rank_filters_below_liquidity_floors():
    rows = [_row("ILLIQUID", 10, 0.50, avg_options_volume=5, open_interest=5),
            _row("LIQUID", 10, 0.50, avg_options_volume=1000, open_interest=1000)]
    ranked = rank_by_wheel_fit(rows, max_collateral_per_contract=10000,
                                min_avg_options_volume=100, min_open_interest=500)
    assert [r["ticker"] for r in ranked] == ["LIQUID"]


def test_rank_skips_rows_missing_last_or_iv():
    rows = [{"ticker": "NEW", "columns": {"Symbol": "NEW"}}, _row("A", 10, 0.40)]
    ranked = rank_by_wheel_fit(rows, max_collateral_per_contract=10000)
    assert [r["ticker"] for r in ranked] == ["A"]


def test_pick_strike_by_delta_within_band():
    instruments = [
        {"strike": 10, "delta": -0.10},
        {"strike": 12, "delta": -0.22},
        {"strike": 14, "delta": -0.45},
    ]
    picked = pick_strike_by_delta(instruments, target_delta_min=0.15, target_delta_max=0.30, option_type="put")
    assert picked["strike"] == 12


def test_pick_strike_by_delta_picks_closest_to_midpoint():
    # band is 0.15-0.30, midpoint 0.225
    instruments = [
        {"strike": 10, "delta": -0.16},
        {"strike": 11, "delta": -0.23},
        {"strike": 12, "delta": -0.29},
    ]
    picked = pick_strike_by_delta(instruments, target_delta_min=0.15, target_delta_max=0.30, option_type="put")
    assert picked["strike"] == 11


def test_pick_strike_by_delta_none_when_nothing_qualifies():
    instruments = [{"strike": 10, "delta": -0.80}]
    picked = pick_strike_by_delta(instruments, target_delta_min=0.15, target_delta_max=0.30, option_type="put")
    assert picked is None


def test_pick_strike_by_otm_pct_put():
    # current price 100: strikes below are OTM for a put
    instruments = [{"strike": 95}, {"strike": 85}, {"strike": 70}]
    picked = pick_strike_by_otm_pct(instruments, current_price=100,
                                     target_otm_pct_min=0.10, target_otm_pct_max=0.20, option_type="put")
    assert picked["strike"] == 85  # 15% OTM, inside the 10-20% band


def test_pick_strike_by_otm_pct_call():
    instruments = [{"strike": 105}, {"strike": 115}, {"strike": 130}]
    picked = pick_strike_by_otm_pct(instruments, current_price=100,
                                     target_otm_pct_min=0.10, target_otm_pct_max=0.20, option_type="call")
    assert picked["strike"] == 115


def test_pick_strike_by_otm_pct_ignores_itm_strikes():
    # for a put, a strike at/above current price is ITM, not OTM
    instruments = [{"strike": 105}, {"strike": 85}]
    picked = pick_strike_by_otm_pct(instruments, current_price=100,
                                     target_otm_pct_min=0.10, target_otm_pct_max=0.20, option_type="put")
    assert picked["strike"] == 85
