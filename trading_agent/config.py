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

2026-09-23 (same day, a third pass): owner asked to optimize for return
subject to a hard "never deploy over 50% of capital" constraint, and to
stop pausing for confirmation on every parameter. Two decisions, made
without re-litigating each one individually per that request:

1. Built a REAL enforced aggregate cap (RISK_LIMITS["max_aggregate_position_pct"],
   new) rather than relying on max_position_pct x max_concurrent_positions
   composing correctly - they don't (15% x 5 = 75%, already over 50%
   before this pass). RiskManager.position_size() and portfolio_backtest.py
   both now take this as an independent final clamp on top of the
   per-asset sizing, using current mark-to-market value (so already-open
   positions appreciating can't quietly push aggregate exposure past the
   ceiling either). Set to 0.50 - this is what actually guarantees the
   50% constraint, not the other two limits.

2. Did NOT re-tune the underlying entry/exit signal logic (SMA windows,
   entry filter, cooldown, exit criteria, the RSI/volume filter
   decisions) chasing higher backtested returns - this session caught
   that exact trap multiple times already (RSI's inert "winner", the
   volume filter's knife-edge at ratio=0.5, the original win-count-first
   SL/TP ranking) and re-optimizing for raw return now would reintroduce
   it. Instead, swept max_position_pct with the new aggregate cap now
   acting as the real backstop - found 20% gave the best or near-best
   return in BOTH real test groups (Group A/IBIT-ETHA and Group B/GBTC-
   Solana) while still preserving full diversification (all assets in
   the more diverse group stayed simultaneously holdable) - see
   backtest_2026-09-23.md's "Optimizing within the 50% aggregate cap"
   section. max_position_pct: 0.15 -> 0.20.

Net live config after all three passes: max_position_pct=20%,
max_concurrent_positions=5, max_aggregate_position_pct=50% (hard cap,
new), auto_execute_max_usd=$100 (unchanged, still not meaningfully
binding at this position size - not revisited again since not asked).

2026-09-23 (same day, fourth pass): extended the agent from crypto-only to
also trade equities, per owner request ("Add stocks to the watchlist too"),
with two explicit owner choices: (1) stocks = a momentum screener run the
same way the crypto watchlist was (not hand-picked tickers) - see
STOCK_WATCHLIST below and watchlist_stocks_2026-09-23.md for the screener
methodology and full ranking; (2) shared risk budget - RISK_LIMITS is one
set of numbers spanning WATCHLIST and STOCK_WATCHLIST together, not
separate pools per asset class. This means max_aggregate_position_pct's 50%
hard cap, max_concurrent_positions' 5-position cap, and max_trades_per_day's
3-trade cap are all counted across crypto AND stock positions combined -
e.g. 3 open crypto positions plus 2 open stock positions already hits the
concurrent cap; a stock trade and two crypto trades in one day already hits
the daily trade cap. See PLAYBOOK.md's stock scanner-based cycle section for
how open_position_count/total_open_position_value are computed across both
lists together each cycle.

2026-09-23 (same day, fifth pass): owner asked to get out of meme coins and
into assets "that has a future" - clarified (AskUserQuestion) as blue-chip/
established crypto rather than literal stablecoins (a stablecoin barely
moves, so an SMA-crossover strategy has nothing to trade). No sell orders
were needed - the account held zero open crypto positions at the time, so
this was a pure watchlist swap, not an exit.

Removed: DOGE (dropped from the "core" carve-out - it's the origin meme
coin by reputation even though it was previously treated as core, not a
screener pick) and the entire meme-coin screener cluster from 2026-09-22
(PEPE, WIF, BONK, PENGU, FLOKI, MEW, POPCAT, SHIB).

Replaced with the same top-10-by-SMA(10,30)-crossover-strength methodology
used throughout this session, re-run against the 49-pair universe with an
explicit exclusion list applied first (meme/joke/political coins and the
one true stablecoin: DOGE, SHIB, PEPE, WIF, BONK, FLOKI, MEW, POPCAT, PNUT,
MOODENG, TRUMP, PENGU, WLFI, USDC) - not hand-picked, same evidence-based
approach as the crypto and stock watchlists. BTC/ETH/SOL kept as the
required "core" carve-out regardless of rank (same pattern as before, DOGE
just dropped out of that core set). Result: LIT, BCH, XCN, HBAR, DOT, CRV,
ZORA, LINK, AVAX, ASTER. PYTH and XLM (already non-meme, added 2026-09-22
for other reasons - see below) were untouched by this pass.
"""

WATCHLIST = [
    "BTC", "ETH", "SOL",  # core assets - DOGE dropped 2026-09-23 (meme-coin removal pass, see module docstring)
    "LIT", "BCH", "XCN", "HBAR", "DOT", "CRV", "ZORA", "LINK", "AVAX", "ASTER",  # top 10 blue-chip screener (2026-09-23, replaces the meme-coin cluster), see module docstring
    "PYTH", "XLM",  # added 2026-09-22 - PYTH is NOT covered by the SMA screener (see README)
]

# Top 10 by SMA(10,30) 1h crossover strength among liquid stocks (market cap
# > $2B, price > $10, 30d avg volume > 1M shares), screened 2026-09-23 - see
# watchlist_stocks_2026-09-23.md for the full methodology and ranking table.
# Shares RISK_LIMITS with WATCHLIST (shared budget, owner's explicit choice
# - see module docstring), not a separate risk pool.
#
# 2026-09-23 (later same day): TNGX and ARQT dropped ("Drop the two. We only
# pick winners here") after backtest_2026-09-23.md's real-data backtest
# found a genuine -15.2% overnight gap (MDLN, 2026-08-05) past the 10%
# stop-loss in a single move - an hourly check can't react until after the
# fact. TNGX and ARQT are both clinical-stage biotechs with real binary
# trial/FDA catalyst risk, categorically worse than MDLN's ordinary-
# volatility gap. No sell orders needed - zero open positions in either at
# the time. Left at 8 names rather than backfilling to 10 - not asked to
# replace them, and the remaining 8 aren't single-catalyst names.
#
# 2026-09-23 (later still): owner asked to replace the mid-cap names with
# larger ones ("Let's look at replacing the small cap stocks with larger
# ones. With more confidence, I will add more capital"). Re-ran the same
# screener with the market-cap floor raised from $2B to $10B (price > $10
# and 30d avg volume > 1M unchanged) - full replacement via the same
# top-10-by-crossover-strength methodology, not hand-picked winners (see
# watchlist_stocks_2026-09-23_large_cap.md for the ranking and the
# combined-portfolio backtest that validated it before this switch: +9.43%
# return / 4.94% max drawdown over the same ~90-day window the mid-cap
# list scored -7.64%/11.18% on). Real, well-known large/mega-caps: CRWD
# ($269B), PANW ($322B), TWLO ($45B), ILMN ($39B), IR ($30B), PTC ($15B),
# CHKP ($14B), MAIR ($13B), AR ($11B), HUBS ($11B).
#
# Honest caveat the backtest surfaced, not hidden: market cap does NOT
# eliminate gap risk the way dropping TNGX/ARQT addressed *binary
# clinical-trial* risk specifically - HUBS gapped -20.01% overnight on
# 2026-08-06 (an earnings reaction), a bigger single-move gap than MDLN's
# -15.2% that motivated the biotech removal. Earnings-driven gaps are a
# universal, ordinary risk across virtually every stock (including this
# list), bounded by max_position_pct (20%) and the 50% aggregate cap, not
# eliminated by market cap - the combined backtest above already includes
# that exact gap event and still came out ahead. No name was excluded on
# a hindsight basis (that would be cherry-picking after the fact) - all
# 10 are ordinary operating companies, not single-catalyst bets.
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
    "max_position_pct": 0.20,       # max 20% of portfolio value held per asset. 5% -> 50% ->
                                     # 15% -> 20% on 2026-09-23 across three re-backtested
                                     # passes - see module docstring and backtest_2026-09-23.md.
                                     # The real backstop against overconcentration is now
                                     # max_aggregate_position_pct below, not this value alone.
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
    "max_aggregate_position_pct": 0.50,  # HARD cap: current mark-to-market value of ALL open
                                     # positions combined may never exceed this fraction of
                                     # portfolio value - added 2026-09-23 because
                                     # max_position_pct x max_concurrent_positions doesn't
                                     # reliably compose into a portfolio-wide ceiling on its
                                     # own (e.g. 20% x 5 = 100%, well over 50% if unchecked).
                                     # This is what actually enforces "never use over 50% of
                                     # capital" - see RiskManager.position_size and
                                     # backtest_2026-09-23.md
}

# Master safety switch: no real orders are placed while True, auto-executed
# or approved. The bounded auto-execution policy above (RISK_LIMITS
# ["auto_execute_max_usd"]) is owner-authorized and ready, but flipping
# this to False is a separate, deliberate action the account owner takes
# themselves - see the module docstring.
DRY_RUN = False
