# Trading cycle playbook

This is the runbook an agent session must follow on each trading cycle. It
requires the `robinhood-trading` MCP server (configured in `.mcp.json`) to
be connected and authenticated with a live Robinhood account — that
connection has to be established by the account owner, it cannot be done
by an agent on their behalf.

Run this cycle on a fixed schedule (e.g. hourly). Each run is one full pass
over the watchlist.

**Simplified 2026-09-24 (audit):** steps 1-6 below (the local-polling
signal path) were narrowed to **`PYTH` only** — it was the one
`WATCHLIST` asset the crypto scanner didn't cover, so it was the only
asset that actually needed a locally-built price series. Every other
asset gets real signals from the scanner-based cycle below from the
first cycle it's on the watchlist, with no warm-up.

**`PYTH` itself was then removed from `WATCHLIST` the same day** (no
documented reason for its inclusion survived, and it was structurally
the worst-served asset - see `CHANGELOG.md`). **Steps 1-6 below currently
apply to zero assets** as a result - every current `WATCHLIST` member is
scanner-covered. Left in place rather than deleted: the mechanism
(`price_history.py`, `entry_filter.confirmed_signal`, volatility-scaled
sizing) is real, tested infrastructure that would matter again the
moment a non-scanner-covered asset is added - ripping it out now would
just mean rebuilding it later. Skip steps 1-6 entirely while `WATCHLIST`
has no such asset; re-activate them (scoped to whichever asset needs it,
not the whole watchlist) if one is ever added.

## Steps, per cycle

1. **Load config.** Read `WATCHLIST`, `STRATEGY`, `RISK_LIMITS`, and
   `DRY_RUN` from `trading_agent/config.py`.

2. **Fetch account state.** Call the `robinhood-trading` MCP tools to get:
   - total portfolio equity (cash + holdings value) - `get_portfolio`,
     account_number `581911765` (the "Agentic" account).
   - current positions and their market value, for each asset in
     `WATCHLIST` (`get_crypto_positions`, `rhs_account_number` `581911765`)
     AND each asset in `STOCK_WATCHLIST` (`get_equity_positions`,
     `account_number` `581911765` - same numeric account, different
     parameter name per tool).
   - `open_position_count`: **shared across both lists** (owner's explicit
     shared-budget choice, see config.py) - the number of `WATCHLIST`
     assets with `quantity_transferable > 0` from `get_crypto_positions`
     PLUS the number of `STOCK_WATCHLIST` assets with `quantity > 0` from
     `get_equity_positions`, as one combined count. Recompute once per
     cycle from the fetched positions, then keep it updated in-memory as
     positions open/close during the cycle (see step 5d and the stock
     scanner cycle below) - a crypto entry and a stock entry in the same
     cycle both increment the same counter.
   - `total_open_position_value`: **shared across both lists**, same
     reasoning - sum of current mark-to-market value (quantity × mark
     price, `get_crypto_quotes` for crypto positions and
     `get_equity_quotes` for stock positions) across every open position
     in `WATCHLIST` and `STOCK_WATCHLIST` combined. Recompute once per
     cycle, then keep it updated in-memory as positions open/close/
     partially exit during the cycle on either asset class. Feeds
     `RiskManager.position_size`'s aggregate cap (step 5d), which is one
     60% ceiling over crypto and stock exposure together (100% for an
     "awesome trade" — see the Hard rules section), not two separate
     ceilings.

3. **Initialize risk state for the day.** Construct a `RiskManager` from
   `trading_agent/risk_manager.py` with `RISK_LIMITS`. Call
   `start_of_day(equity)` with the portfolio equity from step 2 (no-op if
   already recorded today). Call `check_circuit_breaker(equity)` — if it
   returns `True`, stop here for the rest of the cycle: skip all new-signal
   evaluation and do not place any new-entry orders. **This does NOT skip
   "Per-position exit rules" (stop-loss/take-profit)** — those still run
   for every open position this cycle regardless (see the Hard rules
   section: protective exits bypass the circuit breaker by design). Log
   that trading is halted for the day and why. (2026-09-28 audit: the
   live hourly Routine's own scheduled prompt previously said a halt
   means "no crypto or stock evaluation" with no carve-out, contradicting
   this section's Hard Rule below — a real cycle skipped the stop-loss
   check while halted as a result, luck rather than correctness kept the
   position safe. Routine prompt corrected the same day; this note stays
   as a reminder of why the carve-out above is explicit.)

4. **Check the daily trade cap.** Call `can_trade()`. If `False` (cap
   already hit, or the circuit breaker just tripped), stop — do not place
   any orders this cycle.

5. **For any `WATCHLIST` asset not covered by the crypto scanner** (see the
   note above steps 1-6 - currently none; skip this whole step until one
   exists):
   a. Fetch the current mark price via `get_crypto_quotes`, then record it
      as this cycle's bar:
      `PriceHistoryStore().record(asset, mark_price, cycle_timestamp)`
      from `trading_agent/price_history.py`. `cycle_timestamp` must be the
      same value for every asset in this cycle (e.g. the cycle's start
      time) — that's what lets a re-run of the same cycle dedupe instead
      of double-recording a bar. This is a polling-built history, not a
      historicals API: the connected MCP server exposes no crypto
      historicals tool (only equity/index/option), so one bar accumulates
      per cycle. SMA windows in `config.py` are in units of cycles (e.g.
      with an hourly schedule, `short_window=10` means 10 hours).
   b. Read the accumulated series with `get_closes(asset)` and compute the
      signal with
      `confirmed_signal(prices, STRATEGY["short_window"], STRATEGY["long_window"])`
      from `trading_agent/entry_filter.py` (not the raw
      `strategy.sma_crossover_signal` - `confirmed_signal` wraps it with
      the empirically-tuned 1-bar persistence + strength filter that cut
      whipsaw losses in backtest_2026-09-23.md). This returns `"hold"`
      until at least `long_window + 2` cycles have run (one extra cycle
      beyond the raw signal's warm-up, for the confirmation bar) - that's
      expected while history is still accumulating, not an error.
   c. If the signal is `"hold"`, skip this asset.
   d. If `"buy"`: check `PositionStateStore().in_cooldown(asset)` from
      `trading_agent/position_state.py` first — if `True` (this asset
      fully closed a position within the last `DEFAULT_COOLDOWN_HOURS`,
      4h by default), skip this asset entirely this cycle, even though a
      real confirmed buy signal fired. This is the whipsaw cooldown
      (empirically tuned — see backtest_2026-09-23.md), not optional.
      Next, check `RiskManager.can_open_new_position(open_position_count)`
      — if `False` (`RISK_LIMITS["max_concurrent_positions"]`, 5 by
      default, already reached), skip this asset entirely this cycle too,
      the same way the cooldown does — a real confirmed buy signal is
      still not acted on. This only applies to assets not already held;
      never skip a sell or a protective exit because of it, and never
      count an asset already being sold this cycle toward the cap. See
      backtest_2026-09-23.md's concurrent-positions sweep for why: this
      watchlist has correlated clusters (the meme-coin group especially)
      that tend to fire near-duplicate signals, so holding many at once
      concentrates correlated risk and multiplies whipsaw losses rather
      than diversifying. If the order executes below (step g),
      **increment `open_position_count`** so later assets in this same
      cycle see the updated count; if a sell/exit fully closes a position
      earlier in this cycle, decrement it the same way. Otherwise,
      compute a volatility-scaled cap before sizing the order:
      call `volatility_sizing.realized_volatility(get_closes(asset))` and
      the same for `get_closes("BTC")` as the benchmark (from
      `trading_agent/price_history.py`), then
      `volatility_sizing.scaled_max_position_pct(asset_vol, btc_vol, RISK_LIMITS["max_position_pct"])`.
      Both volatility calls need at least 3 accumulated bars for that
      asset — if either doesn't have enough yet (still warming up per
      step 5b), fall back to the flat `RISK_LIMITS["max_position_pct"]`
      instead (pass no override). **`BTC` itself is scanner-covered, not
      polled (see the note above steps 1-6), so its benchmark series
      will be empty whenever this step does run** - expect this to fall
      back to the flat cap in practice, an accepted, documented tradeoff,
      not a bug. Compute the order quantity with
      `RiskManager.position_size(portfolio_value, price, current_position_value, max_position_pct=<the scaled cap or None>, total_open_position_value=total_open_position_value)`.
      Skip if the resulting quantity is 0 (already at the per-asset cap,
      or the `max_aggregate_position_pct` cap is already fully used by
      other open positions — see the hard rule on this below).
      **Scope note:** the scanner-based cycle below has no raw price
      series to compute volatility from (only point-in-time SMA values),
      so volatility-scaled sizing only applies on this polling path, not
      the scanner path. A scanner-detected `fresh_buy_cross` still sizes
      at the flat cap.
   e. If `"sell"`: sell the full existing position in that asset (a
      crossover-down signal means exit, not short — this agent is
      long-only).
   f. Re-check `can_trade()` before every individual order — the daily cap
      applies across the whole cycle, not per asset.
   g. Apply the same **auto-execution policy** as the scanner-based cycle
      below: if `DRY_RUN` is `True`, never place an order — log what
      would have been ordered and move on. If `DRY_RUN` is `False`, place
      the order automatically only when `RiskManager.can_auto_execute`
      says the notional is at/under `auto_execute_max_pct` of current
      total portfolio value, then notify
      the owner after the fact; otherwise present it as a recommendation
      and wait for explicit per-trade approval before calling
      `place_crypto_order`.

6. **Log the cycle summary.** For every asset: the signal, the action
   taken (or why it was skipped), and the resulting state
   (`trades_today`, `halted`).

## Scanner-based cycle (real signals, no 31-cycle warm-up)

Run this alongside steps 1-6 each cycle, for every `WATCHLIST` asset the
scanner covers (currently all of them - see the note above steps 1-6).
It uses real historical data from the start (the RobinHood scanner's
server-side `closeAvg`), instead of waiting for
`price_history.py` to accumulate enough local bars - this is why these
assets don't also need the polling path.

**Preferred: `trading_agent/run_cycle.py` (added 2026-09-25, token
efficiency).** Once `run_scan`, `get_portfolio`, and `get_crypto_positions`
(or `get_equity_positions` for the stock cycle below) have been called
this cycle, save each raw response to a file and run:
`python3 trading_agent/run_cycle.py --asset-class crypto --scan-file
<scan.json> --portfolio-file <portfolio.json> --positions-file
<positions.json>` (`--asset-class stock` and `get_equity_positions` for
the stock cycle). It runs `start_of_day`/`check_circuit_breaker`/
`can_trade()`, calls `scanner_signals.classify(...)` for every watchlist
asset present in the scan and `exit_criteria.check_exit(...)` for every
held position, logs `excellent_watch` entries to `CycleLogStore` as a
side effect (pass `--no-log` to skip that), and tags any `fresh_buy_cross`
strong enough to qualify for the "awesome trade" aggregate-cap override
(see the Hard rules section) as `[AWESOME]` in its output — replacing
the hand-written per-cycle Python this playbook used to require. It is
read-only otherwise: it never calls a RobinHood tool or places an order.
Acting on what it reports — cooldown/concurrent-cap checks, sizing,
`preview_crypto_order`/`place_crypto_order` — is still done by hand,
exactly as described below. **Recording the outcome is not done by
hand** (added 2026-09-29, after a session-permission block on an
inline `RiskManager.record_trade()`/`CycleLogStore.record()` call kept
a real executed trade unrecorded for several cycles): pass
`--record-trade-asset`/`-side`/`-quantity`/`-price` (plus
`-protective`, `-classification`, `-crossover-pct`, `-notional`,
`-order-id` as applicable) on the *same* `run_cycle.py` invocation
after placing the order, rather than a separate inline script — it
inherits the same already-permitted command pattern instead of
triggering a new permission check. See `run_cycle.py --help` for the
full flag list.

**`--record-trade-price` MUST be the order's real fill VWAP
(`average_price` from `place_crypto_order`/`place_equity_order`'s
response), never the order's requested/entered/limit price** (found
2026-09-29, full-system audit: a live cycle recorded a LINK stop-loss's
`limit_price` of 14.50 instead of its real `average_price` of
14.5557783 — the sixth time this exact mistake has happened, after five
supposedly-fixed instances on 2026-09-28 alone; LINK/CRV/AVAX/DOGE/SOL
before it. This has never actually been fixed at the root, only patched
after the fact each time - treat this line as the fix.). A market order
in particular can fill meaningfully away from its quoted price; a
marketable limit order fills at its limit or better, so its
`average_price` is *at least as good as*, and often different from,
the `limit_price` passed to place the order. Always re-read the order's
own response (or a follow-up `get_crypto_orders`/`get_equity_orders`
call with that order's id) for `average_price` before recording -
never reuse the price you originally computed to size or place the
order.

1. Run the saved scan (`run_scan`, scan_id `8f2ca450-1f7f-4e69-b015-daafe494c14e`
   — "Crypto SMA(10,30) 1h Crossover — Strategy Screener"), which returns
   `SMA 10 (1h)`, `SMA 30 (1h)`, `Relative volume`, and `% Change` for
   every crypto pair Robinhood offers. `Relative volume` is real crypto
   data (`volume(1h,1) / volumeAvg(14,1h)`, the most recent hour's volume
   over its own 14-hour average) - see backtest_2026-09-23.md's "Volume
   entry confirmation filter" section for how the threshold was chosen.
2. Filter the results to `WATCHLIST` from `config.py`.
3. For each watchlist asset, call
   `scanner_signals.classify(asset, sma10, sma30, pct_change, relative_volume=relative_volume)`
   from `trading_agent/scanner_signals.py`. As of the entry-confirmation filter
   (backtest_2026-09-23.md), a crossover no longer fires the same cycle it's
   detected - it's held "pending" for one cycle, then only classified
   `fresh_buy_cross`/`fresh_sell_cross` if it still holds and clears
   `entry_filter.DEFAULT_MIN_STRENGTH_PCT` (0% by default as of the
   broader re-tuning in backtest_2026-09-23.md - persistence alone, no
   additional strength requirement). A confirmed buy cross is additionally
   downgraded to `"hold"` if `Relative volume` is below
   `volume_filter.DEFAULT_VOLUME_MIN_RATIO` (0.4 by default) - an
   unconvincing, low-volume breakout; this never applies to a sell cross.
   An immediate reversal classifies `"hold"`.
4. Act on the classification:
   - `fresh_buy_cross`: check `PositionStateStore().in_cooldown(asset)`
     first — if `True`, skip this asset entirely this cycle (the whipsaw
     cooldown, see step 5d above; same rule, same reasoning, applies here
     too). Next check `RiskManager.can_open_new_position(open_position_count)`
     — if `False`, skip this asset entirely this cycle too (the
     concurrent-positions cap, see step 5d above; same rule applies here).
     Otherwise compute the order notional with
     `RiskManager.position_size(..., total_open_position_value=total_open_position_value,
     max_aggregate_pct=RISK_LIMITS["awesome_trade_aggregate_pct"] if
     abs(crossover_pct) >= RISK_LIMITS["awesome_trade_min_crossover_pct"]
     else None)` — an "awesome trade" (a confirmed `fresh_buy_cross`
     whose `crossover_pct` also clears the `excellent_watch` bar, added
     2026-09-25, owner request) may size against the full
     `awesome_trade_aggregate_pct` ceiling (100%) instead of the normal
     `max_aggregate_position_pct` (60%) — it's still using real, unlevered
     capital, just allowed into the last slice of it that an ordinary
     signal cannot reach. `run_cycle.py` above tags these `[AWESOME]` in
     its output. (quantity × price) and continue below; skip this asset
     if the resulting quantity is 0 (the aggregate cap in effect for this
     trade is already fully used — see the hard rule below). If the order
     executes, increment `open_position_count` and add its notional to
     `total_open_position_value` before moving to the next asset in this
     cycle.
   - `fresh_sell_cross`: **first check the asset's held quantity**
     (`quantity_transferable` from step 0's crypto positions). **If it's
     0 — no open position in this asset — this is a spot, long-only
     strategy with no shorting: there is nothing to sell.** Log
     `CycleLogStore().record(asset, "fresh_sell_cross", crossover_pct,
     "blocked_no_position")` (see the Cycle logging table below) and
     move on to the next asset — do not call `preview_crypto_order` or
     `place_crypto_order`. This is the common case for most watchlist
     assets most cycles (a sell-cross firing on something you never
     bought is not a signal to act on, just noise from tracking a wider
     watchlist than what's actually held) and is distinct from
     `excellent_watch`'s "worth discussing" framing — it needs no
     notification, since there's no decision for the owner to make about
     a position that doesn't exist. If `quantity_transferable > 0`, this
     is a real exit candidate: no cooldown check (cooldown only blocks
     new entries, never exits). **Profitability gate (added 2026-09-28,
     owner-approved after a real DOGE/SOL exit both closed at a loss
     this check would have caught — see
     `backtest_2026-09-28_sell_cross_profit_gate.md`):** before doing
     anything else, get the position's average cost basis (same
     `cost_basis_fallback.average_cost_basis_from_trade_log` fallback
     used in "Per-position exit rules" whenever `get_crypto_positions`
     reports a zero cost basis) and the current mark price
     (`get_crypto_quotes`), then call
     `profit_gate.blocks_sell_cross(current_price, avg_cost_basis, profit_gate.MIN_SELL_PROFIT_PCT)`.
     If `True` (the position is below breakeven — `MIN_SELL_PROFIT_PCT`
     is `0.0`), **hold**: log
     `CycleLogStore().record(asset, "fresh_sell_cross", crossover_pct,
     "blocked_unprofitable", price=current_price, avg_cost_basis=avg_cost_basis)`,
     call `PositionStateStore().mark_gate_blocked(asset)` (a no-op if
     already blocked from an earlier cycle — see "Per-position exit
     rules" below for the every-cycle floor check this starts), and move
     on to the next asset — do not preview or place any order.
     This never overrides stop-loss: "Per-position exit rules" below
     still runs every cycle regardless of this gate, so a position held
     back here remains fully protected from a further decline. Only when
     the gate does *not* block (position at or above breakeven) does
     this become a real exit to act on. The order quantity is the
     **full held `quantity_transferable`** — not `RiskManager.position_size(...)`,
     which sizes a *buy* against `max_position_pct` and has no meaning
     for a sell; compute notional as quantity × current price instead.
     **Auto-execution policy (owner-authorized 2026-09-22, see
     `config.py`):** if `DRY_RUN` is `False` and
     `RiskManager.can_auto_execute(order_notional_usd, portfolio_value)` is
     `True` (i.e. the order is at or under
     `RISK_LIMITS["auto_execute_max_pct"]` of current total portfolio
     value, from this cycle's `get_portfolio` call), preview the order
     with `preview_crypto_order`, place it with
     `place_crypto_order`, record it via `run_cycle.py`'s
     `--record-trade-*` flags (see "Per-cycle helper" above) with the
     actual filled quantity/price, and then **notify the account owner
     after the fact** with what was executed — do not ask first, this is
     the pre-authorized automatic path. If the order is larger than the
     threshold (or `DRY_RUN` is `True`), present it as a recommendation
     instead — asset, direction, current price, suggested size — and
     stop; do not call `place_crypto_order` until the owner explicitly
     approves that specific trade. Use `preview_crypto_order` to show
     them exact cost/fee first in that case too. **Order type (changed
     2026-09-24, owner request - "limit orders to the best price from
     our analysis"): use a marketable limit order (`type=limit`,
     `limit_price` at or slightly above the current ask for a buy / at
     or slightly below the current bid for a sell, from
     `get_crypto_quotes`), not `type=market`.** `place_crypto_order`'s
     own documented "collar" on plain market orders is up to ~1% worse
     than the live quote for a buy and up to ~5% worse for a sell - a
     confirmed signal could execute meaningfully worse than the price
     that triggered it. A marketable limit gets the same effective
     near-certain fill in normal liquidity while capping the worst case
     at the limit price - mirrors what the stock scanner cycle
     (`review_equity_order`/`place_equity_order`) already does below,
     for the identical reason. This applies to every crypto order this
     routine places: fresh-cross entries and exits here, and the
     protective stop-loss/take-profit exits in "Per-position exit
     rules" below - all of them switch from market to marketable limit.
     **If placing by `quantity` is rejected for excess decimal
     precision ("Your order quantity has too much precision"), switch
     the sizing input to `dollar_amount` - never switch `type` to
     `market` as part of that same fix.** `dollar_amount` is fully
     supported with `type=limit` (`preview_crypto_order`'s own schema:
     quantity is derived from `dollar_amount` at `limit_price` when the
     order is placed), so a precision rejection is never a reason to
     drop the limit-order policy. This exact confusion caused a real
     deviation on 2026-09-27: a precision-rejection workaround swapped
     both the sizing method *and* the order type at once, so 5 of that
     day's 6 crypto orders (CRV, DOGE, AVAX, SOL, LINK) went out as
     `type=market` with no collar protection, undetected until that
     day's after-action review cross-checked against real Robinhood
     order records. All fills happened to land favorably that day, but
     that was luck, not the policy working - see `CHANGELOG.md`.
   - `excellent_watch`: not a strategy-confirmed signal, never
     auto-executed regardless of size. Alert the account
     owner with the asset, its crossover_pct/% change, and why it didn't
     meet the fresh-cross bar. Frame it as "worth discussing," not a
     recommendation — no preview, no suggested size, just the numbers and
     an open question.
   - `hold`: no action, no message needed (stay quiet unless the account
     owner asked for a status update).

## Scanner-based cycle — stocks

Run this alongside the crypto scanner cycle above, every cycle **during
regular market hours only (9:30-16:00 ET, Mon-Fri)**. Unlike crypto,
equities don't trade 24/7 and market/stop orders only fill during regular
hours (see "Hard rules" below) - skip this whole section outside that
window rather than evaluating signals that can't reliably execute. v1
scope: extended-hours trading is not implemented.

1. **Do NOT use the saved stock scan (scan_id `6e009dcf-d184-45a7-915f-ccfc50b4e6be`)
   to source signals — retired for this purpose 2026-09-25 (see "Known gap"
   below: it silently dropped 9 of 10 `STOCK_WATCHLIST` names almost every
   cycle observed on 2026-09-24/25 due to its 200-row pagination cap).**
   Instead, call `get_equity_historicals(symbols=STOCK_WATCHLIST` (all 10
   in one call — the tool accepts up to 10 symbols), `interval="hour",
   bounds="regular", start_time=<~7 days back, comfortably covers 30
   regular-hours 1h bars even across a weekend>)` and
   `get_equity_quotes(symbols=STOCK_WATCHLIST)` once each, up front.
2. For each `STOCK_WATCHLIST` symbol, compute the signal inputs via
   `equity_signals.py` (new module, added 2026-09-25) instead of reading
   scan columns:
   - `sma10, sma30 = equity_signals.sma_pair(closes)` — `closes` is that
     symbol's `bars[].close_price`, oldest-to-newest. If `sma10` comes
     back `None` (fewer than 30 bars — a newly-added watchlist symbol
     still warming up), skip that symbol silently this cycle, same as a
     symbol missing from a scan page.
   - `relative_volume = equity_signals.relative_volume(volumes)` —
     `volumes` is that symbol's `bars[].volume`, same order.
   - `pct_change = equity_signals.pct_change_from_quote(last_trade_price, previous_close)`
     from that symbol's `get_equity_quotes` result (`quote.last_trade_price`,
     `quote.previous_close`).
3. Call
   `scanner_signals.classify(asset, sma10, sma30, pct_change, relative_volume=relative_volume)`
   — unchanged, still the exact same function used for crypto (it's
   asset-agnostic, keyed only by the symbol string); it persists state in
   the same `scanner_state.json`, so crypto and stock symbols coexist
   there without collision as long as tickers don't overlap (they don't).
   Same persistence-then-strength-then-volume gating as the crypto cycle.
   (`run_cycle.py --asset-class stock --historicals-file ... --quotes-file ...`
   wraps steps 1-3 in one script, same as it already does for crypto.)
4. Act on the classification, mirroring the crypto scanner cycle exactly,
   with these substitutions:
   - Tool substitutions: `get_equity_quotes` instead of `get_crypto_quotes`;
     `review_equity_order` instead of `preview_crypto_order`;
     `place_equity_order` instead of `place_crypto_order` (pass
     `account_number` `581911765`, not `rhs_account_number`); no crypto
     `symbol`-as-pair resolution - just the plain ticker.
   - Order type: use a **marketable limit order** (`type=limit`,
     `limit_price` at or slightly above the current ask for a buy / at or
     slightly below the current bid for a sell, `market_hours=regular_hours`),
     not `type=market` - the account owner has not been asked about
     accepting plain market-order slippage on equities the way the crypto
     path already does, and a marketable limit gets the same effective
     fill during regular hours with explicit price protection. Use
     `quantity` (shares), not `dollar_amount` - `place_equity_order` only
     accepts a fractional `quantity` on `type=market`, never `type=limit`
     (confirmed live 2026-09-29, PANW: a $92.03-sized order came out to
     0.2413 shares, which a marketable limit order can't place at all).
     **Always run `RiskManager.position_size(...)`'s result through
     `equity_signals.whole_share_quantity(...)` before sizing/placing an
     equity order** - it floors to a whole share, which can only put the
     order at or under the risk-sized budget, never over it. If that
     floors to `0.0`, the per-share price alone exceeds this cycle's
     budget: log `"recommended"` and wait for approval, the same as any
     order over `auto_execute_max_pct` - never round up over the cap and
     never fall back to `type=market` to force the exact fractional
     quantity through (see the 2026-09-27 order-type-policy-gap incident,
     `CHANGELOG.md` - a market order dropped the price-protection collar
     it was never authorized to drop).
   - `open_position_count` / `total_open_position_value`: the **same
     shared counters** from step 2 above, not separate ones - a stock
     entry and a crypto entry draw from the same concurrent-positions cap
     and the same aggregate-value cap.
   - Cooldown and concurrent-cap checks (`PositionStateStore`,
     `RiskManager.can_open_new_position`) work identically - both are
     keyed by asset symbol / a shared counter, neither assumes crypto.
   - Profitability gate on `fresh_sell_cross` (see the crypto cycle's
     step 3 above): identical `profit_gate.blocks_sell_cross` check, but
     the average cost basis comes directly from `get_equity_positions`'s
     `average_cost` field — no `cost_basis_fallback` needed on the
     equity side, same as "Per-position exit rules" below already notes
     (none has been observed there either).
   - Auto-execution policy is identical: `RiskManager.can_auto_execute`
     doesn't distinguish asset class, so a confirmed stock signal at/under
     `auto_execute_max_pct` of current total portfolio value auto-executes
     exactly like a crypto one.
   - `excellent_watch` and `hold` handling: identical to the crypto cycle.
   - **Research context on recommendations only (added 2026-09-23, see
     `research_agent/README.md`):** when a stock signal is presented as a
     recommendation (oversized, awaiting the owner's approval — never on
     the bounded-auto-execution path, which stays mechanical and
     untouched by this), call
     `research_agent.research_log.ResearchLogStore().entries_for_asset(asset, since=<7 days ago, ISO date>)`
     and include any hits (news, SEC filings, upcoming earnings) alongside
     the recommendation so the owner has research context at the moment
     they're deciding whether to approve. Advisory only — an empty result
     means no research has been logged yet for that symbol, not that
     nothing is happening; never block or resize a recommendation based on
     what this lookup returns. Crypto has no research coverage in v1 (see
     `research_agent/README.md`'s "Known gap: crypto"), so this lookup
     only applies to `STOCK_WATCHLIST` symbols, never `WATCHLIST`.

## Per-position exit rules (stop-loss / take-profit)

Run this for every watchlist asset with an open position (`quantity_transferable > 0`
from `get_crypto_positions`, or `quantity > 0` from `get_equity_positions`
for `STOCK_WATCHLIST` symbols), every cycle (equities: during regular
market hours only, same as the stock scanner cycle above), independent of
and in addition to the SMA-based sell signal above.

**Stock positions**: `get_equity_positions` returns `average_cost` directly
per position - no cost-basis gap has been observed on the equity side (see
step 1 below, which is crypto-specific), so use it as-is; skip the
`cost_basis_fallback` step entirely for stocks. Sell via
`place_equity_order` (`side=sell`, marketable limit as above, same
`account_number`). Everything else in this section (stop-loss/take-profit
thresholds, `PositionStateStore` cooldown/took-profit tracking, bypassing
`can_trade()`/circuit breaker/size caps) applies identically to stock
positions.

1. Get the position's average cost basis (sum `direct_cost_basis` / sum
   `direct_quantity` across `cost_bases` from `get_crypto_positions` — see
   that tool's own guidance on when the average only covers a subset of
   units) and the current mark price (`get_crypto_quotes`).
   **If `direct_quantity` sums to 0** despite the position being held
   (`quantity_transferable > 0`) - a real, observed gap where Robinhood's
   cost-basis ledger doesn't reflect a normally-filled direct purchase
   (first seen on the PEPE position bought 2026-09-22, still 0 a full day
   later despite a clean, fully-filled, non-transfer buy) - fall back to
   `cost_basis_fallback.average_cost_basis_from_trade_log(asset, RiskManager(...).state["trade_log"])`
   from `trading_agent/cost_basis_fallback.py`. It replays the locally
   recorded buy/sell history for that asset into the same weighted-average
   cost basis `get_crypto_positions` itself would compute. Returns `None`
   if the local log also shows no open quantity - in that rare case
   (e.g. state.json predates the position, or was reset) skip the
   protective-exit checks below for this cycle rather than guessing, and
   note it in the cycle log so it's visible. Always prefer
   `get_crypto_positions`' own figure when it's non-zero; this is a
   fallback for when it isn't, not a general substitute.
2. Check whether take-profit was already taken for this asset:
   `PositionStateStore().took_profit(asset)` from
   `trading_agent/position_state.py`.
3. Call `exit_criteria.check_exit(current_price, avg_cost_basis, took_profit)`
   from `trading_agent/exit_criteria.py`. (A trailing-stop and a
   profit-lock mechanism were both built and backtested in earlier
   sessions - see `backtest_2026-09-24_trailing_stop.md` and
   `backtest_2026-09-25_profit_lock.md` - but consistently hurt returns,
   sometimes severely, across real-series backtests, for the same
   underlying reason: clipping a position before a strong trend fully
   plays out costs more than it protects. Never adopted, and removed
   entirely 2026-09-28 - owner request, "keep it simple" - rather than
   kept as disabled dead code; see those docs and `exit_criteria.py`'s
   git history if either is revisited.) It returns one of:
   - `("stop_loss", 1.0)` — price is 4%+ below cost basis. Sell the
     **entire** position (`quantity_transferable`).
   - `("take_profit", 0.70)` — price is 8%+ above cost basis and profit
     hasn't been taken yet. Sell **70%** of `quantity_transferable`
     (round down to the pair's `min_order_quantity_increment` from
     `get_currency_pairs`), then call
     `PositionStateStore().mark_took_profit(asset)` so this doesn't
     re-trigger next cycle on the remaining 30%.
   - `(None, 0.0)` — no protective exit fires this cycle; the SMA
     death-cross check above still applies independently.
4. **Gate floor (added 2026-09-28, owner-approved — "should the gate come
   with a floor so it can't hold forever" — see
   `backtest_2026-09-28_gate_floor_and_tighter_stops.md`):** unlike step 5
   below, this step is **not** exempt from the daily-cap/circuit-breaker
   gate ("Check the daily trade cap" above) — it's a same-substance
   stand-in for the ordinary `fresh_sell_cross` death-cross exit it forces
   through, not a protective safety net, so skip this step entirely for
   the rest of the cycle if that earlier check already stopped it (same
   as any other non-protective exit). Otherwise: if step 3 didn't already
   close the position, and
   `PositionStateStore().hours_since_gate_blocked(asset)` is not `None`
   (this asset's `fresh_sell_cross` is currently being held by the
   profitability gate — see that section above), do the following every
   cycle for as long as the block lasts, independent of whether a fresh
   sell signal is present this cycle (`blocks_sell_cross` only fires once,
   at the bar the signal itself occurs — see `profit_gate.py`'s
   docstring):
   - If `current_price` has recovered to `avg_cost_basis` (unrealized P&L
     at or above `profit_gate.MIN_SELL_PROFIT_PCT`), call
     `PositionStateStore().clear_gate_blocked(asset)` and stop — no forced
     exit, the position is simply no longer gated (a future
     `fresh_sell_cross` will re-evaluate the gate fresh next time one fires).
   - Otherwise call
     `profit_gate.gate_floor_should_force_exit(current_price, avg_cost_basis,
     bars_since_blocked=hours_since_gate_blocked, max_hold_bars=profit_gate.GATE_MAX_HOLD_HOURS)`
     (a companion price floor was backtested the same day, found
     redundant once `STOP_LOSS_PCT` is this tight, and removed entirely
     2026-09-28 rather than kept disabled — only the 24h time floor
     exists). If `True`, sell the **entire** position (`quantity_transferable`) the
     same way as a `stop_loss` exit in step 5 below, logging
     `reason="gate_floor"` instead. **This is NOT a protective exit** —
     unlike stop-loss/take-profit, record it via `run_cycle.py`'s
     `--record-trade-*` flags **without** `--record-trade-protective` and
     it still counts toward `trades_today` (same as the `fresh_sell_cross`
     death-cross exit it stands in for — see the note on this in step 5
     below).
5. **These exits bypass `can_trade()`, the daily trade cap, the circuit
   breaker, and `auto_execute_max_pct`** — protective exits are never
   blocked by the gates that limit new risk-taking, and (2026-09-28,
   owner request — "non-negotiable trades... does not count towards our
   daily trades") never **consume** the daily trade cap either, so a
   stop-loss/take-profit firing earlier in the day can never crowd out a
   later real signal. The only gate that still applies is `DRY_RUN`:
   while `True`, log what would have been sold and take no action; while
   `False`, place the sell immediately - **`place_crypto_order`,
   `side=sell`, `type=limit`, `limit_price` at or slightly below the
   current bid (same marketable-limit reasoning as the scanner-cycle
   order type note above - not `type=market`, changed 2026-09-24)** -
   record it via `run_cycle.py`'s `--record-trade-*` flags with
   `--record-trade-protective` set (still fully logged to `trade_log`
   for cost-basis/daily-review purposes, just exempt from
   `trades_today`), and notify the account owner immediately
   with the reason (stop_loss/take_profit), quantity, price, and
   resulting P/L. The `fresh_sell_cross` death-cross exit and a
   gate-floor-forced exit (see the profitability gate section) are NOT
   protective in this sense — both still record via the same flags
   without `--record-trade-protective` and still count toward `trades_today`, same
   as before; only the two safety-net exits above are exempt.
6. When a position's `quantity_transferable` reaches 0 (fully closed, by
   any combination of SMA exits, a gate-floor exit, and these protective
   exits), call `PositionStateStore().reset(asset)` (clears the
   take-profit flag, so a future fresh entry starts without a stale one),
   `PositionStateStore().record_exit(asset)` (starts the whipsaw
   cooldown — `DEFAULT_COOLDOWN_HOURS`, 4h by default — blocking a new
   entry into this asset until it expires, even if a fresh buy signal
   fires in the meantime), AND `PositionStateStore().clear_gate_blocked(asset)`
   (so a future block on a future position in this asset starts its own
   fresh clock, rather than inheriting a stale timestamp — a no-op if this
   position was never gate-blocked). All three calls are needed; they track independent
   state and `reset` does not clear the cooldown.

## Hard rules

- Never place an order without going through steps 3–4 immediately before
  it (risk state can change mid-cycle if multiple orders are placed).
- Never bypass `DRY_RUN`. It only becomes `False` when the account owner
  edits `trading_agent/config.py` themselves after verifying the MCP
  connection is live and correct.
- Never size a fresh entry without passing `total_open_position_value`
  (step 2) into `RiskManager.position_size(...)`. `RISK_LIMITS["max_aggregate_position_pct"]`
  (60% as of 2026-09-25 — history: 50% → 75% same-day on live evidence
  the 50% cap bound twice → 60% same day again after backtesting showed
  75% losing to 50% in 3 of 4 windows, incl. a negative worst case; 60%
  won on both worst-case AND mean return for a bounded drawdown cost —
  see `backtest_2026-09-25_aggregate_cap.md`) is a hard cap on the
  combined mark-to-market value of every open position at once — it
  does not follow automatically from `max_position_pct` and
  `max_concurrent_positions` alone (20% x 5 = 100%, well over 60% if
  unchecked). It only ever limits or zeroes a fresh entry's size, never
  an exit, and applies identically on both the polling and scanner
  paths.
- **"Awesome trade" override (added 2026-09-25, owner request):** a
  confirmed `fresh_buy_cross` whose `|crossover_pct|` also clears
  `RISK_LIMITS["awesome_trade_min_crossover_pct"]` (5.0 — the same bar
  `scanner_signals.EXCELLENT_CROSSOVER_PCT` uses for `excellent_watch`)
  may size against `RISK_LIMITS["awesome_trade_aggregate_pct"]` (100%)
  instead of the normal 60% aggregate cap — pass that value as
  `RiskManager.position_size(...)`'s `max_aggregate_pct` argument for
  that one order only. This does not raise `max_position_pct` (still
  20% per asset) or `max_concurrent_positions` (still 5) — only the
  aggregate ceiling moves, and only for a trade strong enough to already
  qualify as `excellent_watch`-tier on its own. Untested via backtest
  (PLAYBOOK.md sizing policy isn't something `backtest.py` models);
  revisit if this override fires often enough to be worth backtesting.
  See `config.py`'s comment on these two keys for the full rationale.
- **Shared budget, crypto + stocks (owner's explicit choice, 2026-09-23):**
  `RISK_LIMITS` is one set of numbers spanning `WATCHLIST` and
  `STOCK_WATCHLIST` together — `max_aggregate_position_pct`,
  `max_concurrent_positions`, and `max_trades_per_day` are never
  recomputed or checked separately per asset class. `open_position_count`
  and `total_open_position_value` (step 2) must include both lists'
  positions before either scanner cycle sizes anything; a stock trade and
  a crypto trade in the same day draw from the same daily-trade-cap
  counter, and an open stock position counts toward the same
  concurrent-positions cap a crypto position would.
- **Stocks only trade during regular market hours (9:30-16:00 ET, Mon-Fri)
  in v1** — skip the entire stock scanner cycle and per-position exit
  checks for `STOCK_WATCHLIST` symbols outside that window; a signal isn't
  re-evaluated or queued, it's simply not acted on until the next cycle
  that falls inside market hours. Crypto is unaffected (24/7, unchanged).
- Auto-execution is bounded and narrow, not a general license: only a
  `fresh_buy_cross` / `fresh_sell_cross` signal, only when `DRY_RUN` is
  `False`, only when
  `RiskManager.can_auto_execute(order_notional_usd, portfolio_value)` is
  `True` (at/under `RISK_LIMITS["auto_execute_max_pct"]` of current total
  portfolio value, owner-set).
  `excellent_watch` is never auto-executed regardless of size. Anything
  outside those conditions is a recommendation requiring the account
  owner's explicit, per-trade approval before `place_crypto_order` is
  called.
- Every auto-executed trade is reported to the account owner immediately
  after placement (asset, side, quantity, price, order id) — auto-execute
  means no approval gate before the order, not silence after it.
- Never increase `RISK_LIMITS` or `max_trades_per_day` from within a
  trading cycle. Those are owner-edited config, not runtime state.
- Protective exits (stop-loss, take-profit) are the one exception to the
  approval/size-cap rules above: once `DRY_RUN` is `False`, they execute
  immediately regardless of order size, `can_trade()`, or the circuit
  breaker, per the "Per-position exit rules" section — reducing existing
  risk is never held back the way taking on new risk is. `DRY_RUN` itself
  still gates them same as everything else. They're also exempt from
  **consuming** `max_trades_per_day` (2026-09-28, owner request —
  `RiskManager.record_trade(..., protective=True)`): a stop-loss/take-profit
  firing earlier in the day never crowds out a later real signal's slot.
  A `fresh_sell_cross` death-cross exit and a gate-floor-forced exit are
  ordinary trades for this purpose — both still consume a slot, only the
  two safety-net exits above are exempt.
- This agent is long-only: it buys and exits, it never shorts or uses
  margin/leverage.
- The profitability gate (`profit_gate.blocks_sell_cross`, added
  2026-09-28) only ever holds a `fresh_sell_cross` exit — it never holds
  back a stop-loss or take-profit, and it never applies to anything
  other than a plain `fresh_sell_cross`/death-cross signal. Always run
  "Per-position exit rules" (stop-loss/take-profit) for every open
  position every cycle regardless of whether this gate blocked a
  death-cross the same cycle — the two checks are independent, and a
  position held back here remains fully exposed to a real stop-loss.
- Never skip the cooldown check on a new-entry signal (`fresh_buy_cross`,
  either detection path). `PositionStateStore().in_cooldown(asset)` must
  be checked before computing order size or presenting a recommendation —
  a confirmed signal during cooldown is still skipped entirely, not
  merely downgraded to a recommendation. The cooldown never blocks exits
  (sells, stop-loss, take-profit) — only new entries.
- Never skip the concurrent-positions check on a new-entry signal, same
  rule as the cooldown above. `RiskManager.can_open_new_position(open_position_count)`
  must be checked (after the cooldown, before sizing) whenever the signal
  is a fresh entry into an asset with no existing position — a confirmed
  signal is still skipped entirely while `RISK_LIMITS["max_concurrent_positions"]`
  is already reached, not downgraded to a recommendation. It never blocks
  exits, and never blocks a signal for an asset already held.
- Never omit `relative_volume` from `scanner_signals.classify()` on the
  scanner-based cycle when the scan result has it (it does, as of the
  "Relative volume" column added 2026-09-23) — a confirmed buy cross on
  thin volume should be downgraded to `"hold"` inside `classify()` itself,
  not treated as a fresh entry. **Scope: scanner path only.** The polling
  path (`price_history.py`, currently dormant - see the note above steps
  1-6) has no volume field available — `get_crypto_quotes` doesn't
  return one and there's still no crypto historicals tool — so a
  polling-detected `"buy"` signal is never volume-gated whenever that
  path does run; this is
  the mirror image of volatility-scaled sizing (step 5d), which is
  polling-only for the same underlying reason (the scanner has no raw
  price series to compute volatility from). It never blocks
  `fresh_sell_cross`.
- Never treat a `get_crypto_positions` cost basis of 0 as "no cost basis,
  skip the exit checks" without first trying the
  `cost_basis_fallback.average_cost_basis_from_trade_log` fallback (see
  "Per-position exit rules" step 1) — a zero cost basis on a real held
  position is a known data gap, not proof the position has none. Only
  skip the stop-loss/take-profit checks for that cycle if the fallback
  *also* returns `None`.

## Cycle logging (for the daily after-action review)

`RiskManager.record_trade(...)` only captures what actually executed —
it can't show what the strategy *saw* but didn't act on. Call
`CycleLogStore().record(asset, classification, crossover_pct, action, **extra)`
from `trading_agent/cycle_log.py` for every non-hold event this cycle,
on both the polling and scanner paths, so the end-of-day review
(`daily_review.py`) has the full picture:

| Event | `action` | Notes |
|---|---|---|
| Auto-executed new entry | `"executed"` | include `price`, `quantity`, `notional`, `order_id` |
| New entry above `auto_execute_max_pct` of portfolio value, awaiting approval | `"recommended"` | include the suggested `price`/`quantity`/`notional` |
| `fresh_buy_cross` skipped — in cooldown | `"blocked_cooldown"` | |
| `fresh_buy_cross` skipped — `max_concurrent_positions` reached | `"blocked_concurrent_cap"` | |
| `fresh_buy_cross` sized to 0 — `max_aggregate_position_pct` reached | `"blocked_aggregate_cap"` | |
| Confirmed cross downgraded to `"hold"` inside `classify()` by the volume gate | `"blocked_volume"` | log this even though `classify()` itself returned `"hold"`, not `fresh_buy_cross` — the whole point is capturing what got filtered out |
| `excellent_watch` | `"excellent_watch"` | |
| `fresh_sell_cross` on an asset with no open position (nothing to sell — see the hard rule above) | `"blocked_no_position"` | no owner notification needed, nothing for them to decide |
| `fresh_sell_cross` on a real held position, but the profitability gate held it (position below breakeven — added 2026-09-28) | `"blocked_unprofitable"` | include `price`, `avg_cost_basis` — the exit is only deferred, not skipped for good: stop-loss still protects the position every cycle, and a later cycle may see it clear the gate or hit stop-loss/take-profit instead |
| Stop-loss or take-profit fired | `"protective_exit"` | include `reason` (`"stop_loss"`/`"take_profit"`), `price`, `avg_cost_basis`, resulting P/L |
| Gate floor forced an exit the profitability gate had been holding (added 2026-09-28) | `"executed"` | include `reason="gate_floor"`, `price`, `avg_cost_basis`, `quantity`, resulting P/L — not protective, counts toward `trades_today` like any other exit (see "Per-position exit rules" step 4) |

A plain `"hold"` with nothing else notable is not logged — this is an
event log of what needed a decision, not a full cycle trace.

## Slack notifications (added 2026-09-27, owner request; channel corrected same day; narrowed to notable-only same day)

The hourly trading cycle and the daily after-action review both also
post to Slack channel `#voltrap-agents-work` (`channel_id
C0C49LR128P`) via `slack_send_message`, alongside `PushNotification`.
(The original channel this was set up on,
`#votrap-agent-collaboration`/`C0C4P136JFQ`, was archived the same day
the owner set it up and replaced with this public channel — if
`slack_send_message` ever fails against `C0C49LR128P`, re-check with
`slack_list_user_channels` rather than assuming the old ID.)

**Hourly cycle:** posts **only when there's something pertinent** —
the same trigger condition as `PushNotification` (an executed trade, a
protective exit, a recommendation awaiting approval, or a blocked
signal worth noting). No "all quiet" line on a plain hold cycle. This
channel has Codex (a separate coding agent the owner may use for
backend work on this same repo) connected to it — the goal is a clean,
high-signal record Codex can pick up real context from, not an hourly
noise stream (this replaced an earlier "post every cycle regardless"
design from the same day, which the owner asked to narrow).

**Daily after-action review:** posts every day regardless (same as its
`PushNotification`) — a once-a-day substantive summary is inherently
pertinent, not noise, so it keeps the original always-on behavior. It
posts the fuller executive-summary/observations content (Slack has no
200-char limit, unlike `PushNotification`).

## Weekly watchlist review

Runs once a week (owner request, 2026-09-25: "remove stocks and crypto
that are not performing well and add those that have potential"). Every
past watchlist change (`watchlist_2026-09-22.md`,
`watchlist_2026-09-23_meme_removal.md`,
`watchlist_stocks_2026-09-23_large_cap.md`) was a deliberate, reviewed,
backtested swap, never a mechanical top-N replace — this keeps that
posture on a standing cadence instead of only when asked. **This review
never edits `config.py` itself.** It produces a written recommendation;
`WATCHLIST`/`STOCK_WATCHLIST` only change after the owner approves it, a
separate follow-up action — same rule the hourly Routine already states
("Do not modify RISK_LIMITS, DRY_RUN, WATCHLIST, or STOCK_WATCHLIST from
within this routine") extended to this Routine too.

1. **Score current holdings by trailing performance**, not today's
   signal strength (that's a different question from "should this
   stay" — see step 3). Load `RiskManager.state["trade_log"]`. For each
   `WATCHLIST`/`STOCK_WATCHLIST` asset, call
   `watchlist_review.trailing_trade_pnl(asset, trade_log, current_price)`
   (`trading_agent/watchlist_review.py`):
   - Not `None` → real trade history exists, this dollar P&L is the
     score.
   - `None` → never traded (the common case for most assets most
     weeks). Run a 90-day-hourly `backtest.py` pass against real
     historicals (`IBIT`/`ETHA` proxies for crypto, direct
     `get_equity_historicals` for stocks — same window used throughout
     this session's backtests) and use that return as the score
     instead.
2. Rank worst-case-first (this project's standing rule — see any
   `backtest_*.md`): sort ascending by score, check that the bottom
   entries aren't a lucky/unlucky single data point before trusting
   them. The bottom 1–2 are removal *candidates* — **skip any with a
   currently open position** (`quantity_transferable > 0` /
   `quantity > 0`); no forced liquidation as part of a routine review,
   note it and revisit next week once flat.
3. **Source addition candidates.** Run both production scans (crypto
   `scan_id 8f2ca450-1f7f-4e69-b015-daafe494c14e`, stocks `scan_id
   6e009dcf-d184-45a7-915f-ccfc50b4e6be` — filters already reflect the
   established floors: `Asset type = CRYPTO`, `$10B+` market cap) and
   call `watchlist_review.rank_by_crossover_strength(rows,
   exclude=<current watchlist + the meme/political exclusion list from
   watchlist_2026-09-23_meme_removal.md for crypto>)`. Take the top 2-3
   non-watchlist names per asset class.
   **Known gap (found 2026-09-25 dry run):** the stock scan's 397-name
   `$10B+` universe returns only 200 rows (a `frontend_limit`, no
   pagination — `run_scan` takes only `scan_id`), sorted by `Last desc`
   (highest-priced first), not by crossover strength — so this can
   systematically miss a strong candidate that's both lower-priced and
   outside the top 200 by price. Not a blocker (the crypto scan's full
   49-name universe always returns in full), but worth a mention in the
   week's review doc when it happens, same as any other real gap this
   project documents rather than silently working around.
4. **Backtest every candidate before proposing it** — never swap on a
   screener snapshot alone. Isolated `backtest.py` per candidate, plus a
   combined `portfolio_backtest.py` run (candidate(s) + current
   watchlist), same method as `watchlist_stocks_2026-09-23_large_cap.md`.
5. **Decide.** Only propose replacing a removal candidate with an
   addition candidate whose backtest *clearly* beats it (worst-case
   return/drawdown first, same bar as every parameter change this
   session). Most weeks the honest answer is "no change recommended" —
   write that up too, the same standard this project holds for a
   negative backtest result (see `backtest_2026-09-25_profit_lock.md`).
6. Write `trading_agent/watchlist_review_<date>.md` (same structure as
   the three existing watchlist docs: method, ranked table, backtest
   numbers, decision) — every week, whether or not a change is proposed.
   Commit and push it on `claude/robinhood-trading-mcp-sdp3cp`.
7. Send one `PushNotification` naming the recommendation (or "no change
   this week") and update the live log. Wait for explicit owner
   approval before touching `config.py`; once approved, edit
   `WATCHLIST`/`STOCK_WATCHLIST` and add the `CHANGELOG.md` entry, same
   as every prior swap.

Hard rules, same as the hourly Routine: never modify `RISK_LIMITS`,
`DRY_RUN`, `WATCHLIST`, or `STOCK_WATCHLIST` from within this Routine
itself; never place, preview, or cancel an order — this is a read-only
research and recommendation cycle.

## VOLTRAP (options wheel strategy: cash-secured puts → covered calls)

Added 2026-09-26 (owner request), renamed to **VOLTRAP** the same day: a
**second, independent** strategy on the same account (`581911765`,
already `option_level_3` — no upgrade needed). Goal: sell weekly
cash-secured puts (CSPs) for premium; if assigned, sell weekly covered
calls against the resulting shares. The point is **collecting premium,
not wanting assignment** — CSPs are an income play here, not a way to
acquire stock cheaply.

**Deliberately NOT part of `RISK_LIMITS`/`WATCHLIST` above.** A CSP's
risk is reserved cash collateral (100 × strike per contract), not a
mark-to-market position — a different accounting shape with no
crypto/stock analogue, so it gets its own budget (`VOLTRAP_RISK_LIMITS`
in `config.py`), own state file (`voltrap_state.json`, via
`voltrap_state.VoltrapStateStore`), own watchlist (`VOLTRAP_WATCHLIST`,
starts empty — populated by the live screen below each cycle, not
hand-picked), and its own go-live switch (`VOLTRAP_AUTO_EXECUTE`,
currently `False` — **recommend-only**, same conservative bootstrap the
crypto/stock bot itself started at before its own bounded auto-execution
was authorized). `DRY_RUN` continues to gate only the crypto/stock bot.

**Not live yet.** Free cash is currently ~$82 — nowhere near the ~$1,000+
a single real contract needs (confirmed live via `review_option_order`,
see CHANGELOG.md). The owner is depositing new funds specifically for
this strategy, sized as a % of total portfolio value
(`VOLTRAP_RISK_LIMITS["max_voltrap_pct"]`, proposed default 25%, owner
to confirm the exact number). **Do not place any real option order, and
do not create either Routine below, until (a) the owner confirms
`max_voltrap_pct` and (b) `get_portfolio` shows real free cash for it.**
Until then this section documents the mechanism only.

### State machine (`voltrap_state.py`, per symbol)

```
idle -> csp_open -> [expires OTM] -> idle (keep premium)
                 -> [assigned]    -> holding_shares
holding_shares -> covered_call_open -> [expires OTM] -> holding_shares
                                    -> [called away]  -> idle
```

### Candidate screening

Saved scan `e3983260-740b-4a84-8369-54420cbeafdd` ("Options Wheel
Candidates — IV/Liquidity Screener"), sorted `Last asc` (biases the
returned page toward affordable names — **re-check this sort against
the current VOLTRAP budget each time it matters**: if the budget grows
large enough that price is no longer the binding constraint, an ascending
price sort may cut off better-IV, higher-priced candidates the same way
it deliberately favors cheap ones now — same 200-row pagination cap as
every scan on this account, see README's "Known gap: stock scan
pagination"). Current filters (tuned live 2026-09-26 — see CHANGELOG.md
for why the first two attempts were rejected):
- `Asset type` `ANY_OF` `[STOCK, ETF]` — ETF is required to include
  leveraged names (SOXL/TQQQ/TSLL-style), explicitly in scope per the
  owner.
- `Implied volatility` `BETWEEN` `[0.35, 0.80]` — a floor alone (no
  ceiling) surfaced almost nothing but distressed microcap/binary-event
  names (150%+ IV) with real assignment-into-a-blowup risk, not genuine
  wheel candidates; the ceiling keeps the screen in "rich premium,
  liquid, real company/ETF" territory instead of "reflects a coin-flip
  FDA decision."
- `Average options volume` `>` `5000` (30d, 1d interval) and
  `Total open interest` `>` `20000` (1d interval) — liquidity floors,
  raised twice live before landing here; anything looser let through
  illiquid names with real slippage risk.
- `Last` `>` `5` — keeps out sub-$5 names, which skew penny-stock/low
  quality even when the liquidity/IV filters are otherwise satisfied.

Per cycle: `run_scan` this scan → `voltrap_candidates.rank_by_voltrap_fit(rows, max_collateral_per_contract=<current budget / desired concurrent positions>, min_avg_options_volume=VOLTRAP_RISK_LIMITS["min_avg_options_volume"], min_open_interest=VOLTRAP_RISK_LIMITS["min_open_interest"])`
→ for the top few survivors: `get_option_chains(underlying_symbol=...)`
→ `get_option_instruments(chain_id=..., expiration_dates=<nearest Friday>, type="put")`
→ `get_option_quotes(instrument_ids=[...])` for each strike (confirmed
live: the quote payload **does carry `delta`**, alongside
`chance_of_profit_short` — the direct "probability this expires OTM"
figure, worth cross-checking against the delta band) →
`voltrap_candidates.pick_strike_by_delta(instruments, VOLTRAP_RISK_LIMITS["target_delta_min"], VOLTRAP_RISK_LIMITS["target_delta_max"], "put")`
(falls back to `pick_strike_by_otm_pct` only if a quote payload is ever
missing delta) → `review_option_order` (pass `chain_symbol`/
`underlying_type` for real collateral + fee numbers) before ever
proposing a contract.

### Weekly + daily cycles (two new Routines, created only once funded)

1. **Weekly entry** (Monday, shortly after open): for `VOLTRAP_WATCHLIST`
   symbols in `idle`, run the screen above and open new CSPs within
   budget. For symbols in `holding_shares` (assigned the prior week),
   sell a covered call at/above `cost_basis` (never below — that would
   lock in a loss on assignment).
2. **Daily monitor** (once per market day, near close): check open
   `csp_open`/`covered_call_open` positions for deep-ITM/early-assignment
   risk; on expiration day, reconcile via `get_option_positions`/
   `get_option_orders` and drive the state transition via
   `VoltrapStateStore.resolve_csp`/`resolve_covered_call`. Rolling (buy-to-
   close + sell-to-open before expiration to avoid an unwanted
   assignment) is a real wheel technique but **out of scope for v1** —
   add only if the owner asks once the mechanism is proven live.

### Auto-execution

`VOLTRAP_AUTO_EXECUTE = False` (recommend-only): every cycle proposes a
specific contract (strike, expiration, premium, collateral, via
`review_option_order`'s real numbers) through `PushNotification` and
waits for explicit approval before `place_option_order`. Revisit once
it's run for a few real weeks — same graduation path the crypto/stock
bot followed before its own bounded auto-execution was authorized.

Hard rules: never modify `VOLTRAP_RISK_LIMITS`, `VOLTRAP_WATCHLIST`, or
`VOLTRAP_AUTO_EXECUTE` from within either Routine itself (same posture as
`RISK_LIMITS`/`WATCHLIST` above — these are deliberate, reviewed
decisions, never a side effect of an automated cycle); never place a
naked option (every put is cash-secured, every call is covered — no
exceptions, no margin leverage beyond what's already reserved as
collateral).

### VOLTRAP dry-run (paper — owner request, 2026-09-30)

**Separate from the real (unfunded, still gated) VOLTRAP above.** The
owner wants to see the mechanism work against real live market data
before committing real funds. This dry-run Routine is **read-only with
respect to money**: it never calls `place_option_order`, never touches
`VOLTRAP_RISK_LIMITS`/`VOLTRAP_WATCHLIST`/`VOLTRAP_AUTO_EXECUTE`, and
never changes the real go-live gate above. See
`voltrap_dryrun_2026-09-30.md` for the first run's full worked example
and findings.

Per firing (weekly, Monday shortly after open — matching the real
design's intended cadence; a mid-week entry was found live to leave too
little time for clean delta granularity near a 2-day expiration, see
the dry-run doc):

1. Use a **hypothetical portfolio value of $5,000** (owner-specified
   2026-09-30) wherever the real procedure above would read
   `get_portfolio` — do not touch the real account balance for this.
2. Reserved collateral ceiling = $5,000 × `VOLTRAP_RISK_LIMITS["max_voltrap_pct"]`
   (the real, already-confirmed 0.25) = $1,250.
3. Assume **2 concurrent positions** (not a documented VOLTRAP config
   value — a reasonable small-book default; max_collateral_per_contract
   = $1,250 / 2 = $625) unless the owner has since specified otherwise.
4. Run the real candidate screen (`run_scan`, scan_id
   `e3983260-740b-4a84-8369-54420cbeafdd`) → `voltrap_candidates.rank_by_voltrap_fit`
   with the hypothetical `max_collateral_per_contract` and the real
   `min_avg_options_volume`/`min_open_interest` from
   `VOLTRAP_RISK_LIMITS` → for the top 1-3 survivors: `get_option_chains`
   → `get_option_instruments` (nearest Friday with at least ~5+ calendar
   days out, not the very next Friday if that's only 1-2 days away) →
   `get_option_quotes` → `voltrap_candidates.pick_strike_by_delta` with
   the real `target_delta_min`/`target_delta_max` → `review_option_order`
   for real collateral/fee/probability numbers.
5. **Never call `place_option_order` or `place_equity_order` from this
   Routine under any circumstance** — this is the one hard line that
   makes it safe to run unattended. If a step would require placing an
   order to continue (it shouldn't), stop and log why instead.
6. Log the cycle's findings to a dated file
   `trading_agent/voltrap_dryrun_<date>.md` (same format as the first
   run) — ranked candidates, the walked-through strike pick(s), real
   collateral/premium/probability numbers, any new observations (e.g.
   if watchlist names now fit, if liquidity/IV shifted materially).
   Commit and push that file (same branch as this session).
7. Send one `PushNotification` (<200 chars) summarizing the cycle's top
   pick(s) and the headline numbers (strike, premium, collateral,
   chance of profit) — clearly labeled "VOLTRAP dry-run (paper)" so it's
   never confused with a real trading notification.

Hard rules (same posture as everywhere else in this file): never modify
`VOLTRAP_RISK_LIMITS`, `VOLTRAP_WATCHLIST`, `VOLTRAP_AUTO_EXECUTE`, or
`RISK_LIMITS`/`WATCHLIST`/`DRY_RUN` from within this Routine; never place
any real order of any kind; the $5,000/2-concurrent-position assumptions
live only in this Routine's own prompt and this PLAYBOOK section, never
in `config.py`, so there's no risk of them leaking into the real,
still-gated VOLTRAP path.
