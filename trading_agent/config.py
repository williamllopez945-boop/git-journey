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
    "BTC", "ETH", "SOL", "DOGE",  # core assets, always held regardless of screener rank.
                                  # DOGE re-added 2026-09-26 (explicit owner request) - it
                                  # was part of the original BTC/ETH/SOL/DOGE core carve-out
                                  # until the 2026-09-23 meme-coin removal dropped it. See
                                  # CHANGELOG.md - this is a deliberate reversal of that
                                  # decision, not a re-litigation of it.
    "LIT", "BCH", "AERO", "HBAR", "DOT", "CRV", "ZORA", "LINK", "AVAX", "ASTER",  # top-10 blue-chip screener pick
    "XLM",  # added 2026-09-22, predates the screener methodology - see CHANGELOG.md
]
# PYTH removed 2026-09-24 (audit follow-up) - it was the only watchlist
# asset with no documented reason for inclusion (added 2026-09-22, never
# screened or re-justified like everything else here) and the only one
# not covered by the crypto scanner, so it was structurally worse-served
# than every other asset (slower signal, no volume gate, flat-cap-only
# sizing). Zero open position at removal - pure watchlist edit, no sell
# needed. See CHANGELOG.md.
# XCN -> AERO (2026-09-26 watchlist review): XCN's scanner data was frozen
# dead (SMA10==SMA30 every cycle observed, zero volume) - structurally
# incapable of ever firing a signal, not just weak-form. See
# watchlist_review_2026-09-26_crypto.md and CHANGELOG.md.

# Top 10 by SMA(10,30) 1h crossover strength among liquid, large-cap stocks
# (market cap > $10B, price > $10, 30d avg volume > 1M shares) - see
# watchlist_stocks_2026-09-23_large_cap.md for the full methodology and
# ranking. Shares RISK_LIMITS with WATCHLIST (shared budget), not a
# separate risk pool. Full change history: CHANGELOG.md.
# CHKP -> CRDO, HUBS -> PYPL (2026-09-26 watchlist review): CHKP/HUBS were
# the two worst 90-day backtested performers (-22.77%/-30.71%); CRDO/PYPL
# backtested +17.59%/+16.82% and passed the same $10B+ market cap screen.
# See watchlist_review_2026-09-26_stocks.md and CHANGELOG.md.
STOCK_WATCHLIST = [
    "CRWD", "PANW", "TWLO", "ILMN", "IR", "PTC", "CRDO", "MAIR", "AR", "PYPL",
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
                                     # position at once (~1/3 of the 15-asset watchlist) -
                                     # see backtest_2026-09-23.md's concurrent-positions sweep
    "max_aggregate_position_pct": 0.60,  # HARD cap: current mark-to-market value of ALL open
                                     # positions combined may never exceed this fraction of
                                     # portfolio value. History: 50% (2026-09-23) -> 75%
                                     # (2026-09-25, un-backtested, same-day live evidence the
                                     # 50% cap bound twice) -> 60% (2026-09-25, same day, after
                                     # backtesting 75%: worse than 50% in 3 of 4 windows tested,
                                     # incl. a negative-return worst case - see
                                     # backtest_2026-09-25_aggregate_cap.md's sweep section for
                                     # the full 50/55/60/65/70/75% comparison). 60% won on both
                                     # worst-case return (+4.41% vs 50%'s +4.33%) AND mean
                                     # return (+20.35% vs +19.39%) for a modest, bounded
                                     # worst-case drawdown cost (11.47% vs 9.70%) - 65%+ already
                                     # shows worst-case drawdown deteriorating sharply for no
                                     # further worst-case return gain. Still exists because
                                     # max_position_pct x max_concurrent_positions doesn't
                                     # reliably compose into a portfolio-wide ceiling on its own
                                     # (e.g. 20% x 5 = 100%, well over 60% if unchecked). See
                                     # RiskManager.position_size and backtest_2026-09-23.md.
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

# VOLTRAP - the options wheel strategy (cash-secured puts -> covered
# calls, added 2026-09-26, renamed to VOLTRAP same day) - a second,
# independent strategy on the same account. Deliberately NOT part of
# RISK_LIMITS/WATCHLIST above: a CSP's risk is reserved cash collateral
# (100 x strike per contract), not a mark-to-market position, so it
# doesn't compose with the crypto/stock bot's aggregate-position-value
# cap. See PLAYBOOK.md's "VOLTRAP" section and CHANGELOG.md for the
# full rationale.
VOLTRAP_WATCHLIST = [
    "SMCI", "MARA", "OKLO", "CLSK", "RGTI", "ASST", "NVDL", "SEDG",
]  # first standing list, 2026-09-26 (previously always [] - populated
   # live from the candidate screen each cycle with nothing persisted).
   # Screened via the tuned IV/liquidity scan, then vetted with
   # get_equity_fundamentals to exclude clinical-stage biotech
   # binary-catalyst risk (SMMT, PGEN) and one thin small-cap (GRRR)
   # that cleared the technical filters but not a fundamentals check.
   # See watchlist_review_2026-09-26_voltrap.md and CHANGELOG.md. Still
   # gated the same as ever: no real option order and no Routine until
   # max_voltrap_pct is confirmed and the account is funded.

VOLTRAP_RISK_LIMITS = {
    "max_voltrap_pct": 0.25,         # ceiling on total reserved options collateral
                                      # (CSP strikes + any assigned shares' cost
                                      # basis) as a fraction of total portfolio
                                      # value - proposed default, owner to confirm
                                      # before first real order. Conservative vs.
                                      # RISK_LIMITS' 60% aggregate cap since this
                                      # is a brand-new, unbacktested mechanism on
                                      # real assignment risk. History: CHANGELOG.md.
    "target_delta_min": 0.15,        # target strike band for both CSPs and
    "target_delta_max": 0.30,        # covered calls: roughly 70-85% chance of
                                      # expiring OTM (the point of the strategy -
                                      # collect premium, don't want assignment).
                                      # Falls back to an OTM-percentage proxy of
                                      # the same band if delta isn't available on
                                      # the option quote payload.
    "min_avg_options_volume": 100,    # liquidity floor for a VOLTRAP candidate -
    "min_open_interest": 500,        # a rich-premium but illiquid chain has real
                                      # slippage risk on the actual fill.
    "min_implied_volatility": 0.35,  # candidate screen's IV floor (fraction, not
                                      # percent - see get_scanner_filter_specs'
                                      # 0-1 gotcha) - the source of "richer
                                      # premium" this strategy is chasing.
}

# Auto-execution: recommend-only to start (my recommendation, approved
# 2026-09-26) - every cycle proposes a specific contract and waits for
# explicit approval, same bootstrap posture the crypto/stock bot itself
# started at before its own bounded auto-execution was authorized.
VOLTRAP_AUTO_EXECUTE = False
