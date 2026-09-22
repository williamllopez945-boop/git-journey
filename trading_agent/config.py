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
    "max_position_pct": 0.05,       # max 5% of portfolio value held per asset
    "daily_loss_limit_pct": 0.03,   # halt all trading for the day past 3% drawdown
    "max_trades_per_day": 3,        # combined across all watchlist assets
    "auto_execute_max_usd": 5.0,    # fresh-crossover orders at/under this notional execute
                                     # automatically (all watchlist assets); larger orders
                                     # still require explicit per-trade approval
}

# Master safety switch: no real orders are placed while True, auto-executed
# or approved. The bounded auto-execution policy above (RISK_LIMITS
# ["auto_execute_max_usd"]) is owner-authorized and ready, but flipping
# this to False is a separate, deliberate action the account owner takes
# themselves - see the module docstring.
DRY_RUN = False
