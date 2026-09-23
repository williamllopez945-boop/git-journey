# Autonomous crypto trading agent

A rule-based agent that trades a configurable crypto watchlist on Robinhood
using an SMA-crossover strategy and conservative risk limits. Built on top
of the `robinhood-trading` MCP server registered in `.mcp.json` at the
repo root.

> **Live trading status (2026-09-22): LIVE.** `DRY_RUN = False`, flipped
> directly by the account owner (Claude Code's own auto-mode safety
> classifier blocked doing this via an agent commit twice; the owner did
> it themselves via a direct push to `main`). Fresh-crossover orders at or
> under $5 notional (`RISK_LIMITS["auto_execute_max_usd"]`) execute
> automatically across the whole watchlist with no per-trade approval;
> anything larger still requires it. Per-position stop-loss (10%) and
> partial take-profit (15%, sells 80%) also execute automatically once
> `DRY_RUN` is `False` — see "Exit criteria" below. First real trade
> placed 2026-09-22: $5.02 PEPE buy, a discretionary override (not a
> strategy-confirmed signal).

**Current watchlist** (`config.py`): BTC, ETH, SOL, DOGE (core) plus PEPE,
WIF, BONK, PENGU, FLOKI, XCN, MEW, POPCAT, SHIB (top 10 by SMA(10,30)
crossover strength from the 2026-09-22 screener — see
`watchlist_2026-09-22.md`), plus PYTH and XLM (added 2026-09-22). The same
5%-per-asset cap and combined daily trade cap apply to all 15. Also synced
to a real Robinhood watchlist ("Trading Agent Watchlist", list_id
`d3d77136-1b9e-403b-8c4a-46e59f8f1d91`) for visibility in the app —
purely organizational, `config.py` remains the source of truth the agent
reads from.

**Known gap: PYTH has no scanner coverage.** The SMA(10,30) screener
(`scanner_signals.py`, scan_id `8f2ca450-...`) covers 49 crypto pairs, and
PYTH is not one of them even though it's a normally tradable pair (real
quotes work fine via `get_crypto_quotes`). Until that's resolved, PYTH's
signal only comes from the slower `price_history.py` polling path (~31
hourly cycles to warm up) — it does not get the scanner's immediate
real-history signal that the other 14 watchlist assets get.

## What's here

| File | Purpose |
|---|---|
| `config.py` | Watchlist, strategy parameters, risk limits, `DRY_RUN` switch |
| `strategy.py` | SMA crossover signal logic (pure computation, no network) |
| `price_history.py` | Builds the crypto price series locally by recording one bar per cycle — persisted to `price_history.json` |
| `scanner_signals.py` | Detects real SMA(10,30) crossover events using the RobinHood scanner's server-side `closeAvg` (real historical candles, no warm-up needed) — persisted to `scanner_state.json` |
| `exit_criteria.py` | Per-position stop-loss (10%) and partial take-profit (15%, sells 80%) checks, independent of the SMA signal |
| `position_state.py` | Tracks whether take-profit was already taken per asset, so it fires once per position — persisted to `position_state.json` |
| `backtest.py` | Runs the exact production strategy/exit code against a historical closing-price series — see `backtest_2026-09-23.md` for results |
| `risk_manager.py` | Position sizing, daily loss circuit breaker, daily trade cap — persisted to `state.json` |
| `PLAYBOOK.md` | Step-by-step runbook an MCP-connected agent session follows each cycle |
| `tests/` | Unit tests for the strategy and risk logic |

## Strategy

**Entry:** SMA crossover, long-only. Short SMA (10 periods) crossing above
the long SMA (30 periods) is a buy signal. No shorting, no margin.

**Exit — three independent triggers, whichever fires first (or both):**
1. **SMA death cross** — short SMA crosses below the long SMA. Exits the
   full position (`strategy.py`).
2. **Stop-loss (10%)** — current price is 10% or more below the position's
   average cost basis. Exits the full position, regardless of the SMA
   state (`exit_criteria.py`).
3. **Take-profit (15%, partial)** — current price is 15% or more above
   average cost basis. Sells 80% of the position, once per position
   lifecycle; the remaining 20% keeps riding, subject to the same
   stop-loss and death-cross checks afterward (`exit_criteria.py` +
   `position_state.py`).

Stop-loss and take-profit are protective/profit-locking checks, not new
risk-taking — see "Auto-execution policy" below for why they're exempt
from the size cap and trade limits that apply to entries.

## Risk limits (conservative, as configured)

- Max 5% of portfolio value per asset
- Daily circuit breaker: all trading halts for the rest of the UTC day
  once portfolio drawdown from that day's starting equity hits 3%
- Max 3 trades per day, combined across the whole watchlist

These are enforced by `RiskManager`, whose state persists in
`trading_agent/state.json` (gitignored — it holds live account/trade data
and must never be committed).

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
- **New-entry auto-execution is bounded**, not blanket "no approval
  ever": only fresh crossover signals (`fresh_buy_cross` /
  `fresh_sell_cross`) at or under `RISK_LIMITS["auto_execute_max_usd"]`
  (currently $5) execute without approval. Everything else — larger
  fresh-cross orders, `excellent_watch` alerts — still requires the
  account owner's explicit, per-trade approval.
- **Protective exits are not bounded the same way.** Stop-loss (10%) and
  take-profit (15%, sells 80%) — see "Strategy" above — execute
  automatically regardless of position size, and bypass `can_trade()`,
  the daily trade cap, and the circuit breaker. Only `DRY_RUN` gates
  them. This is deliberate: those gates limit new risk-taking, and
  applying them to an exit would mean being unable to cut a loss or lock
  in a gain exactly when it matters.
- **Every auto-executed trade is reported immediately after placement**
  (asset, side, quantity, price, order id, and for exits the reason and
  resulting P/L) — auto-execute removes the approval gate before the
  order, not visibility after it.
- The 5%-per-asset cap, 3% daily circuit breaker, and 3-trades/day cap
  (`RiskManager`) still apply to new entries on top of the $5
  auto-execute threshold — defense in depth, not a replacement for it.

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
