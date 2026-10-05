"""Profitability gate for the SMA death-cross sell signal (owner request,
2026-09-28, after a real DOGE/SOL exit both closed at a loss the strategy
never checked for). Optionally blocks a fresh_sell_cross/death-cross exit
unless the position's current unrealized P&L clears a minimum threshold,
so a plain trend-reversal signal doesn't force a loss realization on its
own - it only ever HOLDS the sell instead of executing it; it never forces
an exit. stop_loss_pct/take_profit_pct (exit_criteria.py) are unaffected
and still run first every bar, so a position held back by this gate is
still fully protected from an unbounded further decline - it can still
exit via stop-loss, just not via the death-cross alone while underwater.

Backtested 2026-09-28 against real 90-day hourly data (STOCK_WATCHLIST +
IBIT/ETHA proxies), worst-case first, both in isolation and combined at
the portfolio level (an isolated single-asset test already reversed once
this same week on RVMD vs. MAIR, so the combined result is the binding
one - see backtest_2026-09-28_sell_cross_profit_gate.md for the full
evidence). 0% (breakeven-or-better) was the one value that helped or was
flat everywhere it mattered; -2% was rejected as a non-monotonic
underperformer. **Adopted 2026-09-28** (owner approval) - live via
PLAYBOOK.md's "fresh_sell_cross" procedure, both crypto and stocks.
"""

MIN_SELL_PROFIT_PCT = 0.0  # breakeven or better required for a plain
                            # death-cross/fresh_sell_cross exit to
                            # execute; None disables the gate entirely
                            # (pre-2026-09-28 behavior: every death-cross
                            # sells immediately regardless of P&L). See
                            # backtest_2026-09-28_sell_cross_profit_gate.md.

GATE_MAX_HOLD_HOURS = None  # gate_floor_should_force_exit's max_hold_bars
                            # for live cycles - None means the gate can
                            # hold a position indefinitely (no time floor).
                            # Removed 2026-09-29 (owner request, backtested
                            # first): the 24h floor adopted 2026-09-28
                            # rarely triggered in the same 9-month real
                            # dataset (portfolio F1-F3 byte-identical with
                            # vs. without it), and removing it improved
                            # full-period return and combined drawdown
                            # (portfolio +39.05%/6.44% -> +42.56%/5.41%).
                            # One real caveat found and accepted anyway:
                            # stocks alone saw worse full-period drawdown
                            # without it (6.41% -> 7.60%), and the low
                            # trigger rate in this data means this isn't a
                            # strong test either way - see
                            # backtest_2026-09-29_gate_floor_removal.md.
                            #
                            # A companion price floor (force the exit once
                            # a gated position's loss reaches a threshold
                            # tighter than stop_loss_pct) was also built
                            # and backtested 2026-09-28, but found inert
                            # once stop_loss_pct is this tight (confirmed
                            # byte-identical backtest output with or
                            # without it) - removed 2026-09-28 (owner
                            # request, "keep it simple") rather than kept
                            # as dead code. See that backtest doc if this
                            # is revisited at a looser stop-loss.


def blocks_sell_cross(current_price, avg_cost_basis, min_sell_profit_pct):
    """True if a death-cross/fresh_sell_cross signal should be held
    instead of executed, because the position's current unrealized P&L
    (relative to avg_cost_basis) hasn't yet cleared min_sell_profit_pct.

    min_sell_profit_pct is a fraction, not a percent (0.0 = breakeven or
    better required, -0.02 = allows up to a 2% loss, matching every other
    *_pct convention in this project - e.g. exit_criteria.STOP_LOSS_PCT).
    None disables the gate entirely (every death-cross sells immediately,
    the unchanged pre-2026-09-28 behavior) - the default in every caller.

    avg_cost_basis<=0 never blocks (no real cost basis to gate against -
    same "nothing to check" convention as exit_criteria.check_exit).
    """
    if min_sell_profit_pct is None:
        return False
    if avg_cost_basis <= 0:
        return False
    pct_change = (current_price - avg_cost_basis) / avg_cost_basis
    return pct_change < min_sell_profit_pct


def gate_floor_should_force_exit(current_price, avg_cost_basis, bars_since_blocked,
                                  max_hold_bars=None):
    """True if a position that's been held under the gate should be forced
    out anyway, overriding blocks_sell_cross's "no" for this bar.

    blocks_sell_cross is only ever consulted once, at the bar a death-cross
    signal actually fires (strategy.sma_crossover_signal/scanner_signals.classify
    report "sell" as a one-time event, not a continuing state) - so once a
    signal is blocked, nothing re-checks the decision again until price
    recovers to min_sell_profit_pct or the position hits stop_loss_pct. A
    position that does neither for a long time is "held forever" by the
    gate. This function is a separate, every-bar check the caller runs for
    as long as a position remains in that blocked state (see backtest.py/
    portfolio_backtest.py for the bar-counting), independent of whether a
    fresh sell signal is present this bar.

    bars_since_blocked: how many bars have elapsed since the death-cross
    was first blocked for this position (0 = the block just happened).

    max_hold_bars: force the exit once bars_since_blocked reaches this
    many bars, regardless of P&L - a time-based backstop against the gate
    holding indefinitely. None (default) disables the floor - the gate
    can hold indefinitely, the pre-floor behavior. avg_cost_basis<=0
    never forces an exit (same "nothing to check" convention as
    blocks_sell_cross).
    """
    if avg_cost_basis <= 0:
        return False
    if max_hold_bars is not None and bars_since_blocked >= max_hold_bars:
        return True
    return False
