# Autonomous crypto trading agent

A rule-based agent that trades BTC, ETH, SOL, and DOGE on Robinhood with no
per-trade human approval, using an SMA-crossover strategy and conservative
risk limits. Built on top of the `robinhood-trading` MCP server registered
in `.mcp.json` at the repo root.

## What's here

| File | Purpose |
|---|---|
| `config.py` | Watchlist, strategy parameters, risk limits, `DRY_RUN` switch |
| `strategy.py` | SMA crossover signal logic (pure computation, no network) |
| `risk_manager.py` | Position sizing, daily loss circuit breaker, daily trade cap — persisted to `state.json` |
| `PLAYBOOK.md` | Step-by-step runbook an MCP-connected agent session follows each cycle |
| `tests/` | Unit tests for the strategy and risk logic |

## Strategy

SMA crossover, long-only: short SMA (10 periods) crossing above the long
SMA (30 periods) is a buy signal; crossing below is a sell/exit signal.
No shorting, no margin.

## Risk limits (conservative, as configured)

- Max 5% of portfolio value per asset
- Daily circuit breaker: all trading halts for the rest of the UTC day
  once portfolio drawdown from that day's starting equity hits 3%
- Max 3 trades per day, combined across all four assets

These are enforced by `RiskManager`, whose state persists in
`trading_agent/state.json` (gitignored — it holds live account/trade data
and must never be committed).

## What this agent does NOT do for you

- **It does not connect to your Robinhood account.** The
  `robinhood-trading` MCP server needs to be authenticated by you —
  that's an OAuth/login step tied to your identity that no agent can do on
  your behalf. Add and authenticate it in an environment where you control
  the connector.
- **It has not executed, and cannot execute, any real trade from this
  session.** This cloud session's MCP connections don't include
  `robinhood-trading`, so none of this code has touched your real account.
- **It ships with `DRY_RUN = True`.** Even once the MCP is connected, the
  agent will only log simulated orders until you deliberately edit
  `config.py` and set `DRY_RUN = False`. This is a standard safety default
  for trading bots, independent of the "no per-trade approval" execution
  mode — it's a single, explicit, reviewable line you control, not a
  per-trade gate.

## Going live (steps you have to do yourself)

1. Connect and authenticate the `robinhood-trading` MCP server in an
   agent environment you control.
2. Run the agent in dry-run mode for at least a few cycles and read the
   logs — confirm the signals and position sizing look right against your
   actual account balance.
3. Edit `config.py`, set `DRY_RUN = False`.
4. Set up a recurring schedule (e.g. an hourly cron trigger) that runs the
   `PLAYBOOK.md` cycle in that MCP-connected environment.

## Risk disclosure

This trades real money with no human approval per trade once
`DRY_RUN = False`. Crypto markets are volatile; the risk limits here
reduce but do not eliminate the chance of losses, and a bug in the
strategy or a stale/incorrect price feed can still lose money within
those limits (up to the daily loss cap) before the circuit breaker halts
trading. Review the code yourself before enabling live trading.
