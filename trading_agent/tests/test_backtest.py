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


def test_death_cross_sells_at_a_loss_when_gate_explicitly_disabled():
    # Buy at 9, decline to 8.6 (-4.44%). stop_loss_pct overridden to the
    # old 10% floor so this stays isolated to testing the profit-gate
    # logic (stop_loss_pct tightened to 4% 2026-09-28, which would
    # otherwise exit via stop_loss first and mask what's being tested
    # here - the gate's own reason/price on the resulting sell).
    # Explicitly passing None disables the gate, so it sells immediately,
    # the pre-2026-09-28 gate behavior (still available for comparison/
    # backtests that want it, just no longer the default).
    closes = [5.0] * 30 + [5, 5, 5, 5, 5, 9, 8.8, 8.7, 8.6, 8.6]
    trades, _ = backtest(closes, short_window=2, long_window=4, starting_cash=100.0,
                          min_sell_profit_pct=None, stop_loss_pct=0.10)
    death_crosses = [t for t in trades if t["reason"] == "death_cross"]
    assert len(death_crosses) == 1
    assert death_crosses[0]["price"] == 8.6


def test_death_cross_held_by_default_now_that_gate_is_adopted():
    # Same series, no min_sell_profit_pct passed at all - the adopted
    # 2026-09-28 default (0.0, breakeven) now applies automatically.
    # stop_loss_pct overridden to 10% for the same isolation reason as above.
    closes = [5.0] * 30 + [5, 5, 5, 5, 5, 9, 8.8, 8.7, 8.6, 8.6]
    trades, _ = backtest(closes, short_window=2, long_window=4, starting_cash=100.0,
                          stop_loss_pct=0.10)
    assert not any(t["reason"] == "death_cross" for t in trades)


def test_death_cross_held_at_a_loss_when_gate_requires_breakeven():
    # Identical series - with min_sell_profit_pct=0.0, the same
    # death-cross signal is held instead of executed because the
    # position is at -4.44%, below the breakeven threshold.
    # stop_loss_pct overridden to 10% for the same isolation reason as above.
    closes = [5.0] * 30 + [5, 5, 5, 5, 5, 9, 8.8, 8.7, 8.6, 8.6]
    trades, _ = backtest(closes, short_window=2, long_window=4, starting_cash=100.0,
                          min_sell_profit_pct=0.0, stop_loss_pct=0.10)
    assert not any(t["reason"] == "death_cross" for t in trades)
    buys = [t for t in trades if t["action"] == "buy"]
    assert len(buys) == 1  # position never closed, so no re-entry either


def test_death_cross_still_executes_when_gate_cleared():
    # Same setup, but decline stays small enough that a milder gate
    # (allowing up to a 5% loss) does not block the exit.
    # stop_loss_pct overridden to 10% for the same isolation reason as above.
    closes = [5.0] * 30 + [5, 5, 5, 5, 5, 9, 8.8, 8.7, 8.6, 8.6]
    trades, _ = backtest(closes, short_window=2, long_window=4, starting_cash=100.0,
                          min_sell_profit_pct=-0.05, stop_loss_pct=0.10)
    assert any(t["reason"] == "death_cross" for t in trades)


def test_gate_time_floor_forces_exit_after_max_hold_bars():
    # Same death-cross-then-blocked setup as
    # test_death_cross_held_at_a_loss_when_gate_requires_breakeven, held
    # flat afterward. With gate_max_hold_bars=5, the position is forced
    # out 5 bars after the block instead of riding indefinitely.
    # stop_loss_pct overridden to 10% for the same isolation reason as above.
    closes = [5.0] * 30 + [5, 5, 5, 5, 5, 9, 8.8, 8.7, 8.6] + [8.6] * 10
    trades, _ = backtest(closes, short_window=2, long_window=4, starting_cash=100.0,
                          min_sell_profit_pct=0.0, gate_max_hold_bars=5, stop_loss_pct=0.10)
    floor_exits = [t for t in trades if t["reason"] == "gate_floor"]
    assert len(floor_exits) == 1
    assert floor_exits[0]["price"] == 8.6
    # nothing remains open afterward
    buys = [t for t in trades if t["action"] == "buy"]
    assert len(buys) == 1


def test_gate_floor_does_not_fire_on_a_position_never_blocked():
    # A position that death-crosses and sells cleanly (gate disabled)
    # never sets blocked_since_index, so an aggressive floor has nothing
    # to act on - no spurious gate_floor exit.
    # stop_loss_pct overridden to 10% for the same isolation reason as above.
    closes = [5.0] * 30 + [5, 5, 5, 5, 5, 9, 8.8, 8.7, 8.6] + [8.6] * 10
    trades, _ = backtest(closes, short_window=2, long_window=4, starting_cash=100.0,
                          min_sell_profit_pct=None, gate_max_hold_bars=1,
                          stop_loss_pct=0.10)
    assert not any(t["reason"] == "gate_floor" for t in trades)
    assert any(t["reason"] == "death_cross" for t in trades)


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
