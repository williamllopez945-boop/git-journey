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
