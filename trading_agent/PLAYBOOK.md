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
      `sma_crossover_signal(prices, STRATEGY["short_window"], STRATEGY["long_window"])`
      from `trading_agent/strategy.py`. This returns `"hold"` until at
      least `long_window + 1` cycles have run and recorded a bar — that's
      expected while history is still accumulating, not an error.
   c. If the signal is `"hold"`, skip this asset.
   d. If `"buy"`: compute the order quantity with
      `RiskManager.position_size(portfolio_value, price, current_position_value)`.
      Skip if the resulting quantity is 0 (already at the per-asset cap).
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
   `SMA 10 (1h)`, `SMA 30 (1h)`, and `% Change` for every crypto pair
   Robinhood offers.
2. Filter the results to `WATCHLIST` from `config.py`.
3. For each watchlist asset, call
   `scanner_signals.classify(asset, sma10, sma30, pct_change)` from
   `trading_agent/scanner_signals.py`.
4. Act on the classification:
   - `fresh_buy_cross` / `fresh_sell_cross`: this is a genuine strategy
     signal. Compute the order notional with
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
2. Check whether take-profit was already taken for this asset:
   `PositionStateStore().took_profit(asset)` from
   `trading_agent/position_state.py`.
3. Call `exit_criteria.check_exit(current_price, avg_cost_basis, took_profit)`
   from `trading_agent/exit_criteria.py`. It returns one of:
   - `("stop_loss", 1.0)` — price is 10%+ below cost basis. Sell the
     **entire** position (`quantity_transferable`).
   - `("take_profit", 0.80)` — price is 15%+ above cost basis and profit
     hasn't been taken yet. Sell **80%** of `quantity_transferable`
     (round down to the pair's `min_order_quantity_increment` from
     `get_currency_pairs`), then call
     `PositionStateStore().mark_took_profit(asset)` so this doesn't
     re-trigger next cycle on the remaining 20%.
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
   any combination of SMA exits and these protective exits), call
   `PositionStateStore().reset(asset)` so a future fresh entry in that
   asset starts without a stale take-profit flag.

## Hard rules

- Never place an order without going through steps 3–4 immediately before
  it (risk state can change mid-cycle if multiple orders are placed).
- Never bypass `DRY_RUN`. It only becomes `False` when the account owner
  edits `trading_agent/config.py` themselves after verifying the MCP
  connection is live and correct.
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
