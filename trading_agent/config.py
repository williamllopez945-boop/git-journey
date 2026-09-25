"""Static configuration for the autonomous crypto + stock trading agent.

Edit these values to change the watchlist, strategy parameters, or risk
limits. DRY_RUN must be explicitly flipped to False to allow real orders.

This file shows CURRENT state only. For the reasoning behind any setting
- why it's the value it is, what it used to be, what changed and when -
see CHANGELOG.md in this directory. Every value below has a short inline
comment for what it does *today*; longer history lives there instead of
here, so this file stays scannable (split out 2026-09-24, audit).
"""

WATCHLIST = [
    "BTC", "ETH", "SOL",  # core assets, always held regardless of screener rank
    "LIT", "BCH", "XCN", "HBAR", "DOT", "CRV", "ZORA", "LINK", "AVAX", "ASTER",  # top-10 blue-chip screener pick
    "XLM",  # added 2026-09-22, predates the screener methodology - see CHANGELOG.md
]
# PYTH removed 2026-09-24 (audit follow-up) - it was the only watchlist
# asset with no documented reason for inclusion (added 2026-09-22, never
# screened or re-justified like everything else here) and the only one
# not covered by the crypto scanner, so it was structurally worse-served
# than every other asset (slower signal, no volume gate, flat-cap-only
# sizing). Zero open position at removal - pure watchlist edit, no sell
# needed. See CHANGELOG.md.

# Top 10 by SMA(10,30) 1h crossover strength among liquid, large-cap stocks
# (market cap > $10B, price > $10, 30d avg volume > 1M shares) - see
# watchlist_stocks_2026-09-23_large_cap.md for the full methodology and
# ranking. Shares RISK_LIMITS with WATCHLIST (shared budget), not a
# separate risk pool. Full change history: CHANGELOG.md.
STOCK_WATCHLIST = [
    "CRWD", "PANW", "TWLO", "ILMN", "IR", "PTC", "CHKP", "MAIR", "AR", "HUBS",
]

STRATEGY = {
    # Simple moving average crossover: short SMA crossing above/below the
    # long SMA on the latest price bar generates a buy/sell signal.
    "short_window": 10,
    "long_window": 30,
}

RISK_LIMITS = {
    "max_position_pct": 0.20,       # max 20% of portfolio value held per asset. The real
                                     # backstop against overconcentration is
                                     # max_aggregate_position_pct below, not this value alone.
                                     # History: CHANGELOG.md.
    "daily_loss_limit_pct": 0.03,   # halt all trading for the day past 3% drawdown
    "max_trades_per_day": 3,        # combined across all watchlist assets (crypto + stocks
                                     # share this one counter). Backtest-validated at 3 - see
                                     # backtest_2026-09-24_trade_cap.md and CHANGELOG.md.
    "auto_execute_max_usd": 100.0,   # fresh-crossover orders at/under this notional execute
                                     # automatically (all watchlist assets); larger orders
                                     # still require explicit per-trade approval. History:
                                     # CHANGELOG.md.
                                     # NOTE (2026-09-24 audit): at the current ~$200 portfolio
                                     # and 20% max_position_pct, the largest possible single
                                     # trade is ~$40 - well under this $100 threshold, so the
                                     # approval gate can't currently trigger; every properly-
                                     # sized entry auto-executes. This is intentional headroom
                                     # for when the account grows, not a bug - but it means the
                                     # "requires approval above $100" description above isn't
                                     # doing anything today. Revisit if/when the account grows
                                     # enough for $100 to be reachable, or lower this value if
                                     # the approval gate should have teeth sooner.
    "max_concurrent_positions": 5,  # at most this many WATCHLIST assets may have an open
                                     # position at once (~1/3 of the 14-asset watchlist) -
                                     # see backtest_2026-09-23.md's concurrent-positions sweep
    "max_aggregate_position_pct": 0.75,  # HARD cap: current mark-to-market value of ALL open
                                     # positions combined may never exceed this fraction of
                                     # portfolio value - added 2026-09-23 at 50%, raised to 75%
                                     # 2026-09-25 (owner request, after the 50% cap bound twice
                                     # in one day - once from a live buy, once from pure price
                                     # appreciation of already-held positions - see
                                     # CHANGELOG.md and daily_logs/2026-09-24.md). Still exists
                                     # because max_position_pct x max_concurrent_positions
                                     # doesn't reliably compose into a portfolio-wide ceiling on
                                     # its own (e.g. 20% x 5 = 100%, well over 75% if unchecked).
                                     # See RiskManager.position_size and backtest_2026-09-23.md.
    "awesome_trade_min_crossover_pct": 5.0,  # added 2026-09-25 (owner request): a fresh_buy_cross
                                     # whose |crossover_pct| clears this bar - the same threshold
                                     # scanner_signals.EXCELLENT_CROSSOVER_PCT already uses for
                                     # "worth a look" - is strong enough to size against
                                     # awesome_trade_aggregate_pct below instead of the normal
                                     # 75% cap, i.e. it may use the last 25% of aggregate budget
                                     # that an ordinary signal cannot. Deliberately reuses the
                                     # existing excellent_watch bar rather than inventing a new
                                     # number - untested via backtest, since PLAYBOOK.md sizing
                                     # policy isn't something backtest.py models; revisit if this
                                     # override fires often enough to be worth backtesting.
    "awesome_trade_aggregate_pct": 1.00,  # the aggregate ceiling an "awesome" trade (see above)
                                     # may size against - never higher than 100% of portfolio
                                     # value; still fully deployed, not leveraged.
}

# Master safety switch: no real orders are placed while True, auto-executed
# or approved. The bounded auto-execution policy above (RISK_LIMITS
# ["auto_execute_max_usd"]) is owner-authorized and ready, but flipping
# this to False is a separate, deliberate action the account owner takes
# themselves - see CHANGELOG.md.
DRY_RUN = False
