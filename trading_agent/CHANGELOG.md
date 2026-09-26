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

**Same day, later still: profit-lock stop built, tested, NOT adopted.**
Owner asked to tighten the stop-loss from -10% to +10% once a position's
unrealized gain hits 15% (pre-take-profit), so a reversal can't fully
round-trip a gain into a loss. Built the mechanism (mirrors the existing
disabled trailing stop's peak-tracking pattern exactly) and backtested
it against the same 48-series set used for the take-profit ratio change
that same day, at the requested 15%/10% plus two neighboring pairs.
**Every variant hurt more than it helped** - 15%/10% itself: 2 helped/6
hurt/40 flat, mean -1.36%, worst case -25.00% (a strong-trend regime cut
short before it would have reached the real 20% take-profit). Same root
cause as the 2026-09-24 trailing-stop finding, mirror-image mechanism:
clipping a position before a strong trend fully plays out costs more
than it protects. `PROFIT_LOCK_TRIGGER_PCT`/`PROFIT_LOCK_STOP_PCT` left
`None` (disabled) - mechanism built and tested, matching the trailing
stop's own built-but-disabled treatment, but not shipped live. See
`backtest_2026-09-25_profit_lock.md`.

**Same day, later still: weekly watchlist review added.** Owner asked
for a standing weekly review to drop underperforming
`WATCHLIST`/`STOCK_WATCHLIST` names and bring in stronger candidates,
rather than only reviewing on request as every prior watchlist change
this session did (`watchlist_2026-09-22.md`,
`watchlist_2026-09-23_meme_removal.md`,
`watchlist_stocks_2026-09-23_large_cap.md`). Added
`trading_agent/watchlist_review.py` (`rank_by_crossover_strength` for
sourcing candidates - same method every past swap used - and
`trailing_trade_pnl` for scoring current holdings by what they actually
made or lost, not today's signal strength) plus a new "Weekly watchlist
review" section in `PLAYBOOK.md` documenting the full procedure and a
new self-bound "Weekly watchlist review" Routine (Sundays 15:00 UTC).
**This review only ever produces a written recommendation** -
`config.py` is never edited by the Routine itself; a swap happens only
after explicit owner approval, same posture the hourly Routine already
holds for `WATCHLIST`/`STOCK_WATCHLIST`. 13 new tests, 170/170 passing.

## 2026-09-25 (later): stock scan pagination gap fixed

After the owner asked whether two market days of live data (2026-09-24,
2026-09-25) surfaced anything worth changing, review of both days'
after-action logs found that the production stock scan (scan_id
`6e009dcf-...`) had silently evaluated only 1 of `STOCK_WATCHLIST`'s 10
names (`ILMN`) on nearly every market-hours cycle either day - the scan's
~398-stock universe returns only its first 200 rows (sorted by price,
no pagination exposed), and the other 9 names never landed on that page.
Not a strategy problem - a data-sourcing one, and one the strategy could
not have surfaced itself, since a symbol that never appears in the scan
also never gets logged as "skipped."

**Fixed** by no longer sourcing `STOCK_WATCHLIST`'s live signals from
that scan at all: new `equity_signals.py` computes sma10/sma30/
pct_change/relative_volume directly per symbol from `get_equity_historicals`
(1h bars, regular hours - 10 symbols per call, exactly the watchlist
size) and `get_equity_quotes` (previous close). `scanner_signals.classify()`
needed no changes - it was already asset-agnostic, just fed bad/missing
inputs for 9 of 10 stocks. `run_cycle.py --asset-class stock` now takes
`--historicals-file`/`--quotes-file` instead of `--scan-file`. Dry-run
verified live against real `get_equity_historicals`/`get_equity_quotes`
data for the full watchlist before wiring it in: all 10 symbols now
produce real classifications every cycle, not just `ILMN`. 12 new tests
(`test_equity_signals.py` plus `run_cycle.py` coverage), 183/183 passing.
`PLAYBOOK.md`'s stock scanner cycle (steps 1-3) and `README.md` updated
to match. The stock scan itself is untouched and still used, unchanged,
for sourcing *new* candidates during the weekly watchlist review - that
use case needs to discover symbols outside the watchlist, which
`equity_signals.py` can't do by design, so that narrower gap (documented
in `PLAYBOOK.md`'s "Weekly watchlist review" section) remains open.

## 2026-09-26: options wheel strategy added (cash-secured puts -> covered calls)

Owner requested a second, independent strategy on the same account:
sell weekly cash-secured puts for premium, sell weekly covered calls if
assigned, goal being income (collect premium) not assignment. Leveraged
ETFs explicitly in scope. Resolved via `AskUserQuestion` before building:
capital comes from **new funds the owner will deposit**, sized as a
**% of total portfolio value** rather than a fixed dollar cap.

Verified the account (`581911765`) already has `option_level_3` - no
upgrade needed. Found live: free cash is only ~$82 (rest is in the
crypto bot's positions) - confirmed via a real `review_option_order`
call on a real candidate (MARA $11.50 put, 2026-10-02 expiration) that
this genuinely can't go live yet: the order preview returned
`OPTION_NOT_ENOUGH_BP_FOR_COLLATERAL`, needing a **$1,055.35** deposit
against the $1,150 collateral requirement. Nothing was placed - this
confirms the mechanism end-to-end without funding it.

**New, independent system - deliberately not part of `RISK_LIMITS`:**
a CSP's risk is reserved cash collateral, not a mark-to-market position,
so it doesn't compose with the crypto/stock bot's aggregate-position-value
cap. Added `WHEEL_RISK_LIMITS` (own dict, `config.py`) with a proposed
`max_wheel_pct` of 25% (owner to confirm before going live - conservative
vs. the crypto/stock bot's 60%, since this is a brand-new, unbacktested
mechanism carrying real assignment risk and no options-historicals
source exists here to backtest it against), a `target_delta_min`/`_max`
band of 0.15-0.30 (roughly 70-85% chance of expiring OTM - the point of
the strategy), and liquidity floors. Added `WHEEL_WATCHLIST` (starts
empty, populated by the live screen each cycle) and `WHEEL_AUTO_EXECUTE`
(`False` - recommend-only to start, same conservative bootstrap the
crypto/stock bot itself used before its own auto-execution was
authorized).

New files: `wheel_state.py` (per-symbol state machine:
idle -> csp_open -> {idle, holding_shares} -> covered_call_open ->
{holding_shares, idle}, mirrors `position_state.py`'s persisted-store
pattern) and `wheel_candidates.py` (`rank_by_wheel_fit`,
`pick_strike_by_delta`/`pick_strike_by_otm_pct`, mirrors
`watchlist_review.py`'s pure-function pattern). 33 new tests, 204/204
passing.

**Candidate screen tuned live against real data, not guessed:** built a
new saved scan (`create_scan`, `HIGH_OPTIONS_VOLUME_IV`-style custom
filters) and iterated twice before it was usable. First attempt (IV >
35% alone, loose liquidity floors) surfaced almost entirely distressed
microcap/biotech names with 100-300% IV - real tail/binary-event risk,
not genuine wheel candidates. Second attempt raised liquidity floors
(avg options volume > 1,000, open interest > 5,000) but still mostly
speculative microcaps. **Fixed:** bounded IV to a BETWEEN band (35-80%,
not floor-only - a ceiling turns out to matter as much as a floor, since
"higher IV" alone selects for scarier tail risk, not richer safe premium),
raised liquidity floors further (avg options volume > 5,000, open
interest > 20,000), and added a $5 price floor. The resulting scan
(`e3983260-740b-4a84-8369-54420cbeafdd`, sorted `Last asc` to bias
toward budget-affordable names) surfaces recognizable liquid names
(SMCI, MARA, RGTI, OKLO, NVDL, TSLL, BITX) instead of penny-stock/biotech
noise. Also found (same known class of gap as the stock scan's own
pagination cap): 392-400 total matches, 200-row cap, so the returned
page's sort order matters a lot and must be reconsidered as the wheel's
real budget changes - documented in `PLAYBOOK.md`.

Dry-run verified the full pipeline against real market data before
shipping: `rank_by_wheel_fit` against real scan rows (with an
illustrative $2,000 budget, not the real ~$82 one, purely to prove the
filtering/sorting logic) correctly kept 110 of 200 candidates within
collateral and above the liquidity floors; `get_option_chains` /
`get_option_instruments` / `get_option_quotes` for real MARA puts
confirmed the quote payload **does carry `delta`** (so
`pick_strike_by_delta` is the primary path, `pick_strike_by_otm_pct`
only a documented fallback) and that `pick_strike_by_delta` correctly
picked the one real contract (11.50 strike, delta -0.185) inside the
0.15-0.30 target band out of seven real strikes checked.

New "Options wheel strategy" section added to `PLAYBOOK.md` documenting
the full state machine, screen, and weekly/daily cycle procedure. **Not
live**: no Routine created, no real order will be placed, until (a) the
owner confirms the `max_wheel_pct` number and (b) new funds are visible
in the account.

## 2026-09-26 — System audit (owner request, after the HBAR permission fix)

Full-system pass across `trading_agent/` and `research_agent/`: 204+11
tests re-run green, `.mcp.json`/`.gitignore` checked for exposed
secrets (none), every scheduled Routine's stored prompt cross-checked
against the current `PLAYBOOK.md` (all four in sync), no stray
TODO/FIXME markers, all "built but not wired live" modules
(`rsi_filter.py`, the `price_history.py`/`entry_filter.py`/
`volatility_sizing.py` polling path, `TRAILING_STOP_PCT`/
`PROFIT_LOCK_*`) confirmed intentional and already documented
(backtest-rejected or scoped to zero current assets), not orphaned code.

**One real gap found and fixed:** the manual HBAR sell (see the 15:47
UTC entry in today's live log) skipped `PositionStateStore().record_exit`
- the 4h re-entry whipsaw cooldown that's supposed to start on every
full position close. Added retroactively from the real fill timestamp.

**One gap re-confirmed, still open (not urgent - unfunded):** the
options-wheel candidate scan's 200-row cap (documented above) is sorted
`Last asc` (cheapest-first) - as the wheel's budget grows this will
keep hiding pricier, possibly-better candidates rather than just
trimming weak ones. Revisit the scan's filters/sort before scaling the
budget up.

**Checked and NOT a bug:** the weekly watchlist review's stock
candidate-sourcing scan (`6e009dcf...`, same 200-row cap) is sorted
`Crossover % desc` - the cap only trims the *weakest* 198 signals of
398, which is exactly what `rank_by_crossover_strength` wants; current
`STOCK_WATCHLIST` members correctly don't appear in the top 200 (their
crossover has cooled since they were picked) but that's irrelevant since
they're excluded from "addition candidate" ranking anyway. This looked
like the same class of bug as the already-fixed hourly-cycle stock-scan
gap (sorted by price, applied to a small fixed list) but isn't - sort
order matters, and this one already happens to be the right one.

No other issues found. Full history in this file and `daily_logs/
2026-09-24-live-log.md`.

## 2026-09-26 — Options wheel strategy renamed to VOLTRAP

Owner request (naming only - no behavior change). The options wheel
strategy built earlier today is now branded **VOLTRAP**. Renamed
throughout: `wheel_state.py` -> `voltrap_state.py`, `wheel_candidates.py`
-> `voltrap_candidates.py` (and their test files), `WheelStateStore` ->
`VoltrapStateStore`, `rank_by_wheel_fit` -> `rank_by_voltrap_fit`,
`WHEEL_WATCHLIST`/`WHEEL_RISK_LIMITS`/`WHEEL_AUTO_EXECUTE` (config.py) ->
`VOLTRAP_WATCHLIST`/`VOLTRAP_RISK_LIMITS`/`VOLTRAP_AUTO_EXECUTE`,
`max_wheel_pct` -> `max_voltrap_pct`, `wheel_state.json` ->
`voltrap_state.json` (was empty - no data migration needed).
`PLAYBOOK.md`'s "Options wheel strategy" section is now "VOLTRAP", and
`README.md` updated to match.

Older entries above this one still say `wheel_state.py`/`WHEEL_*` -
that's the accurate historical record of what things were named when
they were built; left as-is rather than rewritten. Everything currently
live uses the VOLTRAP names. No open PR/Routine referenced the old
names (VOLTRAP has no Routine yet - still unfunded, see above), so
nothing else needed updating. 215/215 tests passing after the rename.

## 2026-09-26 — Three-watchlist refresh + research_agent scope extension

Owner request: "work on our watchlists. One for crypto. One for
options, and one for just stocks. Have our research agent support this
effort." Clarified via `AskUserQuestion`: refresh all three with real
candidates now (not just a process rebuild), and extend `research_agent`
to cover stocks + VOLTRAP (not crypto - that scope decision from
2026-09-23 stands).

**Three review docs written, matching this project's standing "screen
-> backtest/trailing-perf -> write a doc -> owner approves before
config.py changes" discipline** (same as every prior watchlist swap):

- `watchlist_review_2026-09-26_crypto.md` - re-ran the crossover screen
  plus real trailing P&L (`trade_log`) for the 4 traded assets, and
  multi-day `cycle_log.json` history (not just today's snapshot) for
  the rest. Found `XCN`'s scanner data is **frozen dead** (SMA10==SMA30
  every cycle observed, zero volume) - a structural defect, not just
  weak form. One clean swap proposed: `XCN` -> `AERO`. Everything else
  that looked weak on today's snapshot alone (BCH, XLM, ASTER) turned
  out to be noisy/oscillating on the multi-day check, not persistently
  bad - no change proposed for those (avoided a false-positive swap).
- `watchlist_review_2026-09-26_stocks.md` - stocks have a real
  historicals source, so this ran genuine `backtest.py` passes (90d
  hourly) for every current member and every screened candidate, not
  just a crossover snapshot. `HUBS` (-30.71%) and `CHKP` (-22.77%) are
  clear bottom-2 by backtested return; proposed swapping them for
  `PYPL` (+16.82%) and `CRDO` (+17.59%). Notably, the top-ranked
  screener candidate by today's crossover (`BE`) backtested **negative**
  (-4.03%) and was rejected on that basis alone - exactly the "never
  swap on a screener snapshot alone" scenario this project's rule
  exists for.
- `watchlist_review_2026-09-26_voltrap.md` - VOLTRAP_WATCHLIST turns
  from "always empty, populated live" into a **reviewed, standing list**
  for the first time: screened the tuned candidate scan, excluded two
  clinical-stage biotechs (`SMMT`, `PGEN` - same binary-catalyst-risk
  reasoning that excluded TNGX/ARQT from the stock watchlist) and one
  thin small-cap (`GRRR`) despite all three clearing the technical
  IV/liquidity filters, landing on 8 names: `SMCI, MARA, OKLO, CLSK,
  RGTI, ASST, NVDL, SEDG`.

**`research_agent` scope extended** (`research_agent/config.py`):
`WATCHLIST` is now the union of `STOCK_WATCHLIST` and
`VOLTRAP_WATCHLIST` (deduplicated), not `STOCK_WATCHLIST` alone -
every VOLTRAP candidate is a real stock/ETF underneath the option, so
the same equity news/SEC-filing/earnings tools already cover it, no new
data source needed. Crypto remains explicitly out of scope (owner
re-confirmed this, not revisited). `README.md`/`PLAYBOOK.md` updated in
both `trading_agent/` and `research_agent/`; the daily research
Routine's own stored prompt updated to match (same reason the hourly
trading Routine's prompt needed updating after the stock-scan-pagination
fix - it duplicates the procedure rather than only pointing at it).

**None of the three `config.py` watchlists have been edited.** All
three docs are recommendations awaiting explicit owner approval, per
this project's standing rule that a watchlist swap is never a side
effect of an automated or delegated review. 215/215 tests still passing
(only `research_agent/config.py`'s `WATCHLIST` computation actually
changed code-wise; the rest of this pass is docs).

## 2026-09-26 — Watchlist swaps approved and applied ("Push to Robinhood")

Owner approved all three recommendations from the same-day review docs
and asked to push them live and create matching Robinhood watchlists.
`config.py` changed:

- `WATCHLIST`: `XCN` -> `AERO`.
- `STOCK_WATCHLIST`: `CHKP` -> `CRDO`, `HUBS` -> `PYPL`.
- `VOLTRAP_WATCHLIST`: `[]` -> `["SMCI", "MARA", "OKLO", "CLSK", "RGTI",
  "ASST", "NVDL", "SEDG"]` (first standing list - previously always
  empty, populated live from the scan each cycle with nothing
  persisted).

No sell orders needed - none of the removed names (`XCN`, `CHKP`,
`HUBS`) held an open position. `research_agent.config.WATCHLIST`
recomputes automatically from the union (no separate edit needed - see
the prior entry). Full reasoning for each swap is in the three
`watchlist_review_2026-09-26_*.md` docs; this entry just records that
they were approved and applied, same day. 215/215 tests passing.

Also created three real Robinhood watchlists this pass (crypto, stock,
VOLTRAP-candidates), mirroring these three lists 1:1 for the owner's own
visibility in the app - a display convenience, not something the
trading/research agents read from. See README.md's "Robinhood
watchlists" note for the mechanism and the standing rule about keeping
them in sync going forward.

## 2026-09-26 — DOGE re-added to the crypto watchlist (owner request)

Explicit owner request: "Include SOL, DOGE, and ETH." SOL and ETH were
already core `WATCHLIST` members; `DOGE` was part of the original
BTC/ETH/SOL/DOGE core carve-out until `watchlist_2026-09-23_meme_removal.md`
dropped it as part of the broader meme-coin cleanup. This is a
deliberate reversal of that one piece, not a re-litigation of the whole
meme-coin decision - the rest of that cleanup (WIF/BONK/PENGU/FLOKI/MEW/
POPCAT/SHIB/PEPE all still excluded) is untouched. `WATCHLIST` is now
15 assets (was 14): `BTC, ETH, SOL, DOGE, LIT, BCH, AERO, HBAR, DOT,
CRV, ZORA, LINK, AVAX, ASTER, XLM`. Updated the `max_concurrent_positions`
comment and README's watchlist description to match the new count.
Synced the real "Trading Agent Watchlist" Robinhood watchlist to add
`DOGE`. 215/215 tests passing (no test asserted the old 14-count).

## 2026-09-26 — Owner confirmed the deposit; concurrent-cap re-check (5 -> 10?)

Owner confirmed the large balance/position change found on the 16:31
UTC rescan was a manual transfer they made themselves - not an error,
not something to reverse. The placeholder cost basis recorded for
DOGE/SOL (current mark price at detection time, since the real
acquisition price isn't visible to this account) stands unless/until
the owner provides the actual entry price.

Owner also asked: "Increase to 10 positions if the back testing
supports it" (`RISK_LIMITS["max_concurrent_positions"]`, currently 5).
Re-ran `portfolio_backtest.py`'s concurrent-cap sweep against a larger,
fresher 12-series test bed (all 10 `STOCK_WATCHLIST` names + IBIT/ETHA
crypto-beta proxies, 378 real bar-aligned hourly bars) at current
production settings. **Result: it doesn't support the change.** Caps
5 through 12 are byte-for-byte identical (peak concurrency never
exceeds 5) - the 60% aggregate cap combined with 20%-per-position
sizing already limits real simultaneous exposure to 5, so raising the
raw count to 10 would change nothing. Checked further: even with the
aggregate cap experimentally relaxed to 90% (which does let more
positions open), a cap of 10 (reaching 8 concurrent) underperforms a
cap of 5 on both return (+6.93% vs +10.55%) and worst-case drawdown
(9.12% vs 7.85%) - the same "correlated assets concentrate risk rather
than diversify it" finding `backtest_2026-09-23.md` established,
confirmed again on fresh data. **No change made** -
`max_concurrent_positions` stays at 5. See
`backtest_2026-09-26_concurrent_cap.md` for the full sweep.

## 2026-09-26 — Daily trade cap re-check (3 -> higher?): still worse

Owner asked "will increase daily trade cap be better or worse" -
re-ran `backtest_2026-09-24_trade_cap.md`'s sweep on fresh data (the
same 12-series test bed from the concurrent-cap re-check above,
current `STOCK_WATCHLIST` with `CRDO`/`PYPL` now included). **Same
answer as two days ago: worse.** `cap=3` is again the clear full-window
peak (+8.94% vs +5.79% for cap 4 and up, which all collapse to the
same plateau) and again the *only* value positive in both independent
half-windows (+0.24%/+1.18% vs cap 4+'s -4.40% in H1 despite looking
fine in H2 alone - the exact overfitting shape this project's
split-window check exists to catch). **No change made** -
`max_trades_per_day` stays at 3. See
`backtest_2026-09-26_trade_cap_recheck.md`.
