import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.backtest import backtest, summarize


def test_no_trades_when_flat_series_never_crosses():
    closes = [100.0] * 40
    trades, equity_curve = backtest(closes, short_window=10, long_window=30, starting_cash=100.0)
    assert trades == []
    assert equity_curve[-1] == 100.0


def test_buys_on_upward_crossover_and_tracks_equity():
    # Flat then a ramp up, engineered so short SMA crosses above long SMA.
    closes = [5.0] * 30 + [5.0, 5.0, 5.0, 5.0, 5.0, 9.0]
    trades, equity_curve = backtest(closes, short_window=2, long_window=4, starting_cash=100.0)
    buys = [t for t in trades if t["action"] == "buy"]
    assert len(buys) == 1
    assert buys[0]["reason"] == "fresh_buy_cross"
    # all cash deployed into the position
    assert equity_curve[-1] == buys[0]["qty"] * closes[-1]


def test_stop_loss_exits_full_position():
    # Buy on a crossover, then price craters past -10%.
    closes = [5.0] * 30 + [5.0, 5.0, 5.0, 5.0, 5.0, 9.0, 9.0, 9.0, 9.0, 7.0]
    trades, equity_curve = backtest(closes, short_window=2, long_window=4, starting_cash=100.0)
    sells = [t for t in trades if t["action"] == "sell"]
    assert any(t["reason"] == "stop_loss" for t in sells)
    stop_loss_trade = next(t for t in sells if t["reason"] == "stop_loss")
    # full exit means no position remains
    assert equity_curve[-1] == stop_loss_trade["cash_after"] or trades[-1]["action"] == "buy"


def test_summarize_computes_return_and_drawdown():
    closes = [100.0] * 40
    trades, equity_curve = backtest(closes, short_window=10, long_window=30, starting_cash=100.0)
    s = summarize(trades, equity_curve, closes, starting_cash=100.0)
    assert s["total_return_pct"] == 0.0
    assert s["buy_hold_return_pct"] == 0.0
    assert s["max_drawdown_pct"] == 0.0
    assert s["num_trades"] == 0
    assert s["win_rate_pct"] is None


def test_summarize_win_rate_from_round_trips():
    # Two clean up-then-down-then-up cycles engineered to trigger buy/death-cross exits.
    closes = ([5.0] * 30 +
              [5.0, 5.0, 5.0, 5.0, 5.0, 9.0] +   # crosses up -> buy
              [9.0, 9.0, 9.0, 9.0, 9.0, 5.0])     # crosses down -> sell (death cross)
    trades, equity_curve = backtest(closes, short_window=2, long_window=4, starting_cash=100.0)
    s = summarize(trades, equity_curve, closes, starting_cash=100.0)
    assert s["num_round_trips"] >= 1
    assert s["win_rate_pct"] is not None
