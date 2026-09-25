# Config changelog

History of every change to `trading_agent/config.py`'s live settings,
moved out of `config.py`'s own module docstring on 2026-09-24 (audit) so
the config file itself stays short and scannable - this file is the
place to look for *why* a setting is what it is; `config.py` is the
place to look for what it currently *is*.

## 2026-09-22

Owner explicitly authorized a bounded auto-execution policy after a
two-round confirmation (see `PLAYBOOK.md` "Auto-execution policy" and
`RISK_LIMITS["auto_execute_max_usd"]`): once `DRY_RUN` is `False`, fresh
crossover signals at or under that notional execute automatically across
the whole watchlist; anything larger still requires explicit per-trade
approval as before. The policy was implemented and tested, but `DRY_RUN`
itself was not flipped at this point - Claude Code's own auto-mode
safety classifier blocked the commit that would have done so, since it
enables live automated trading. Flipping it to `False` required the
account owner's own direct action (edit `config.py` and commit/push it
themselves, or grant the permission the classifier asked for and have it
retried).

## 2026-09-23

**First pass.** Owner raised `max_position_pct` from 5% to 50%, then
raised `auto_execute_max_usd` from $5 to $100 to match it (a one-time
dollar snapshot of 50% of the ~$200 portfolio value at the time - these
two values don't stay in sync automatically as portfolio value changes,
and they're not required to be equal). Net effect: the $5 threshold was
originally a narrow, bounded exception to "everything needs approval" -
at $100, matching the position-sizing cap, essentially every
properly-sized confirmed entry now auto-executes, and approval becomes
the exception (oversized or non-confirmed signals like `excellent_watch`)
rather than the default. This significantly widened the system's
real-money autonomy versus the original bounded design.

**Second pass (same day).** Re-running the concurrent-positions cap
backtest (`portfolio_backtest.py`, `backtest_2026-09-23.md`) at the new
50% sizing found two things worth acting on: (1) `max_concurrent_positions=5`
had become vestigial - at 50% per position, cash runs out after 2
positions regardless of the cap, so 5 never actually bound anything;
(2) worst-case drawdown on the more representative test group jumped 6x
(6.30% -> 36.76%) versus the same test at the original 5% sizing. Owner
chose to address this by lowering `max_position_pct` back down
(0.50 -> 0.15) rather than restricting concurrency to 1 asset - restores
real diversification across up to 5 concurrent positions (backtested:
~18% worst-case drawdown at 15%, vs 50%'s 36.76% and the original 5%'s
6.30% - see `backtest_2026-09-23.md`'s "Concurrent-positions cap
re-check after the sizing change" section for the full sweep).
`auto_execute_max_usd` was NOT revisited in this pass - it stayed $100,
now well above what a 15%-sized position ever reaches at this portfolio
value, so it no longer meaningfully gated anything either.

**Third pass (same day).** Owner asked to optimize for return subject to
a hard "never deploy over 50% of capital" constraint, and to stop
pausing for confirmation on every parameter. Two decisions, made without
re-litigating each one individually per that request:

1. Built a REAL enforced aggregate cap (`RISK_LIMITS["max_aggregate_position_pct"]`,
   new) rather than relying on `max_position_pct` x `max_concurrent_positions`
   composing correctly - they don't (15% x 5 = 75%, already over 50%
   before this pass). `RiskManager.position_size()` and
   `portfolio_backtest.py` both now take this as an independent final
   clamp on top of the per-asset sizing, using current mark-to-market
   value (so already-open positions appreciating can't quietly push
   aggregate exposure past the ceiling either). Set to 0.50 - this is
   what actually guarantees the 50% constraint, not the other two
   limits.

2. Did NOT re-tune the underlying entry/exit signal logic (SMA windows,
   entry filter, cooldown, exit criteria, the RSI/volume filter
   decisions) chasing higher backtested returns - this session caught
   that exact trap multiple times already (RSI's inert "winner", the
   volume filter's knife-edge at ratio=0.5, the original win-count-first
   SL/TP ranking) and re-optimizing for raw return would reintroduce it.
   Instead, swept `max_position_pct` with the new aggregate cap now
   acting as the real backstop - found 20% gave the best or near-best
   return in BOTH real test groups (Group A/IBIT-ETHA and Group B/GBTC-
   Solana) while still preserving full diversification (all assets in
   the more diverse group stayed simultaneously holdable) - see
   `backtest_2026-09-23.md`'s "Optimizing within the 50% aggregate cap"
   section. `max_position_pct`: 0.15 -> 0.20.

Net live config after all three passes: `max_position_pct`=20%,
`max_concurrent_positions`=5, `max_aggregate_position_pct`=50% (hard
cap, new), `auto_execute_max_usd`=$100 (unchanged, still not
meaningfully binding at this position size - not revisited again since
not asked).

**Fourth pass (same day).** Extended the agent from crypto-only to also
trade equities, per owner request ("Add stocks to the watchlist too"),
with two explicit owner choices: (1) stocks = a momentum screener run
the same way the crypto watchlist was (not hand-picked tickers) - see
`STOCK_WATCHLIST` and `watchlist_stocks_2026-09-23.md` for the screener
methodology and full ranking; (2) shared risk budget - `RISK_LIMITS` is
one set of numbers spanning `WATCHLIST` and `STOCK_WATCHLIST` together,
not separate pools per asset class. This means `max_aggregate_position_pct`'s
50% hard cap, `max_concurrent_positions`' 5-position cap, and
`max_trades_per_day`'s 3-trade cap are all counted across crypto AND
stock positions combined - e.g. 3 open crypto positions plus 2 open
stock positions already hits the concurrent cap; a stock trade and two
crypto trades in one day already hits the daily trade cap. See
`PLAYBOOK.md`'s stock scanner-based cycle section for how
`open_position_count`/`total_open_position_value` are computed across
both lists together each cycle.

**Fifth pass (same day).** Owner asked to get out of meme coins and into
assets "that has a future" - clarified (AskUserQuestion) as blue-chip/
established crypto rather than literal stablecoins (a stablecoin barely
moves, so an SMA-crossover strategy has nothing to trade). No sell
orders were needed - the account held zero open crypto positions at the
time, so this was a pure watchlist swap, not an exit.

Removed: DOGE (dropped from the "core" carve-out - it's the origin meme
coin by reputation even though it was previously treated as core, not a
screener pick) and the entire meme-coin screener cluster from
2026-09-22 (PEPE, WIF, BONK, PENGU, FLOKI, MEW, POPCAT, SHIB).

Replaced with the same top-10-by-SMA(10,30)-crossover-strength
methodology used throughout this session, re-run against the 49-pair
universe with an explicit exclusion list applied first (meme/joke/
political coins and the one true stablecoin: DOGE, SHIB, PEPE, WIF,
BONK, FLOKI, MEW, POPCAT, PNUT, MOODENG, TRUMP, PENGU, WLFI, USDC) - not
hand-picked, same evidence-based approach as the crypto and stock
watchlists. BTC/ETH/SOL kept as the required "core" carve-out regardless
of rank (same pattern as before, DOGE just dropped out of that core
set). Result: LIT, BCH, XCN, HBAR, DOT, CRV, ZORA, LINK, AVAX, ASTER.
PYTH and XLM (already non-meme, added 2026-09-22 for other reasons - see
`STOCK_WATCHLIST`'s own history below) were untouched by this pass.

### `STOCK_WATCHLIST` changes (same day)

**TNGX/ARQT dropped** ("Drop the two. We only pick winners here") after
`backtest_2026-09-23.md`'s real-data backtest found a genuine -15.2%
overnight gap (MDLN, 2026-08-05) past the 10% stop-loss in a single
move - an hourly check can't react until after the fact. TNGX and ARQT
are both clinical-stage biotechs with real binary trial/FDA catalyst
risk, categorically worse than MDLN's ordinary-volatility gap. No sell
orders needed - zero open positions in either at the time. Left at 8
names rather than backfilling to 10 - not asked to replace them, and the
remaining 8 aren't single-catalyst names.

**Replaced mid-cap names with large-caps** ("Let's look at replacing the
small cap stocks with larger ones. With more confidence, I will add more
capital"). Re-ran the same screener with the market-cap floor raised
from $2B to $10B (price > $10 and 30d avg volume > 1M unchanged) - full
replacement via the same top-10-by-crossover-strength methodology, not
hand-picked winners (see `watchlist_stocks_2026-09-23_large_cap.md` for
the ranking and the combined-portfolio backtest that validated it before
this switch: +9.43% return / 4.94% max drawdown over the same ~90-day
window the mid-cap list scored -7.64%/11.18% on). Real, well-known
large/mega-caps: CRWD ($269B), PANW ($322B), TWLO ($45B), ILMN ($39B),
IR ($30B), PTC ($15B), CHKP ($14B), MAIR ($13B), AR ($11B), HUBS ($11B).

Honest caveat the backtest surfaced, not hidden: market cap does NOT
eliminate gap risk the way dropping TNGX/ARQT addressed *binary
clinical-trial* risk specifically - HUBS gapped -20.01% overnight on
2026-08-06 (an earnings reaction), a bigger single-move gap than MDLN's
-15.2% that motivated the biotech removal. Earnings-driven gaps are a
universal, ordinary risk across virtually every stock (including this
list), bounded by `max_position_pct` (20%) and the 50% aggregate cap,
not eliminated by market cap - the combined backtest above already
includes that exact gap event and still came out ahead. No name was
excluded on a hindsight basis (that would be cherry-picking after the
fact) - all 10 are ordinary operating companies, not single-catalyst
bets.

## 2026-09-24

**Raised, then reverted, `max_trades_per_day`.** Owner asked to raise
`RISK_LIMITS["max_trades_per_day"]` from 3 to 10 - not re-backtested
against this change specifically (unlike the position-sizing/
concurrent-cap passes above) at the time it was made. The per-trade
guards this doesn't touch still applied unchanged per trade:
`max_position_pct` (20%), `max_aggregate_position_pct` (50% hard cap),
`max_concurrent_positions` (5), and `auto_execute_max_usd` ($100).
Raising the daily *count* only meant more individual trades - each
still sized/capped/gated exactly as before - could execute in one day;
it did not raise how much any single trade or the portfolio's total
open exposure could be.

Same day: added `max_trades_per_day` support to `portfolio_backtest.py`
(it had none before) and backtested the 3 vs 10 change against real
hourly data for all 10 `STOCK_WATCHLIST` symbols (~90 days) - see
`backtest_2026-09-24_trade_cap.md`. cap=10 turned out identical to no
cap at all (daily trade count never exceeded 7 in this window) and
underperformed cap=3 (-2.81% vs +2.60% return, 34.1% vs 42.4% win rate).
A follow-up sweep (1-20) plus a split-window robustness check confirmed
cap=3 as the only value solidly positive in BOTH independent halves of
the window, not just a single-window peak. Owner reverted to 3 based on
this evidence. Crypto side not covered - no historicals source for the
current `WATCHLIST` composition.

**Audit / simplification pass.** Owner asked for a system audit and
approved three cleanups, none of which change live trading behavior
except the first:

1. Narrowed the local-polling signal path (`price_history.py` +
   `entry_filter.confirmed_signal`, `PLAYBOOK.md` steps 1-6) from the
   whole `WATCHLIST` to `PYTH` only - it's the one asset the crypto
   scanner doesn't cover. A same-day check found 14 of 15 watchlist
   assets sitting 28-29 hours from their first real polling signal
   (warm-up resets on every watchlist swap), while the scanner path was
   already producing real signals for the same assets from day one.
   Scanner-covered assets lose nothing - volatility-scaled sizing (step
   5d) was already polling-only and scanner entries never used it.
   `price_history.json` trimmed to PYTH's real accumulated bars only.
2. Added a note on `auto_execute_max_usd` explaining it's currently
   unreachable at this portfolio size (max single trade ~$40 vs $100
   threshold) - documentation only, value unchanged.
3. Moved this changelog out of `config.py`'s module docstring into this
   file, so `config.py` stays short and shows current state, not a
   running narrative.

**PYTH removed from WATCHLIST (same day, follow-up).** Owner asked
whether PYTH's inclusion was still justified. Checked the record rather
than assuming: every other current crypto holding has a documented
reason (BTC/ETH/SOL are an explicit "core" carve-out; the other 10 came
from the 2026-09-23 top-10-by-crossover-strength screener). PYTH's entry
just said "added 2026-09-22" - no rationale anywhere in this repo, and
it was explicitly left untouched (not re-evaluated) when the meme-coin
removal pass later applied that same screener methodology to everything
else. It was also structurally the worst-served asset on pure mechanics:
the only one the scanner didn't cover, meaning the only one still needing
the 32-hour local warm-up, never getting the volume-confirmation gate,
and (as of the audit above) falling back to flat-cap sizing. Confirmed
zero open PYTH position before removing - pure watchlist edit, no sell
needed, same pattern as every prior watchlist change this session.
`WATCHLIST` now 14 assets (was 15); `XLM` (also added 2026-09-22, but
scanner-covered) is unaffected. The local-polling path this asset
motivated (`price_history.py`, `entry_filter.confirmed_signal`,
volatility-scaled sizing) now applies to zero assets - left in place as
dormant, tested infrastructure rather than deleted, since a future
non-scanner-covered addition would need it again; see `PLAYBOOK.md`'s
note above its steps 1-6. `price_history.json` cleared to empty (no
asset left to track).

## 2026-09-25

Owner reviewed the day's 3 trades (DOT, LINK, HBAR buys) and 2 blocked
signals (XLM, BCH — both `blocked_aggregate_cap`) and asked for two
changes:

1. **`max_aggregate_position_pct` raised 0.50 → 0.75.** The 50% cap had
   bound twice in one day: once from a live buy (HBAR) consuming the
   last of the budget, once purely from the already-held DOT/LINK/HBAR
   positions appreciating past it (BCH's cross sized to $0 with no new
   buy involved). At $200 and ~$40/position that left room for only
   ~2-3 concurrent positions even though `max_concurrent_positions=5`
   suggests more. Not backtested against this specific change (the cap
   itself isn't a `backtest.py` parameter, unlike `stop_loss_pct`/
   `take_profit_pct`/etc.) — a direct owner risk-tolerance call.
2. **New "awesome trade" override**
   (`awesome_trade_min_crossover_pct=5.0`, `awesome_trade_aggregate_pct=1.00`):
   a confirmed `fresh_buy_cross` whose `|crossover_pct|` also clears the
   `excellent_watch` bar (5%, matching `scanner_signals.EXCELLENT_CROSSOVER_PCT`
   — reused rather than inventing a new number) may size against 100% of
   portfolio value instead of the normal 75% cap. Still fully deployed
   capital, never leveraged; `max_position_pct` (20%) and
   `max_concurrent_positions` (5) are unchanged — only the aggregate
   ceiling moves, and only for a trade strong enough to already qualify
   as `excellent_watch`-tier on its own. See `PLAYBOOK.md`'s "Hard
   rules" section for the exact sizing-call change.

Same session: added `trading_agent/run_cycle.py` (token-efficiency
request, unrelated to the risk-limit change above) to replace the
hand-written per-cycle Python `PLAYBOOK.md`'s scanner-based cycle used
to require, and narrowed the crypto/stock scans (`update_scan_filters`)
to just the current watchlist symbols instead of every instrument
Robinhood offers — see the tool-call log for the exact filter payloads.

**Same day, later: 75% backtested and found worse than 50%, replaced
with 60%.** Owner asked to backtest the un-backtested 75% change above.
`portfolio_backtest.py` extended with `awesome_trade_min_crossover_pct`/
`awesome_trade_aggregate_pct` so the override could be tested too (see
`backtest_2026-09-25_aggregate_cap.md`). Result: the awesome-trade
override never fired once across ~4 years of real data (harmless,
dormant); the 75% aggregate cap itself lost to 50% in 3 of 4windows
tested, including a negative-return worst case (most recent regime:
-4.25% vs 50%'s +12.98%, with higher drawdown). Reported back rather
than silently reverting. Owner asked to try 60-65% — swept
50/55/60/65/70/75% across the same 5 windows: **60% won on both
worst-case return (+4.41%, beating even 50%'s +4.33%) and mean return
(+20.35%), for a modest worst-case drawdown cost (11.47% vs 50%'s
9.70%)**; 65% is where the tradeoff turns bad (drawdown jumps to
16.38% for a worse worst-case return than 60%). `max_aggregate_position_pct`
set to 0.60. `awesome_trade_aggregate_pct`/`awesome_trade_min_crossover_pct`
unchanged (100%/5%) - dormant at every level tested, not specifically
tied to 75%.

**Same day, later still: `TAKE_PROFIT_PCT` raised 15% → 20%.** Owner
asked for a 1:2 risk/reward ratio (10% stop-loss / 20% take-profit).
The original 2026-09-23 stop-loss/take-profit sweep never tested this
specific combination (only 50%-take-profit variants, both rejected).
Backtested first against 48 real series (current watchlist composition,
90-day hourly + 3 daily regimes) - 22 helped/9 hurt/17 flat, mean delta
+2.02%, worst case -8.06% (well inside what the 50%-take-profit
combinations already failed at: -25.84% to -75.26%). Shipped:
`exit_criteria.TAKE_PROFIT_PCT = 0.20`, `STOP_LOSS_PCT` unchanged at
10%, `TAKE_PROFIT_SELL_FRACTION` unchanged at 70%. See
`backtest_2026-09-25_stop_take.md`.
