# Autonomous crypto + stock trading agent

A rule-based agent that trades a configurable crypto watchlist AND a
configurable stock watchlist on Robinhood using the same SMA-crossover
strategy and one shared set of risk limits. Built on top of the
`robinhood-trading` MCP server registered in `.mcp.json` at the repo root.
Crypto-only through 2026-09-22; extended to equities 2026-09-23 (see
"Stock watchlist" below).

> **Live trading status (2026-09-22): LIVE.** `DRY_RUN = False`, flipped
> directly by the account owner (Claude Code's own auto-mode safety
> classifier blocked doing this via an agent commit twice; the owner did
> it themselves via a direct push to `main`). `RISK_LIMITS["auto_execute_max_usd"]`
> is $100 (raised from $5 on 2026-09-23), `max_position_pct` is 20% (5% →
> 50% → 15% → 20% the same day, across three re-backtested passes — see
> "Risk limits" and "Concurrent-positions cap" below), and
> `max_aggregate_position_pct` is a new **hard cap at 50% of portfolio
> value across every open position combined** — the owner's explicit
> "never use over 50% of capital" constraint, enforced independently of
> the other two limits (which don't reliably compose into one on their
> own: 20% × 5 concurrent = 100%, well over 50% if unchecked). Since $100
> is well above what a 20%-sized position at this portfolio's size ever
> reaches, **the $100 threshold no longer meaningfully gates anything** —
> a properly-sized, strategy-confirmed entry now auto-executes with no
> per-trade approval essentially always, not just "at or under" some
> binding threshold. Per-position stop-loss (10%) and partial take-profit
> (15%, sells 70%) also execute automatically once `DRY_RUN` is `False`
> — see "Exit criteria" below. First real trade placed 2026-09-22: $5.02
> PEPE buy, a discretionary override (not a strategy-confirmed signal). A
> confirmed buy cross on the scanner path is also gated on real crypto
> volume (2026-09-23) — see "Volume
> confirmation" below.

**Current crypto watchlist** (`config.py`'s `WATCHLIST`): BTC, ETH, SOL
(core) plus LIT, BCH, XCN, HBAR, DOT, CRV, ZORA, LINK, AVAX, ASTER (top 10
by SMA(10,30) crossover strength among blue-chip/established crypto,
2026-09-23 — see `watchlist_2026-09-23_meme_removal.md`), plus PYTH and
XLM (added 2026-09-22). Also synced to a real Robinhood watchlist ("Trading
Agent Watchlist", list_id `d3d77136-1b9e-403b-8c4a-46e59f8f1d91`) for
visibility in the app — purely organizational, `config.py` remains the
source of truth the agent reads from.

**Meme-coin removal (2026-09-23):** the owner asked to "get out of meme
coins and into [assets] that has a future," clarified as blue-chip crypto
rather than literal stablecoins (a stablecoin barely moves, so a
momentum strategy has nothing to trade). DOGE and the entire 2026-09-22
meme-coin screener cluster (PEPE, WIF, BONK, PENGU, FLOKI, MEW, POPCAT,
SHIB) were removed and replaced with a fresh top-10 screener run against
the 49-pair universe with meme/joke/political coins and USDC excluded
first — same evidence-based, screener-driven methodology as every other
watchlist change this session, not hand-picked. No sell orders were
needed — the account held zero open crypto positions at the time. Full
exclusion list and ranking in `watchlist_2026-09-23_meme_removal.md`.

## Stock watchlist (2026-09-23)

`config.py`'s `STOCK_WATCHLIST`: **CRWD, PANW, TWLO, ILMN, IR, PTC, CHKP,
MAIR, AR, HUBS** — top 10 by SMA(10,30) 1h crossover strength among
**large-cap** stocks (market cap > $10B, price > $10, 30d avg volume >
1M shares), same screener methodology used for every watchlist this
session. Scanned via the same saved scan, `Stock SMA(10,30) 1h Crossover
— Strategy Screener`, scan_id `6e009dcf-d184-45a7-915f-ccfc50b4e6be`
(market-cap filter updated in place, so future re-screens inherit the
$10B floor automatically).

**History of this list, most recent first:**
- **2026-09-23 (large-cap upgrade):** owner asked to replace the mid-cap
  names with larger ones ("Let's look at replacing the small cap stocks
  with larger ones. With more confidence, I will add more capital").
  Raised the screener's market-cap floor from $2B to $10B and re-ran it
  — full replacement, not hand-picked. Validated with a real-data
  backtest first: the new list's combined portfolio (with crypto
  proxies, shared budget) scored **+9.43% return / 4.94% max drawdown**
  over the same ~90-day window the mid-cap list scored **-7.64% /
  11.18%** on. Full ranking, backtest, and an important honest caveat —
  HUBS gapped **-20.01% overnight** on 2026-08-06 (bigger than the
  MDLN gap that motivated dropping the biotechs, though an ordinary
  earnings reaction, not a special single-catalyst risk like TNGX/ARQT's
  — see the doc for why it wasn't excluded on that basis) — in
  `watchlist_stocks_2026-09-23_large_cap.md`.
- **TNGX and ARQT dropped:** a real-data backtest (`backtest_2026-09-23.md`)
  found a genuine -15.2% overnight gap in MDLN on 2026-08-05 — past the
  10% stop-loss in a single move, which an hourly check can't react to
  until after the fact. TNGX and ARQT were both clinical-stage biotechs
  carrying real binary trial/FDA catalyst risk, categorically worse than
  MDLN's ordinary-volatility gap. Owner's call: "Drop the two. We only
  pick winners here." No sell orders needed.
- **Original list (2026-09-22 methodology, $2B floor):** GLBE, VVV,
  TRLV, ESI, CE, BHF, MDLN, OLLI, plus TNGX/ARQT before they were
  dropped — see `watchlist_stocks_2026-09-23.md` for that original
  ranking and why the liquidity filters were needed (the unfiltered
  STOCK universe is dominated by illiquid micro-caps whose SMA
  crossovers are noise, not momentum).

No sell orders were needed for the large-cap switch either — zero open
equity positions at the time.

**Shared risk budget (owner's explicit choice, not separate per asset
class):** `RISK_LIMITS` — `max_position_pct`, `max_aggregate_position_pct`,
`max_concurrent_positions`, `max_trades_per_day` — is one set of numbers
spanning `WATCHLIST` and `STOCK_WATCHLIST` together. A stock trade and a
crypto trade draw from the same daily-trade-cap counter; an open stock
position counts toward the same concurrent-positions cap and the same 50%
aggregate-value ceiling a crypto position would. See `PLAYBOOK.md`'s
"Scanner-based cycle — stocks" section for exactly how the shared counters
are computed each cycle.

**Market hours (stocks only, v1 scope):** unlike crypto (24/7), the stock
scanner cycle only evaluates and acts during regular market hours
(9:30-16:00 ET, Mon-Fri) — outside that window a stock signal simply isn't
acted on until the next in-hours cycle. Orders use marketable limit orders
(not plain market orders) for explicit price protection. Extended-hours
trading is not implemented in v1.

**No cost-basis fallback needed for stocks (so far):** `get_equity_positions`
returns `average_cost` directly per position; the crypto-side
`cost_bases`-returns-zero gap (see "Known gap: cost basis" below) has not
been observed on the equity side, so `cost_basis_fallback.py` is not wired
into the stock exit-rules path.

**Known gap: cost basis can come back zero on a real position.**
`get_crypto_positions`' `cost_bases` field reported `direct_quantity: 0` /
`direct_cost_basis: 0` for the PEPE position bought 2026-09-22, still 0 a
full day later — despite the underlying order being a completely normal
single fill (1,014,198 units at `effective_price` $0.00000494, agentic
market buy, no transfer/reward/fork involved). This looks like a gap in
Robinhood's own cost-basis ledger, not anything in this codebase, and not
covered by `get_crypto_positions`' own "average only covers a subset of
units" caveat (there's no un-costed transfer here — the entire position
came from one traceable order). Since `exit_criteria.check_exit()` treats
a zero-or-less cost basis as inert, an unresolved zero would silently
disable stop-loss/take-profit protection on that position. `PLAYBOOK.md`'s
"Per-position exit rules" step 1 now falls back to
`cost_basis_fallback.average_cost_basis_from_trade_log` (computed from
`RiskManager`'s own locally recorded trade log) whenever this happens.
**A related bug in that fallback itself was found and fixed live
2026-09-23:** `RiskManager`'s day-rollover logic used to discard the
*entire* `trade_log` on any UTC date mismatch, not just the day-scoped
`trades_today`/`starting_equity`/`halted` fields - so a position bought
one day and exited the next (PEPE's actual death-cross exit that day)
found its own fallback cost basis unrecoverable, since the buy that
established it had aged into "yesterday." Fixed: `trade_log` now
survives the rollover; only the truly daily-scoped fields reset.

**Known gap: PYTH has no scanner coverage.** The SMA(10,30) screener
(`scanner_signals.py`, scan_id `8f2ca450-...`) covers 49 crypto pairs, and
PYTH is not one of them even though it's a normally tradable pair (real
quotes work fine via `get_crypto_quotes`). Until that's resolved, PYTH's
signal only comes from the slower `price_history.py` polling path (~31
hourly cycles to warm up) — it does not get the scanner's immediate
real-history signal that the other 14 watchlist assets get, and (since
2026-09-23) it also never gets the volume confirmation gate below, which
is scanner-only — `get_crypto_quotes` has no volume field.

## What's here

| File | Purpose |
|---|---|
| `config.py` | Crypto watchlist (`WATCHLIST`) and stock watchlist (`STOCK_WATCHLIST`, added 2026-09-23), strategy parameters, one shared `RISK_LIMITS`, `DRY_RUN` switch |
| `strategy.py` | Raw SMA crossover signal logic (pure computation, no network) |
| `entry_filter.py` | Wraps `strategy.py` with an entry confirmation filter (1-bar persistence + minimum crossover strength) - cuts whipsaw losses, see `backtest_2026-09-23.md` |
| `price_history.py` | Builds the crypto price series locally by recording one bar per cycle — persisted to `price_history.json` |
| `scanner_signals.py` | Detects real SMA(10,30) crossover events using the RobinHood scanner's server-side `closeAvg` (real historical candles, no warm-up needed); gates a confirmed buy cross on real `Relative volume` from the same scan — persisted to `scanner_state.json`. Asset-agnostic (keyed by symbol string) — used for both the crypto scan (scan_id `8f2ca450-...`) and the stock scan (scan_id `6e009dcf-...`, added 2026-09-23) |
| `volume_filter.py` | Volume entry confirmation filter — blocks a fresh buy on unconvincing, low-volume breakouts — see `backtest_2026-09-23.md`'s "Volume entry confirmation filter" section |
| `cost_basis_fallback.py` | Computes average cost basis from the local trade log, as a fallback for when `get_crypto_positions` reports a zero cost basis on a real held position (see "Known gap: cost basis" below) |
| `exit_criteria.py` | Per-position stop-loss (10%) and partial take-profit (15%, sells 70%) checks, independent of the SMA signal |
| `position_state.py` | Tracks take-profit state (fires once per position) and the post-exit whipsaw cooldown (4h, blocks re-entry) — persisted to `position_state.json` |
| `backtest.py` | Runs the exact production strategy/exit code against a historical closing-price series — see `backtest_2026-09-23.md` for results |
| `risk_manager.py` | Position sizing (flat or volatility-scaled, plus a hard aggregate cap across all open positions), daily loss circuit breaker, daily trade cap, concurrent-positions cap — persisted to `state.json` |
| `volatility_sizing.py` | Scales the position-size cap down for higher-volatility assets relative to a benchmark (BTC) — see `volatility_sizing_2026-09-23.md` |
| `portfolio_backtest.py` | Multi-asset backtest sharing one cash pool across several price series at once — validates the concurrent-positions cap, which `backtest.py`'s single-asset simulator can't test — see `backtest_2026-09-23.md` |
| `rsi_filter.py` | RSI entry confirmation filter — built and backtested but **not** wired into live entries (see `backtest_2026-09-23.md`'s "RSI entry confirmation filter" section: it hurt worst-case robustness in every setting that meaningfully engaged) |
| `cycle_log.py` | Append-only log of every non-hold signal/gate event each cycle (executed, recommended, blocked-by-X, excellent_watch, protective exit) — feeds `daily_review.py`, persisted to `cycle_log.json` |
| `daily_review.py` | Assembles the end-of-day after-action review from `cycle_log.py` + `RiskManager`'s trade log, including a chronological executive summary of every buy/sell/hold decision and why — see "Daily after-action review" below |
| `PLAYBOOK.md` | Step-by-step runbook an MCP-connected agent session follows each cycle |
| `tests/` | Unit tests for the strategy and risk logic |

## Strategy

**Entry:** SMA crossover, long-only, no shorting/margin. Short SMA (10
periods) crossing above the long SMA (30 periods) is a buy signal — but
it must be *confirmed*: `entry_filter.py` requires the cross to still
hold one cycle later before treating it as tradeable (no additional
strength requirement by default — see below).

**Whipsaw cooldown:** even with the entry filter, a stopped-out or
death-crossed position can't immediately re-enter — `position_state.py`
blocks new entries into that asset for 4 hours after a full exit. Only
blocks new entries — exits (sells, stop-loss, take-profit) are never
delayed by it.

**Volume confirmation (scanner path only):** a confirmed buy cross is
additionally blocked when the asset's `Relative volume`
(`volume(1h,1) / volumeAvg(14,1h)`, added to the production scan
2026-09-23) is below `volume_filter.DEFAULT_VOLUME_MIN_RATIO` (0.4) - an
unconvincing, low-volume breakout. Real crypto data from the scanner, not
an equity proxy. Backtested against equity/ETF proxy volume (real crypto
volume has no historicals source, same limitation as price):
`backtest_2026-09-23.md`'s "Volume entry confirmation filter" section
found this conservative threshold never hurt in any of 9 clean real
series and modestly helped on 2 of them (IBIT, ETHA) - thinner evidence
than the other tunings on this page, since only those two series showed
real engagement, but smooth and non-negative across every neighboring
threshold and period tested. Never blocks a sell cross, and unavailable
on the polling path (`price_history.py`/`get_crypto_quotes` have no
volume field) - PYTH-only entries never get this gate.

**Tuning history, briefly (see `backtest_2026-09-23.md` for the full
story):** an initial sweep against only IBIT/ETHA's one 6-month trending
window suggested a 0.25% strength requirement and a 12h cooldown, and
looked like a big win there. Testing that tuning against a much broader
sample — GBTC's real 2018-2026 history across 6 market regimes, plus 3
Solana ETFs — showed it helped only 5 of 11 series and hurt the other 6,
including some large losses. Re-tuned against the full 11-series set: 0%
strength (persistence alone) + 4h cooldown is the current default,
helping 6/11 series with a far safer worst case. Treat these as a
reasonable, moderately-validated starting point, not a proven edge —
this strategy family (SMA crossover) trails buy-and-hold in strong
trends and only clearly earns its keep in choppy or falling markets,
which is inherent to the approach, not something tuning fixes.

**Exit — three independent triggers, whichever fires first (or both):**
1. **SMA death cross** — short SMA crosses below the long SMA. Exits the
   full position (`strategy.py`).
2. **Stop-loss (10%)** — current price is 10% or more below the position's
   average cost basis. Exits the full position, regardless of the SMA
   state (`exit_criteria.py`).
3. **Take-profit (15%, partial)** — current price is 15% or more above
   average cost basis. Sells 70% of the position, once per position
   lifecycle; the remaining 30% keeps riding, subject to the same
   stop-loss and death-cross checks afterward (`exit_criteria.py` +
   `position_state.py`).

Stop-loss and take-profit are protective/profit-locking checks, not new
risk-taking — see "Auto-execution policy" below for why they're exempt
from the size cap and trade limits that apply to entries.

## Risk limits (as configured)

- Max 20% of portfolio value per asset. 5% → 50% → 15% → 20% on
  2026-09-23, across three re-backtested passes the same day - see
  "Concurrent-positions cap" below and `backtest_2026-09-23.md`. This is
  no longer the primary backstop against overconcentration; the
  aggregate cap below is.
- **Max 50% of portfolio value across ALL open positions combined**
  (`max_aggregate_position_pct`, new 2026-09-23) - a hard, independently
  enforced ceiling, added because the per-asset cap and the
  concurrent-positions cap don't reliably compose into one on their own
  (20% × 5 concurrent = 100%, well over 50% if unchecked). Uses current
  mark-to-market value, so already-open positions appreciating can't
  quietly push total exposure past 50% either. Only ever limits or
  zeroes a *fresh entry's* size - never forces an exit on positions
  already open, even if they've since appreciated past the ceiling on
  their own.
- Daily circuit breaker: all trading halts for the rest of the UTC day
  once portfolio drawdown from that day's starting equity hits 3%
- Max 3 trades per day, combined across the whole watchlist
- Max 5 concurrent open positions across the whole watchlist (of 15
  assets) — see "Concurrent-positions cap" below

These are enforced by `RiskManager`, whose state persists in
`trading_agent/state.json` (gitignored — it holds live account/trade data
and must never be committed).

## Position sizing: flat cap, or volatility-scaled

The 20% cap above is a ceiling, not always the actual size used.
`volatility_sizing.py` can scale it down (never up) for assets more
volatile than BTC (the benchmark) — e.g. an asset twice as volatile as
BTC gets sized at 10% instead of 20%. Validated against real market data
(`volatility_sizing_2026-09-23.md`, back when the flat cap was still 5%):
on real hourly bars, ETH measured ~27% more volatile than BTC and scaled
to ~79% of the flat cap — a sensible, real differentiation; the
*proportional* scaling behavior is unaffected by the flat cap's own
value, only the resulting dollar/percentage figures move with it.

**Scope, stated plainly:** this only sizes an individual position by its
own volatility. It does not account for correlation across several
simultaneously-held positions (e.g. multiple meme coins moving together)
— the concurrent-positions cap below is a partial mitigation for that
(fewer correlated positions open at once), not a full multi-asset
portfolio backtester. Also only available on the polling path
(`price_history.py` accumulates the raw closes volatility needs); the
faster scanner path only has point-in-time SMA values, not a series, so
it always sizes at the flat cap.

## Concurrent-positions cap

`RISK_LIMITS["max_concurrent_positions"]` (5, out of the 15-asset
watchlist) caps how many assets may have an open position at the same
time — a fresh buy signal into a previously-flat asset is skipped, same
as the whipsaw cooldown, while 5 are already open; it never blocks a
sell/exit or a signal for an asset already held. Enforced by
`RiskManager.can_open_new_position(open_position_count)`.

Validated with `portfolio_backtest.py` — a multi-asset simulator that
runs the same production entry/exit rules across several price series at
once, sharing one cash pool, since the single-asset `backtest.py` has no
notion of "how many are open simultaneously." Swept against two real,
bar-aligned correlated groups (backtest_2026-09-23.md's
"Concurrent-positions cap" section): IBIT/ETHA (hourly) and
GBTC+VSOL+BSOL+GSOL (daily, 4-way aligned). Lower caps consistently
reduced max drawdown in both groups, and in the more-correlated 4-asset
group even improved total return — correlated assets tend to fire
near-duplicate signals, so holding many at once concentrates risk and
multiplies whipsaw losses rather than diversifying.

**Scope, stated plainly:** the sweep only ever tested 2 or 4 correlated
series (no larger real, bar-aligned correlated group exists to test
against), so it validates the *mechanism* (capping helps), not a proven
optimal number for a 15-asset watchlist with several distinct clusters
(core BTC/ETH/SOL/DOGE, the meme-coin group, PYTH/XLM). 5 is a
moderate, owner-chosen extension of that direction, not a backtested
optimum the way the exit-criteria and SMA-window defaults are.

**Re-checked 2026-09-23 (same day, later)** after `max_position_pct` was
briefly raised to 50%: at that sizing, cash ran out after just 2
positions in both test groups regardless of the cap value (2, 3, 4, and
uncapped all produced identical results) - `max_concurrent_positions=5`
had become vestigial, and worst-case drawdown on the 4-asset group jumped
6x (6.30% → 36.76%) versus the same test at 5% sizing. The owner chose
to bring `max_position_pct` back down (to 15%, not 5%) rather than
restrict concurrency to 1 asset, restoring genuine multi-position
diversification: at 15%, all 4 assets in the test group can still be
held simultaneously, with worst-case drawdown around 18% - well below
50%'s 36.76%, though still above the original 5%'s 6.30%, since drawdown
scales roughly linearly with `max_position_pct` once diversification is
preserved (verified by sweeping 5-25% - see `backtest_2026-09-23.md`'s
"Concurrent-positions cap re-check after the sizing change" section).

**Re-optimized again 2026-09-23 (same day, a third pass)** once
`max_aggregate_position_pct` (above) existed as a real, hard 50% ceiling
on total exposure: with that backstop in place independent of
`max_position_pct`, swept the per-asset cap for return rather than
drawdown and found 20% gave the best or near-best return in *both* real
test groups while still preserving full diversification - see
`backtest_2026-09-23.md`'s "Optimizing within the 50% aggregate cap"
section. `max_position_pct` set to 20%; the underlying entry/exit signal
logic (SMA windows, entry filter, cooldown, exit criteria) was
deliberately *not* re-tuned chasing higher backtested returns in this
pass - see that section for why.

## Crypto price history: built by polling, not fetched

Verified against a live, authenticated `RobinHood` MCP connector: it has
no crypto-pair historicals tool (only equity/index/option historicals).
Since there's no historicals API to call, `trading_agent/price_history.py`
builds the series itself: each scheduled cycle records the current mark
price (from `get_crypto_quotes`) as one bar via `PriceHistoryStore`,
persisted to `trading_agent/price_history.json` (gitignored — it's
runtime-accumulated market data, not source). `sma_crossover_signal`
correctly returns `"hold"` until at least `long_window + 1` cycles have
recorded a bar — expect holds for the first ~30 cycles after a fresh
start (30 hours, at an hourly schedule) before the strategy has enough
history to generate a real buy/sell signal.

## Scanner-based signal detection (faster than the polling warm-up)

`price_history.py`'s polling approach needs ~31 hourly cycles before it has
enough locally-recorded bars to compute a signal. `scanner_signals.py`
gets a real signal immediately by reading the RobinHood scanner's
`closeAvg` columns (server-side SMA over actual historical candles — see
the scanner discovery in `watchlist_2026-09-22.md`) each cycle, and
comparing this cycle's bullish/bearish state per asset to the last
persisted one to detect an actual crossover *event*, not just a state.

Each cycle's `classify()` call returns one of:
- `fresh_buy_cross` / `fresh_sell_cross` — SMA10 crossed SMA30 since the
  last cycle. This is a genuine strategy signal. If the order notional is
  at/under `auto_execute_max_usd` and `DRY_RUN` is `False`, it executes
  automatically (see the live-trading banner above) and is reported after
  the fact; otherwise it's surfaced as a recommendation awaiting approval.
- `excellent_watch` — no fresh cross, but `|crossover_pct|` or
  `|% change|` clears a "worth a look" threshold (5% either way). Flagged
  for discussion, explicitly not a strategy-confirmed recommendation, and
  never auto-executed regardless of size.
- `hold` — nothing notable, or this is the first observation for that
  asset (no prior state to compare against).

## Auto-execution policy (live, DRY_RUN=False)

- **The `robinhood-trading` MCP server** (in `.mcp.json`) is still
  unauthenticated — it needs an OAuth/login step tied to the account
  owner's identity that no agent can do on their behalf. Actual trading
  currently happens through a separate, already-authenticated `RobinHood`
  connector available in agent sessions on this account.
- **New-entry auto-execution is gated by signal type, not blanket "no
  approval ever":** only fresh crossover signals (`fresh_buy_cross` /
  `fresh_sell_cross`) at or under `RISK_LIMITS["auto_execute_max_usd"]`
  (currently $100 - raised from $5 on 2026-09-23) execute without
  approval; `excellent_watch` alerts still always require it, regardless
  of size. **The threshold no longer meaningfully gates anything:** it
  was raised to $100 to match `max_position_pct`'s 50% cap that same day,
  but `max_position_pct` was subsequently brought down to 20% across two
  more passes (see "Risk limits" above) while `auto_execute_max_usd` was
  left at $100 - since a 20%-sized position at this portfolio's value
  never reaches anywhere close to $100, essentially every properly-sized
  confirmed entry now auto-executes unconditionally, not "at or under" a
  real binding threshold. Revisit `auto_execute_max_usd` if the approval
  gate is meant to matter again - it was left alone deliberately, not
  by oversight (see `CHANGELOG.md`). Reconfirmed still true in the
  2026-09-24 audit - `config.py` now carries a NOTE on this setting
  directly, not just here.
- **Protective exits are not bounded the same way.** Stop-loss (10%) and
  take-profit (15%, sells 70%) — see "Strategy" above — execute
  automatically regardless of position size, and bypass `can_trade()`,
  the daily trade cap, and the circuit breaker. Only `DRY_RUN` gates
  them. This is deliberate: those gates limit new risk-taking, and
  applying them to an exit would mean being unable to cut a loss or lock
  in a gain exactly when it matters.
- **Every auto-executed trade is reported immediately after placement**
  (asset, side, quantity, price, order id, and for exits the reason and
  resulting P/L) — auto-execute removes the approval gate before the
  order, not visibility after it.
- The 20%-per-asset cap, 50% aggregate cap, 3% daily circuit breaker, and
  3-trades/day cap (`RiskManager`) still apply to new entries on top of
  the $100 auto-execute threshold — defense in depth, not a replacement
  for it. Since the $100 threshold no longer binds at this position size
  (see above), it's the 50% aggregate cap in particular - a hard,
  independently enforced ceiling - doing the real risk-limiting on new
  entries now, alongside the 3-trades/day cap, the 3% circuit breaker,
  and the concurrent-positions cap, not the approval gate.

## Automated cycles (2026-09-23)

Two persistent Routines (`Claude_Code_Remote` triggers, not the earlier
session-scoped `CronCreate` jobs — those die silently when a session
recycles, confirmed ~6 times earlier this session) now run this agent
hands-off:

- **Hourly trading cycle** — runs `PLAYBOOK.md` in full, including
  bounded auto-execution (fresh, strategy-confirmed signals at/under
  `auto_execute_max_usd` execute with no approval step; protective exits
  always execute; everything else alerts or waits for approval). Also
  calls `CycleLogStore().record(...)` (see `cycle_log.py`) for every
  non-hold event, so the daily review below has real data to work from.
  **Stays hourly, not every 30 minutes** (considered 2026-09-23):
  persistent Routines enforce a hard 1-hour minimum interval, and the
  strategy's SMA(10,30) is itself computed on 1-hour candles regardless
  of check frequency - a 30-minute cadence would only cut alert latency,
  not improve signal quality, so it wasn't worth trading the Routine's
  reliability for a session-scoped `CronCreate` supplement (the same
  mechanism that died silently ~6 times earlier this session).
- **Daily after-action review** — fires at **20:05 UTC** (changed
  2026-09-23, owner request: "right at the end of the trading time,"
  owner is in Texas/Central time) — 4:05pm ET / 3:05pm CT, just after
  the stock market's 4:00pm ET close. This cron is a fixed UTC time, not
  DST-aware — it'll need bumping by an hour when the US clocks change
  (~Nov 1 and ~Mar 8) to keep landing at market close local time.
  **Known trade-off:** the review's date filtering is UTC-midnight-based
  and crypto trades 24/7, so firing mid-UTC-day (rather than the
  original 23:50 UTC, close to the day boundary) means crypto activity
  in the ~4 hours after 20:05 UTC is logged under that same UTC date but
  never reviewed — tomorrow's run only looks at tomorrow's date. A real,
  permanent gap for late-day crypto, not just a delayed report; the
  routine's prompt flags this explicitly so a recurring late-day trade
  or exit gets surfaced as an observation rather than silently missed.
  Reads the day's
  `cycle_log.json` entries and `RiskManager`'s trade log through
  `daily_review.summarize_day`/`format_markdown_report`, writes the
  result to `trading_agent/daily_logs/YYYY-MM-DD.md`, commits and pushes
  it, and sends a push notification with the headline. The mechanical
  counts (trades, P/L, blocked-signal counts by gate) come from real
  recorded data; the qualitative "anything to improve" read is added on
  top by whichever session runs the review, the same way every backtest
  write-up in `backtest_2026-09-23.md` pairs real numbers with judgment.
  **Executive summary (2026-09-23, owner request):** the report now
  opens with a chronological, plain-language account of every decision
  the strategy made that day and why - built by
  `daily_review.format_executive_summary` entirely from `cycle_log.json`
  (what was considered: the classification/crossover_pct the scanner
  actually saw, set against the decision: executed/recommended/blocked-
  by-a-specific-gate/excellent_watch/protective_exit), not written or
  interpreted freehand. Passing `watchlist=config.WATCHLIST +
  config.STOCK_WATCHLIST` into `format_markdown_report` also names every
  asset that had zero events that day, since a plain "hold" is
  deliberately never logged per-cycle (see `cycle_log.py`) - without the
  watchlist argument, a quiet asset simply isn't mentioned rather than
  being explicitly called out as held.

`daily_logs/*.md` is intentionally **not** gitignored — unlike
`state.json`/`cycle_log.json`/etc. (live runtime data, never committed),
the daily review is meant to be a durable, versioned record.

## Adjusting or disabling live trading (the owner's own direct action)

`DRY_RUN` was flipped to `False` by the account owner directly — Claude
Code's own auto-mode safety classifier blocked doing this via an agent
commit (twice), so the owner pushed the change to `main` themselves and
had it pulled into this branch. The same applies to any further change:

- To adjust the auto-execute threshold or scope, edit
  `RISK_LIMITS["auto_execute_max_usd"]` directly — `0` disables new-entry
  auto-execution while leaving recommendations active (protective exits
  are unaffected by this value).
- To adjust the stop-loss/take-profit levels or the take-profit sell
  fraction, edit the constants at the top of `exit_criteria.py`.
- To stop all trading entirely (including protective exits), set
  `DRY_RUN = True`.
- Optionally connect and authenticate the `robinhood-trading` MCP server
  in an agent environment you control, if you want trading to route
  through it instead of the currently-connected `RobinHood` connector.

## Risk disclosure

This trades real money. Orders at/under the auto-execute threshold place
with no human approval per trade; larger orders still require it.
Stop-loss and take-profit exits place with no approval and no size cap.
Crypto markets are volatile; the risk limits
here reduce but do not eliminate the chance of losses, and a bug in the
strategy or a stale/incorrect price feed can still lose money within
those limits (up to the daily loss cap, or up to the auto-execute
threshold per untraced signal) before the circuit breaker halts trading.
Review the code yourself before enabling live trading or raising any of
these limits.
