# All-time P&L reconciliation, 2026-09-29

Owner asked "are we down $185?" after a session of hourly cycles. Local
`daily_logs/*.md` running totals never added up to that, so this
reconciles against Robinhood's own authoritative records
(`get_realized_pnl`, `get_pnl_trade_history`, `span=all`) rather than
local bookkeeping.

## The real number

**Total realized P&L, all-time: -$189.10** (-20.6% of deployed capital,
10 closing trades, `get_realized_pnl(span=all)`). The account is
currently 100% cash ($459.36) with zero open positions, so there is no
unrealized P&L on top of this - it is the complete picture, not a
snapshot.

This slightly exceeds the owner's "$185" estimate, not falls short of
it. The gap between this and what daily reporting had been showing is
almost entirely two already-flagged, never-corrected `trade_log`
cost-basis entries.

## Per-trade comparison: Robinhood's real record vs local `trade_log`

`get_pnl_trade_history(span=all)` returns every closing trade this
account has ever had (the earliest realized-gain bucket with any
activity starts 2026-08-30, before this project's own history begins on
2026-09-23, so "all" and "this project" are effectively the same
window):

| Date | Asset | Real realized (Robinhood) | Local `trade_log` implied | Gap |
|---|---|---:|---:|---:|
| 2026-09-28 | **DOGE** | **-$95.71** | -$2.99 | **-$92.72** |
| 2026-09-27 | **SOL** | **-$78.20** | -$17.51 | **-$60.69** |
| 2026-09-29 | LINK (stop-loss) | -$5.56 | -$5.56 | $0 |
| 2026-09-28 | AVAX | -$6.54 | -$6.52 | ~$0 (rounding) |
| 2026-09-28 | CRV | -$5.22 | -$5.21 | ~$0 (rounding) |
| 2026-09-28 | XLM | -$2.81 | -$2.80 | ~$0 (rounding) |
| 2026-09-23 | PEPE | -$0.50 | not present | -$0.50 |
| 2026-09-27 | DOT | +$2.67 | +$2.68 | ~$0 (rounding) |
| 2026-09-27 | LINK | +$2.74 | +$2.75 | ~$0 (rounding) |
| 2026-09-26 | HBAR | +$0.03 | +$0.04 | ~$0 (rounding) |
| **Total** | | **-$189.10** | ~-$35.94 | **-$153.16** |

(PEPE's -$0.50 was correctly reconciled same-day in
`daily_logs/2026-09-23.md` - "matching Robinhood's own records exactly,
no discrepancy found" - it simply predates `state.json`'s `trade_log`,
which starts 2026-09-23T15:10:58, sixteen seconds after that trade. Not
a new finding, just excluded from the local sum above for that reason.)

## Root cause: two transfer-in entries never got a real cost basis

Both SOL and DOGE entered this account on 2026-09-26 as external
transfers-in (no matching order in `get_crypto_orders`, `cost_bases`
0/0 on `get_crypto_positions` - the standard transfer-in signature per
that tool's own guidance). Since a transfer has no fill price, the
`trade_log` reconciliation entries recorded at the time used
placeholder cost bases:

- **DOGE**: a mark-price snapshot at detection time (0.098310635/unit) -
  explicitly logged as "NOT a known real entry price" at the time, after
  the owner's stated $1.10/unit was rejected as impossible (exceeds
  DOGE's real all-time high, ~$0.74) and the owner "confirmed
  2026-09-26 to drop pursuing the real figure."
- **SOL**: the owner's stated $130.00/unit, taken at face value on
  2026-09-26.

Both positions have since fully closed (DOGE sold 2026-09-28, SOL sold
2026-09-27), and Robinhood's own realized-P&L figures on those closing
sales are the authoritative record of what the true cost basis actually
was - regardless of what placeholder was used along the way. Neither
placeholder was ever reconciled back against that real figure once it
became available:

- **SOL was already flagged** in `daily_logs/2026-09-27.md`: "Robinhood's
  own realized loss on today's SOL sale was -$78.23... not the -$17.51
  the $130.00/unit reconciliation figure implies." The finding was
  documented but the `trade_log` entry itself was never corrected -
  every daily review since has been computing off the wrong number.
- **DOGE was never connected to this pattern at all.** The
  `daily_logs/2026-09-28.md` review flagged a *different*, unrelated
  DOGE discrepancy that day (see "Not the same issue" below) and never
  cross-checked the sell itself against `get_pnl_trade_history`.

## Corrected cost basis (derived from the real closing-sale realized gain)

Same method as the existing 2026-09-28 audit's LINK/SOL/CRV/AVAX
VWAP-price corrections (`CHANGELOG.md`, "Audit finding: 5 trade_log
entries had the wrong fill price"): back out the true average cost from
`realized_gain = (sell_price - avg_cost) * qty` using Robinhood's own
reported `sell_price` and `realized_gain`.

**DOGE** (`get_pnl_trade_history`: qty=1178.76, price=0.095787,
realized_gain=-$95.71):
- Total implied cost basis: 1178.76 x 0.095787 + 95.71 = $208.62
- The 2026-09-27 buy leg (49.64 @ 0.09873026) is already a real,
  VWAP-corrected fill (2026-09-28 audit) - not touched.
- Remaining 2026-09-26 transfer-in leg (1129.12766834 units): implied
  cost = $208.62 - $4.90 = $203.72 -> **$0.180421/unit** (was
  0.098310635)

**SOL** (`get_pnl_trade_history`: qty=1.66043295, price=119.45380832 -
matches the local entry's already-VWAP-corrected sell price to display
precision - realized_gain=-$78.20):
- avg_cost = 119.45380832 - (-78.20 / 1.66043295) = **$166.549955/unit**
  (was 130.0) - confirms and refines the 2026-09-27 daily review's own
  "~$166.54/unit" estimate almost exactly.

## Not the same issue: the $96.51 "mystery DOGE buy"

`daily_logs/2026-09-28.md` separately flagged an unresolved
discrepancy: a filled DOGE **buy** (1000 units, $96.51 notional, order
id `6ab9cf16`, 2026-09-27 22:21 ET) with no `trade_log` entry and no
DOGE currently held. That is a *different* event from the DOGE **sell**
this doc corrects (1178.76 units, 2026-09-28T01:10 UTC, ~1 hour
*before* the mystery buy, not after) - different quantity, different
price, different side. The owner separately explained the mystery buy
as a manual transfer outside the agent's own workflow, which this doc
does not reopen or re-litigate. The two figures (-$95.71 realized loss
vs $96.51 notional) are similar-sized by coincidence (DOGE was trading
in the same ~$0.09-0.10 band both times), not because they are the same
trade.

## Status: correction pending

**The `state.json` edit itself was blocked by this session's own
permission system** ("Modify Shared Resources" - `state.json` is a
shared, multi-agent runtime file per `COLLABORATION.md`) before it could
be applied, even though this is a same-session, owner-approved
correction to a value this same session already generates and consumes
live. The derived values above (DOGE transfer-in leg -> 0.180421/unit,
SOL transfer-in leg -> 166.549955/unit) are ready to apply - either by
the owner running the correction directly, or by re-authorizing this
specific write (e.g. a scoped Bash permission rule for
`trading_agent/state.json`) so a future turn can finish it the same way
the 2026-09-28 audit's five corrections were applied.

Until applied, this doc is the authoritative reconciliation - not
`state.json`'s DOGE/SOL buy entries, and not the day-by-day dollar
figures already printed in `daily_logs/2026-09-27.md` and
`daily_logs/2026-09-28.md`, both of which predate this finding.

## What this doesn't change

- No open position depends on either corrected cost basis (both fully
  closed).
- No `RISK_LIMITS`, `DRY_RUN`, `WATCHLIST`, `STOCK_WATCHLIST`, or
  strategy parameter changes as a result of this doc - purely a
  historical bookkeeping correction.
- The true all-time realized loss, -$189.10, was already true before
  this correction - `state.json` was under-reporting it, not causing
  it. Applying the correction changes what future reviews *show*, not
  what already happened.
