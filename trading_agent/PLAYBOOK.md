# Trading cycle playbook

This is the runbook an agent session must follow on each trading cycle. It
requires the `robinhood-trading` MCP server (configured in `.mcp.json`) to
be connected and authenticated with a live Robinhood account — that
connection has to be established by the account owner, it cannot be done
by an agent on their behalf.

Run this cycle on a fixed schedule (e.g. hourly). Each run is one full pass
over the watchlist.

## Steps, per cycle

1. **Load config.** Read `WATCHLIST`, `STRATEGY`, `RISK_LIMITS`, and
   `DRY_RUN` from `trading_agent/config.py`.

2. **Fetch account state.** Call the `robinhood-trading` MCP tools to get:
   - total portfolio equity (cash + holdings value)
   - current positions and their market value, for each asset in
     `WATCHLIST`
   - `open_position_count`: the number of `WATCHLIST` assets with
     `quantity_transferable > 0` from `get_crypto_positions` - recompute
     this once per cycle from the fetched positions, then keep it updated
     in-memory as positions open/close during the cycle (see step 5d).
   - `total_open_position_value`: sum of current mark-to-market value
     (quantity × mark price from `get_crypto_quotes`) across every
     `WATCHLIST` asset with an open position - recompute once per cycle,
     then keep it updated in-memory as positions open/close/partially
     exit during the cycle (add a fresh entry's notional when it
     executes; subtract a sell's proceeds-equivalent value when a
     position closes or partially exits). Feeds
     `RiskManager.position_size`'s aggregate cap (step 5d).

3. **Initialize risk state for the day.** Construct a `RiskManager` from
   `trading_agent/risk_manager.py` with `RISK_LIMITS`. Call
   `start_of_day(equity)` with the portfolio equity from step 2 (no-op if
   already recorded today). Call `check_circuit_breaker(equity)` — if it
   returns `True`, stop here for the rest of the cycle. Do not place any
   orders. Log that trading is halted for the day and why.

4. **Check the daily trade cap.** Call `can_trade()`. If `False` (cap
   already hit, or the circuit breaker just tripped), stop — do not place
   any orders this cycle.

5. **For each asset in `WATCHLIST`:**
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
      instead (pass no override). Compute the order quantity with
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
      says the notional is at/under `auto_execute_max_usd`, then notify
      the owner after the fact; otherwise present it as a recommendation
      and wait for explicit per-trade approval before calling
      `place_crypto_order`.

6. **Log the cycle summary.** For every asset: the signal, the action
   taken (or why it was skipped), and the resulting state
   (`trades_today`, `halted`).

## Scanner-based cycle (real signals, no 31-cycle warm-up)

Run this alongside steps 1-6 each cycle. It uses real historical data from
the start (the RobinHood scanner's server-side `closeAvg`), instead of
waiting for `price_history.py` to accumulate enough local bars.

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
     `RiskManager.position_size(..., total_open_position_value=total_open_position_value)`
     (quantity × price) and continue below; skip this asset if the
     resulting quantity is 0 (the `max_aggregate_position_pct` cap is
     already fully used — see the hard rule below). If the order
     executes, increment `open_position_count` and add its notional to
     `total_open_position_value` before moving to the next asset in this
     cycle.
   - `fresh_sell_cross`: no cooldown check (cooldown only blocks new
     entries, never exits). Compute the order notional with
     `RiskManager.position_size(...)` (quantity × price).
     **Auto-execution policy (owner-authorized 2026-09-22, see
     `config.py`):** if `DRY_RUN` is `False` and
     `RiskManager.can_auto_execute(order_notional_usd)` is `True` (i.e.
     the order is at or under `RISK_LIMITS["auto_execute_max_usd"]`),
     preview the order with `preview_crypto_order`, place it with
     `place_crypto_order`, call `RiskManager.record_trade(...)` with the
     actual filled quantity/price, and then **notify the account owner
     after the fact** with what was executed — do not ask first, this is
     the pre-authorized automatic path. If the order is larger than the
     threshold (or `DRY_RUN` is `True`), present it as a recommendation
     instead — asset, direction, current price, suggested size — and
     stop; do not call `place_crypto_order` until the owner explicitly
     approves that specific trade. Use `preview_crypto_order` to show
     them exact cost/fee first in that case too.
   - `excellent_watch`: not a strategy-confirmed signal, never
     auto-executed regardless of size. Alert the account
     owner with the asset, its crossover_pct/% change, and why it didn't
     meet the fresh-cross bar. Frame it as "worth discussing," not a
     recommendation — no preview, no suggested size, just the numbers and
     an open question.
   - `hold`: no action, no message needed (stay quiet unless the account
     owner asked for a status update).

## Per-position exit rules (stop-loss / take-profit)

Run this for every watchlist asset with an open position (`quantity_transferable > 0`
from `get_crypto_positions`), every cycle, independent of and in addition to
the SMA-based sell signal above.

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
   from `trading_agent/exit_criteria.py`. It returns one of:
   - `("stop_loss", 1.0)` — price is 10%+ below cost basis. Sell the
     **entire** position (`quantity_transferable`).
   - `("take_profit", 0.70)` — price is 15%+ above cost basis and profit
     hasn't been taken yet. Sell **70%** of `quantity_transferable`
     (round down to the pair's `min_order_quantity_increment` from
     `get_currency_pairs`), then call
     `PositionStateStore().mark_took_profit(asset)` so this doesn't
     re-trigger next cycle on the remaining 30%.
   - `(None, 0.0)` — no protective exit fires this cycle; the SMA
     death-cross check above still applies independently.
4. **These exits bypass `can_trade()`, the daily trade cap, the circuit
   breaker, and `auto_execute_max_usd`** — protective exits are never
   blocked by the gates that limit new risk-taking. The only gate that
   still applies is `DRY_RUN`: while `True`, log what would have been
   sold and take no action; while `False`, place the sell
   (`place_crypto_order`, side=sell) immediately, call
   `RiskManager.record_trade(...)`, and notify the account owner
   immediately with the reason (stop_loss/take_profit), quantity, price,
   and resulting P/L.
5. When a position's `quantity_transferable` reaches 0 (fully closed, by
   any combination of SMA exits and these protective exits), call both
   `PositionStateStore().reset(asset)` (clears the take-profit flag, so a
   future fresh entry starts without a stale one) AND
   `PositionStateStore().record_exit(asset)` (starts the whipsaw
   cooldown — `DEFAULT_COOLDOWN_HOURS`, 4h by default — blocking a new
   entry into this asset until it expires, even if a fresh buy signal
   fires in the meantime). Both calls are needed; they track independent
   state and `reset` does not clear the cooldown.

## Hard rules

- Never place an order without going through steps 3–4 immediately before
  it (risk state can change mid-cycle if multiple orders are placed).
- Never bypass `DRY_RUN`. It only becomes `False` when the account owner
  edits `trading_agent/config.py` themselves after verifying the MCP
  connection is live and correct.
- Never size a fresh entry without passing `total_open_position_value`
  (step 2) into `RiskManager.position_size(...)`. `RISK_LIMITS["max_aggregate_position_pct"]`
  (50%) is a hard cap on the combined mark-to-market value of every open
  position at once — it does not follow automatically from
  `max_position_pct` and `max_concurrent_positions` alone (20% x 5 = 100%,
  well over 50% if unchecked). It only ever limits or zeroes a fresh
  entry's size, never an exit, and applies identically on both the
  polling and scanner paths.
- Auto-execution is bounded and narrow, not a general license: only a
  `fresh_buy_cross` / `fresh_sell_cross` signal, only when `DRY_RUN` is
  `False`, only when `RiskManager.can_auto_execute(order_notional_usd)` is
  `True` (at/under `RISK_LIMITS["auto_execute_max_usd"]`, owner-set).
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
  still gates them same as everything else.
- This agent is long-only: it buys and exits, it never shorts or uses
  margin/leverage.
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
  path (`price_history.py`) has no volume field available — `get_crypto_quotes`
  doesn't return one and there's still no crypto historicals tool — so a
  polling-detected `"buy"` signal is never volume-gated; this is the
  mirror image of volatility-scaled sizing (step 5d), which is polling-only
  for the same underlying reason (the scanner has no raw price series to
  compute volatility from). It never blocks `fresh_sell_cross`.
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
| New entry above `auto_execute_max_usd`, awaiting approval | `"recommended"` | include the suggested `price`/`quantity`/`notional` |
| `fresh_buy_cross` skipped — in cooldown | `"blocked_cooldown"` | |
| `fresh_buy_cross` skipped — `max_concurrent_positions` reached | `"blocked_concurrent_cap"` | |
| `fresh_buy_cross` sized to 0 — `max_aggregate_position_pct` reached | `"blocked_aggregate_cap"` | |
| Confirmed cross downgraded to `"hold"` inside `classify()` by the volume gate | `"blocked_volume"` | log this even though `classify()` itself returned `"hold"`, not `fresh_buy_cross` — the whole point is capturing what got filtered out |
| `excellent_watch` | `"excellent_watch"` | |
| Stop-loss or take-profit fired | `"protective_exit"` | include `reason` (`"stop_loss"`/`"take_profit"`), `price`, `avg_cost_basis`, resulting P/L |

A plain `"hold"` with nothing else notable is not logged — this is an
event log of what needed a decision, not a full cycle trace.
