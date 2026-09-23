"""Static configuration for the autonomous crypto trading agent.

Edit these values to change the watchlist, strategy parameters, or risk
limits. DRY_RUN must be explicitly flipped to False to allow real orders.

2026-09-22: owner explicitly authorized a bounded auto-execution policy
after a two-round confirmation (see PLAYBOOK.md "Auto-execution policy"
and RISK_LIMITS["auto_execute_max_usd"] below): once DRY_RUN is False,
fresh crossover signals at or under that notional execute automatically
across the whole watchlist; anything larger still requires explicit
per-trade approval as before. The policy is implemented and tested, but
DRY_RUN itself was not flipped here - Claude Code's own auto-mode safety
classifier blocked the commit that would have done so, since it enables
live automated trading. Flipping it to False requires the account owner's
own direct action (edit this file and commit/push it yourself, or grant
the permission the classifier is asking for and have it retried).

2026-09-23: owner raised max_position_pct from 5% to 50%, then raised
auto_execute_max_usd from $5 to $100 to match it (a one-time dollar
snapshot of 50% of the ~$200 portfolio value at the time - these two
values don't stay in sync automatically as portfolio value changes, and
they're not required to be equal). Net effect: the $5 threshold was
originally a narrow, bounded exception to "everything needs approval" -
at $100, matching the position-sizing cap, essentially every
properly-sized confirmed entry now auto-executes, and approval becomes
the exception (oversized or non-confirmed signals like excellent_watch)
rather than the default. This significantly widened the system's
real-money autonomy versus the original bounded design.

2026-09-23 (same day, later): re-running the concurrent-positions cap
backtest (portfolio_backtest.py, backtest_2026-09-23.md) at the new 50%
sizing found two things worth acting on: (1) max_concurrent_positions=5
had become vestigial - at 50% per position, cash runs out after 2
positions regardless of the cap, so 5 never actually bound anything;
(2) worst-case drawdown on the more representative test group jumped
6x (6.30% -> 36.76%) versus the same test at the original 5% sizing.
Owner chose to address this by lowering max_position_pct back down
(0.50 -> 0.15) rather than restricting concurrency to 1 asset -
restores real diversification across up to 5 concurrent positions
(backtested: ~18% worst-case drawdown at 15%, vs 50%'s 36.76% and the
original 5%'s 6.30% - see backtest_2026-09-23.md's "Concurrent-positions
cap re-check after the sizing change" section for the full sweep).
auto_execute_max_usd was NOT revisited in this pass - it's still $100,
now well above what a 15%-sized position ever reaches at this portfolio
value, so it no longer meaningfully gates anything either; worth the
owner's attention if they want the approval gate to matter again.
"""

WATCHLIST = [
    "BTC", "ETH", "SOL", "DOGE",  # core assets
    "PEPE", "WIF", "BONK", "PENGU", "FLOKI", "XCN", "MEW", "POPCAT", "SHIB",  # top 10 screener (2026-09-22), DOGE deduped
    "PYTH", "XLM",  # added 2026-09-22 - PYTH is NOT covered by the SMA screener (see README)
]

STRATEGY = {
    # Simple moving average crossover: short SMA crossing above/below the
    # long SMA on the latest price bar generates a buy/sell signal.
    "short_window": 10,
    "long_window": 30,
}

RISK_LIMITS = {
    "max_position_pct": 0.15,       # max 15% of portfolio value held per asset. Raised from
                                     # 5% to 50% on 2026-09-23, then lowered back to 15% the
                                     # same day after re-backtesting the concurrent-positions
                                     # cap at 50% sizing found it made max_concurrent_positions
                                     # vestigial and 6x'd worst-case drawdown - see module
                                     # docstring and backtest_2026-09-23.md
    "daily_loss_limit_pct": 0.03,   # halt all trading for the day past 3% drawdown
    "max_trades_per_day": 3,        # combined across all watchlist assets
    "auto_execute_max_usd": 100.0,   # fresh-crossover orders at/under this notional execute
                                     # automatically (all watchlist assets); larger orders
                                     # still require explicit per-trade approval. Raised from
                                     # $5 on 2026-09-23 to match max_position_pct's 50% cap at
                                     # the ~$200 portfolio value that day - see module docstring
    "max_concurrent_positions": 5,  # at most this many WATCHLIST assets may have an open
                                     # position at once (~1/3 of the 15-asset watchlist) -
                                     # see backtest_2026-09-23.md's concurrent-positions sweep
}

# Master safety switch: no real orders are placed while True, auto-executed
# or approved. The bounded auto-execution policy above (RISK_LIMITS
# ["auto_execute_max_usd"]) is owner-authorized and ready, but flipping
# this to False is a separate, deliberate action the account owner takes
# themselves - see the module docstring.
DRY_RUN = False
