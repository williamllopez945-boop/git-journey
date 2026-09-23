import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.portfolio_backtest import portfolio_backtest, summarize_portfolio

# Flat, then a ramp that crosses and holds - same pattern proven in
# test_backtest.py, extended with plateau bars so entry_filter.confirmed_signal
# (one bar of persistence past the raw cross) also fires, not just the raw signal.
_RAMP_AND_HOLD = [5.0] * 30 + [5.0] * 5 + [9.0] * 10


def test_uncapped_lets_every_asset_open_a_position():
    series = {"A": list(_RAMP_AND_HOLD), "B": list(_RAMP_AND_HOLD)}
    trades, equity_curve, final_state = portfolio_backtest(
        series, short_window=2, long_window=4, starting_cash=1000.0,
        max_position_pct=0.5, max_concurrent_positions=None,
    )
    summary = summarize_portfolio(trades, equity_curve, 1000.0)
    assert summary["max_concurrent_positions_held"] == 2


def test_cap_of_one_blocks_the_second_concurrent_entry():
    series = {"A": list(_RAMP_AND_HOLD), "B": list(_RAMP_AND_HOLD)}
    trades, equity_curve, final_state = portfolio_backtest(
        series, short_window=2, long_window=4, starting_cash=1000.0,
        max_position_pct=0.5, max_concurrent_positions=1,
    )
    summary = summarize_portfolio(trades, equity_curve, 1000.0)
    assert summary["max_concurrent_positions_held"] == 1
    buys = [t for t in trades if t["action"] == "buy"]
    assert len(buys) == 1


def test_cap_none_and_cap_equal_to_asset_count_behave_the_same():
    series = {"A": list(_RAMP_AND_HOLD), "B": list(_RAMP_AND_HOLD), "C": list(_RAMP_AND_HOLD)}
    trades_uncapped, eq_uncapped, _ = portfolio_backtest(
        series, short_window=2, long_window=4, starting_cash=1000.0,
        max_position_pct=0.3, max_concurrent_positions=None,
    )
    trades_capped, eq_capped, _ = portfolio_backtest(
        series, short_window=2, long_window=4, starting_cash=1000.0,
        max_position_pct=0.3, max_concurrent_positions=3,
    )
    assert eq_uncapped == eq_capped


def test_sizing_uses_pct_of_total_portfolio_value_not_all_cash():
    # A single ramp-and-hold series with a 10% cap should never deploy more
    # than 10% of the portfolio's value into that one asset at entry.
    series = {"A": list(_RAMP_AND_HOLD)}
    trades, equity_curve, final_state = portfolio_backtest(
        series, short_window=2, long_window=4, starting_cash=1000.0,
        max_position_pct=0.10, max_concurrent_positions=None,
    )
    buys = [t for t in trades if t["action"] == "buy"]
    assert buys
    first_buy = buys[0]
    notional = first_buy["qty"] * first_buy["price"]
    assert notional <= 1000.0 * 0.10 + 1e-9


def test_empty_trades_summary_is_inert():
    series = {"A": [100.0] * 20}
    trades, equity_curve, final_state = portfolio_backtest(
        series, short_window=5, long_window=15, starting_cash=1000.0,
    )
    summary = summarize_portfolio(trades, equity_curve, 1000.0)
    assert summary["num_trades"] == 0
    assert summary["max_concurrent_positions_held"] == 0
    assert summary["total_return_pct"] == 0.0


def test_misaligned_series_lengths_raise():
    series = {"A": [1.0, 2.0, 3.0], "B": [1.0, 2.0]}
    try:
        portfolio_backtest(series, short_window=5, long_window=15)
        assert False, "expected ValueError"
    except ValueError:
        pass
