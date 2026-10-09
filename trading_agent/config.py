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
# MAIR -> VTRS (2026-09-29 watchlist review): MAIR was independently
# flagged as the weakest member 3 times (2026-09-26/09-27 reviews, then
# the 2026-09-29 walk-forward backtest's -21.92% real fold). Sourced 6
# candidates via the production scan; every one beat MAIR at the
# portfolio level (not just isolated). VTRS won on the binding portfolio
# metric (+31.66% vs. MAIR-in's +17.64% full-period, best worst-case
# fold among top candidates, lower turnover) despite a mediocre isolated
# result - another isolated/portfolio ranking flip. MAIR had zero open
# positions and zero trade history, so no liquidation was needed. See
# watchlist_review_2026-09-29_stocks.md and CHANGELOG.md.
# 10 -> 5 trim (2026-10-07 owner approval): VTRS/PYPL/AR/CRDO/IR removed -
# bottom 5 of all 10 ranked worst-case-first on a real 90-day/384-bar
# backtest (see watchlist_review_2026-10-06_stocks_top5.md). The kept-5
# portfolio cleanly beat the full-10 baseline on full-period return,
# worst-case half, AND max drawdown (6.90%/4.84% vs 5.07%/6.32%) - not
# just a mean-level improvement. No stock here has ever actually traded
# live (trade_log confirms), so this is backtest-only, same as every
# prior stock-side review. Caveat: with exactly 5 names now,
# RISK_LIMITS["max_concurrent_positions"]=5 stops being a real
# constraint on this list specifically - not a reason to avoid the
# trim, just noted; no RISK_LIMITS change proposed or made here.
STOCK_WATCHLIST = [
    "TWLO", "ILMN", "PTC", "CRWD", "PANW",
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
    "max_trades_per_day": 4,        # combined across all watchlist assets (crypto + stocks
                                     # share this one counter). Raised from 3 (2026-09-27,
                                     # owner request for more room) - the one value with a
                                     # positive worst-case on both real test beds checked:
                                     # STOCK_WATCHLIST's own 90-day data (worst +0.28%, vs 3's
                                     # +2.70% - a modest give-up) and a real 3.7-year, more
                                     # volatile 8-symbol universe (worst +5.82%, vs 3's +3.77% -
                                     # better there). See backtest_2026-09-24_trade_cap.md and
                                     # backtest_2026-09-27_trade_cap_recheck.md, and CHANGELOG.md.
    "auto_execute_max_pct": 0.20,    # fresh-crossover orders at/under this fraction of current
                                     # total portfolio value (RiskManager.can_auto_execute,
                                     # computed fresh each cycle from get_portfolio) execute
                                     # automatically (all watchlist assets); larger orders
                                     # still require explicit per-trade approval. Set equal to
                                     # max_position_pct (2026-09-27, owner request) so a
                                     # properly-sized confirmed entry always auto-executes and
                                     # approval stays the exception (oversized/unconfirmed
                                     # signals only) - the original 2026-09-22 design intent.
                                     # Replaces the flat-dollar auto_execute_max_usd, which was
                                     # a one-time snapshot of portfolio value (2026-09-23) that
                                     # went stale as equity changed - see CHANGELOG.md.
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
# ["auto_execute_max_pct"]) is owner-authorized and ready, but flipping
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
    "max_voltrap_pct": 1.00,         # ceiling on total reserved options collateral
                                      # (CSP strikes + any assigned shares' cost
                                      # basis) as a fraction of total portfolio
                                      # value. Raised from the proposed 0.25 default
                                      # to 1.00 (owner request, 2026-10-09, confirmed
                                      # via AskUserQuestion right after a real deposit
                                      # brought the account to $1,028.21) - the owner
                                      # explicitly chose to allocate the full account
                                      # to VOLTRAP rather than the conservative
                                      # default. Both real go-live conditions (owner
                                      # confirms this number; get_portfolio shows real
                                      # free cash) are now met - see CHANGELOG.md.
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

# Income sleeve (YieldMax-style weekly-distribution basket ETFs) - added
# 2026-10-06, live the same day (owner request: auto-execute from the
# start, no recommend-only trial period, unlike every other strategy
# here). Deliberately NOT part of RISK_LIMITS/STOCK_WATCHLIST above - a
# third, independent strategy, own budget, own state files
# (income_state.py), own entry signal (income_signals.classify_dip, a
# dip/support read, not the SMA crossover) and exit rule
# (income_exit.check_income_exit). See PLAYBOOK.md's "Income sleeve"
# section and income_candidates_2026-10-06.md for the full screen.
INCOME_WATCHLIST = ["YMAX", "YMAG", "ULTY", "CHPY", "GPTY", "AMDW", "GOOW", "NVDW"]
# 2026-10-07 owner-approved expansion (see
# income_candidates_2026-10-07_expansion.md for the full screen):
# - GPTY (YieldMax AI & Tech basket, unleveraged) - previously excluded on an
#   after-hours 3.19% spread (2026-10-06); re-checked during regular hours at
#   1.78%, clears the 2% liquidity filter. Same risk shape as the original 4.
# - AMDW/GOOW/NVDW (Roundhill "WeeklyPay" series) - owner-approved despite a
#   MATERIALLY DIFFERENT risk profile from the rest of this list: each is a
#   single-stock, 1.2x-LEVERAGED weekly payer (AMD/GOOGL/NVDA respectively),
#   not a diversified basket. Real 1.75yr price-only backtest: AMDW +89.17%,
#   GOOW +16.36%, NVDW -21.06% (max drawdowns 17.98-38.43%) - the two winners
#   are explained entirely by that one stock's own run, not a repeatable
#   edge; four other same-family single-stock funds screened the same day
#   (TSLW, COIW, HOOW, PLTW) lost 32-66% over the identical window and were
#   explicitly NOT added. Other previously-screened basket funds (LFGY, QDTY,
#   RDTY, SDTY, MINY, SLTY, TOPW) remain excluded on liquidity, re-confirmed
#   2026-10-07.

INCOME_RISK_LIMITS = {
    "max_position_pct": 0.05,          # smaller than the originally
                                        # proposed 10% - initial live run
                                        # (owner request), revisit after
                                        # a couple of real weeks.
    "max_aggregate_position_pct": 0.08, # smaller than the originally
                                        # proposed 15%. Same key name as
                                        # RISK_LIMITS' own
                                        # max_aggregate_position_pct -
                                        # RiskManager.position_size reads
                                        # this key by default.
    "max_concurrent_positions": 2,
    "max_trades_per_day": 2,
    "auto_execute_max_pct": 0.05,      # matches max_position_pct - every
                                        # correctly-sized entry
                                        # auto-executes, same convention
                                        # RISK_LIMITS uses.
    "daily_loss_limit_pct": 0.03,      # same value as RISK_LIMITS - shares
                                        # RiskManager.check_circuit_breaker's
                                        # mechanism, measured against total
                                        # account equity like the main bot's
                                        # own circuit breaker (not a
                                        # sleeve-only sub-slice).
}

INCOME_AUTO_EXECUTE = True  # live from the start, owner request 2026-10-06.
