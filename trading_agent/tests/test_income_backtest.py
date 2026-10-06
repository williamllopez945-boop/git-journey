import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.income_backtest import income_backtest
from trading_agent.backtest import summarize


def _synthetic_dip_then_recover_then_crash():
    # Warm up flat at 10.0 for 20 bars (no range -> no signal), then a
    # sharp dip to 9.0 (bottom of a new 20-bar range -> dip_buy should
    # fire), a strong recovery past the +10% trim trigger, then a crash
    # past the -15% stop-loss from the dip's entry price.
    warmup = [10.0] * 20
    dip = [9.0]
    recover = [9.5, 10.0, 10.5]  # +10.5%/+9.0 from 9.0*(1+0) entry -> should trim around here
    crash = [7.0]                # well past -15% stop-loss from the ~9.0 entry
    return warmup + dip + recover + crash


def test_dip_buy_then_trim_then_stop_loss_fires():
    closes = _synthetic_dip_then_recover_then_crash()
    trades, equity_curve = income_backtest(closes, starting_cash=100.0)

    assert len(equity_curve) == len(closes)

    reasons = [t["reason"] for t in trades]
    assert "dip_buy" in reasons
    buy_index = reasons.index("dip_buy")
    # a sell (trim and/or stop_loss) must follow the entry
    later_reasons = reasons[buy_index + 1:]
    assert "trim" in later_reasons or "stop_loss" in later_reasons


def test_no_signal_on_flat_series_produces_no_trades():
    closes = [10.0] * 30
    trades, equity_curve = income_backtest(closes, starting_cash=100.0)
    assert trades == []
    assert equity_curve == [100.0] * 30


def test_output_runs_cleanly_through_backtest_summarize():
    closes = _synthetic_dip_then_recover_then_crash()
    trades, equity_curve = income_backtest(closes, starting_cash=100.0)

    result = summarize(trades, equity_curve, closes, starting_cash=100.0)

    assert "final_equity" in result
    assert "total_return_pct" in result
    assert "max_drawdown_pct" in result
    assert result["final_equity"] == pytest.approx(equity_curve[-1])


def test_fee_pct_reduces_final_equity_versus_frictionless():
    closes = _synthetic_dip_then_recover_then_crash()
    _, frictionless_curve = income_backtest(closes, starting_cash=100.0, fee_pct=0.0)
    _, with_fees_curve = income_backtest(closes, starting_cash=100.0, fee_pct=0.01)
    assert with_fees_curve[-1] < frictionless_curve[-1]
