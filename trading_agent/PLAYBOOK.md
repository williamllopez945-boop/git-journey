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
   a. Fetch recent closing-price history via the MCP tools (enough bars to
      cover at least `STRATEGY["long_window"] + 1` periods).
   b. Compute the signal with
      `sma_crossover_signal(prices, STRATEGY["short_window"], STRATEGY["long_window"])`
      from `trading_agent/strategy.py`.
   c. If the signal is `"hold"`, skip this asset.
   d. If `"buy"`: compute the order quantity with
      `RiskManager.position_size(portfolio_value, price, current_position_value)`.
      Skip if the resulting quantity is 0 (already at the per-asset cap).
   e. If `"sell"`: sell the full existing position in that asset (a
      crossover-down signal means exit, not short — this agent is
      long-only).
   f. Re-check `can_trade()` before every individual order — the daily cap
      applies across the whole cycle, not per asset.
   g. If `DRY_RUN` is `True`: do not call any order-placement MCP tool.
      Log what would have been ordered (asset, side, quantity, price) and
      move on.
      If `DRY_RUN` is `False`: place the order via the appropriate
      `robinhood-trading` MCP tool, then call
      `RiskManager.record_trade(asset, side, quantity, price)` with the
      actual filled quantity/price returned by the order call.

6. **Log the cycle summary.** For every asset: the signal, the action
   taken (or why it was skipped), and the resulting state
   (`trades_today`, `halted`).

## Hard rules

- Never place an order without going through steps 3–4 immediately before
  it (risk state can change mid-cycle if multiple orders are placed).
- Never bypass `DRY_RUN`. It only becomes `False` when the account owner
  edits `trading_agent/config.py` themselves after verifying the MCP
  connection is live and correct.
- Never increase `RISK_LIMITS` or `max_trades_per_day` from within a
  trading cycle. Those are owner-edited config, not runtime state.
- This agent is long-only: it buys and exits, it never shorts or uses
  margin/leverage.
