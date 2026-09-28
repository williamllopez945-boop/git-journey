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

Proposal only as of 2026-09-28 - see backtest_2026-09-28_sell_cross_profit_gate.md
for the real backtest evidence and recommendation. Not wired into
PLAYBOOK.md's live cycle procedure; exists here (and in backtest.py/
portfolio_backtest.py, both default-disabled via None) purely to let that
backtest run against the same production-shaped logic other parameter
changes in this project are tested with, not a reimplementation.
"""


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
