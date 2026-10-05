# Trade ledger reconciliation — 2026-10-05

Priority 1 of Codex's trade-ledger review (`#voltrap-agents-work`,
2026-10-05): "Produce a reconciled ledger... Reconcile BTC +$0.17/+1.13%
vs +$0.18/+0.20%, CRV -4.13% vs -5.35%, and stop-rule effective dates...
do not silently rewrite records." This report, plus the new
`trading_agent/reconcile_ledger.py` module it's generated from, is that
deliverable.

## Headline: the true numbers differ from every prior estimate, including both of mine and Codex's

Two independent Robinhood endpoints agree exactly, cross-checked live
2026-10-05 (account `581911765`):

| Source | Total realized | Closed trades |
|---|---|---|
| `get_pnl_trade_history` (span=all), summed by hand | **-$200.07** | **15** |
| `get_realized_pnl` (span=all), its own aggregate total | **-$200.07** | **15** |
| This session's own earlier estimate (Slack, before this review) | -$199.44 | "16 round-trips" |
| Codex's re-derivation from that same Slack extract | -$199.43 | 16 (9W/9L/2 flat split differently) |

Both local estimates were built from `trading_agent/state.json`'s
`trade_log` / the dashboard's backfilled copy of it - **not** from real
broker order history - and that local record turns out to be missing
two real orders (below). Both estimates are superseded by the broker
numbers in this report.

- **Win rate: 5/15 = 33.3%** (not 31.2%/5W-11L - the extra "loss" in
  every prior count was ETH's $0.00 dust reconciliation, which was never
  a real trade at all and shouldn't have been counted as a round-trip
  either way - see "What changed" below).
- **Avg win: $1.51. Avg loss: -$20.76.** Expectancy ratio 0.073 - even
  worse than the 0.08 figure already flagged as concerning, once PEPE's
  real -$0.50 (previously counted as $0.00) is included among the
  losses.
- By strategy version (`strategy_version_at()`, sourced from the real
  `exit_criteria.py` commit history, not a guessed "era" - see below):

  | Version | Effective from | Realized P&L |
  |---|---|---|
  | v1: 10%/15% | 2026-09-22 | -$0.50 (PEPE only) |
  | v2: 10%/20% | 2026-09-25 | -$183.04 |
  | v3: 4%/8% (current) | 2026-09-28T17:39:15Z | -$16.53 |

  The two large legacy losses (DOGE -$95.71, SOL -$78.20) both fall
  under v2, not v1 - consistent with what's already been said about them
  being pre-tightening, but now dated precisely rather than approximately.

## What changed and why (methodology)

`trading_agent/reconcile_ledger.py`'s `build_canonical_ledger()` sources
every leg from `get_crypto_orders`/`get_equity_orders` (real order id,
fill VWAP, fee, timestamp - never `get_crypto_positions`' aggregate
fields, which round differently, see the BTC reconciliation below) and
matches every sell to its realized gain/loss directly from
`get_pnl_trade_history` - Robinhood's own authoritative number, never
locally recomputed from a reconstructed cost basis. This is why it can't
reproduce either prior local estimate's error: there is no local cost
basis left to get wrong for a *closing* leg's dollar P&L.

Diffing the real order history (36 filled crypto orders total,
2026-09-22 through 2026-10-05, zero filled equity orders ever) against
`trading_agent/state.json`'s `trade_log` found two real orders that were
never recorded locally at all:

1. **A real PEPE buy** (2026-09-22T08:28:15-04:00, average_price
   0.00000494, quantity 1,014,198, order `6ab2745f...`). Only its
   2026-09-23 sell was ever in `trade_log`. Every local recomputation
   this session used a 0/unknown cost basis for PEPE as a result, and
   reported its real -$0.50 loss as a "$0.00 flat" trade - silently
   absorbing a real loss into the noise floor. This is also most of why
   my own win/loss split (16 round-trips, 2 "flat") differed from
   Codex's re-derivation of the same Slack extract (16, same 2 "flat")
   despite using the same input - PEPE's true delta and ETH's true $0.00
   look identical from a 0/0 cost basis, but only one of them actually
   is.
2. **A real DOGE buy** (2026-09-27T22:21:10-04:00, average_price
   0.09650002, quantity 1000, $96.51 notional, order `6ab9cf16...`) has
   **no matching entry in `get_pnl_trade_history`** and the account
   currently holds 0 DOGE (`get_crypto_positions`, checked live) - this
   $96.51 was transferred out of the account at some point after
   purchase and never sold on this platform, so it never realized a
   gain or loss here at all. A prior session's own note on this asset
   ("Distinct from the separately-explained 2026-09-28 '$96.51 mystery
   DOGE buy' (a transfer out, already resolved)") shows this was
   *understood* once before but never actually *recorded* anywhere -
   "resolved" in conversation, not in the ledger. It still isn't fully
   resolved today: the order is now recorded (see "Dashboard update"
   below), but exactly when/how it left the account is not re-derivable
   from Robinhood's order/trade-history tools alone - see
   `detect_quantity_gaps()`'s limitation note below.

Neither gap changes the authoritative -$200.07 total (that number came
from Robinhood directly, not from a recomputation this diff could have
corrupted) - but both explain why two different *local* recomputations
of the same underlying trades landed on two different wrong numbers,
and why "ETH $0.00" and "PEPE $0.00" looked like the same kind of entry
when they are not.

### `detect_quantity_gaps()`: a general check, run against the real account

Comparing each asset's broker-order-implied net quantity (sum of real
buys minus real sells) against its actual current holding
(`get_crypto_positions`) surfaces every quantity that moved by some path
other than a Robinhood order:

| Asset | Orders-implied qty | Actual qty | Gap | Direction |
|---|---|---|---|---|
| SOL | -0.9511 | 0.70931 | +1.6604 | transfer in |
| DOGE | -129.12 | 0 | +129.12 | transfer in |

Every other traded asset (BTC, AVAX, CRV, LINK, DOT, XLM, HBAR, BCH,
PEPE) shows **zero gap** - fully explained by real orders alone, no
transfers involved.

SOL's +1.6604 gap matches the known 2026-09-26 SOL transfer-in
(1.66043295, already recorded in `trade_log` as a reconciliation entry)
almost exactly. DOGE's +129.12 is the **net** of two separate real
events this function cannot itself tell apart (it only sees the final
balance, not the path): a 2026-09-26 transfer-in of 1129.12766834 DOGE
(already recorded) minus the 2026-09-27 ~1000 DOGE transfer-out
described above (newly identified, not yet independently confirmed by
any tool beyond "bought, never sold here, not currently held"). The
owner may want to check Robinhood's transfer/activity history directly
to confirm the exact 1000-DOGE transfer-out event if full certainty is
wanted; this report does not claim more precision than the tools available
support.

## The three specific discrepancies Codex flagged, reconciled

See `reconcile_discrepancies()` in `reconcile_ledger.py` for this
exact text, kept as data so a future report can quote it without
retyping the numbers:

**1. BTC: +$0.17/+1.13% vs +$0.18/+0.20%.** Two different cost-basis
sources for the same lot, both real, neither a bug. +1.13% used
`get_crypto_positions`' `direct_cost_basis`/`direct_quantity` at sell
time (91 / 0.00107393 = 84735.504176) - Robinhood appears to round a
small-notional position's `direct_cost_basis` to the nearest dollar
($91 flat) rather than carry the fill's full precision. +0.20% used the
original buy order's own `average_price` (84730.63257805, from
`get_crypto_orders`) as cost basis. Robinhood's own `realized_gain` for
this sell is +$0.17, confirming the position-level rounded figure was
closer - the canonical ledger now sources `realized_gain` directly from
`get_pnl_trade_history`, bypassing both locally-reconstructed numbers
for good.

**2. CRV: -4.13% (trigger) vs -5.35% (P&L leg).** Different prices at
different times, not different cost bases. -4.126% was
`exit_criteria.check_exit`'s trigger-time comparison (mark price vs avg
cost basis **at the moment the protective-exit check ran**, implying a
mark price around $0.3700 at detection). -5.35% is the realized P&L
comparison using the **actual fill price** (0.3652983) against the
recorded buy price (0.385935823) moments later. The ~1.3-point gap
between the two percentages is real detection-to-fill slippage - CRV
kept declining between the stop-loss firing and the marketable-limit
sell actually filling, worsened by CRV's $0.01 tick size forcing the
limit to $0.36 (below the computed marketable price) - exactly the kind
of latency cost Codex's Priority 3 asks to measure directly, not a
reporting error. Robinhood's own `realized_gain` is -$3.33, matching the
fill-based calculation.

**3. "Pre-tightening (10%/20% era)" labels on LINK (9/29), AVAX (9/30),
and DOT (10/2).** This was a real mislabeling on my part, not just a
conflicting date claim, as Codex suspected. The 4%/8% tightening commit
(`906c568`) landed **2026-09-28T17:39:15Z** - before all three trades
(9/29, 9/30, 10/2), not after. Their actual exit percentages (-5.97%,
-5.12%, -5.49%) are consistent with a 4% trigger plus 1-2 points of
detection-to-fill slippage (the same mechanism as CRV above), not a
stale 10% threshold - a 10%-regime stop firing at ~5% would itself be
the anomaly needing explanation, not a quiet confirmation of the old
regime. `strategy_version_at()` now tags every leg by the real
`exit_criteria.py` commit history instead of a hand-guessed "era," so
this specific mistake can't recur silently.

## Dashboard update

Two new documents added to the Trade Ledger artifact's `trades`
collection (ADDED, nothing edited or removed - per "do not silently
rewrite records"):

- The real PEPE buy (order `6ab2745f...`) - closes PEPE's cost-basis gap
  cleanly; the dashboard's own weighted-average-cost P&L calculation
  will now show PEPE's real ~-$0.50 instead of $0.00.
- The real DOGE buy (order `6ab9cf16...`), its note explicitly stating
  it was never sold on this platform and was most likely transferred out
  - so a reader of the raw data isn't left thinking it is either an
    unrecorded loss or a currently-held position.

**Known remaining limitation**: the dashboard's own JS (`computePnl`/
`summarizePoints` in `trade_ledger.html`) has no concept of a transfer
out - only buy/sell orders. Adding the DOGE buy without a matching
disposal leaves its "By asset" net-quantity rollup for DOGE showing a
small negative number (orders-implied net, not the real 0) rather than
reflecting the transfer. This does not affect any realized-P&L total
shown on the dashboard (`computePnl` only moves cumulative P&L on a
sell), only that one rollup display - flagged here rather than
papered over with a fabricated synthetic "transfer-out" leg at a price
that was never actually observed.

## Not yet done (future work, out of scope for this pass)

- Wiring the live dashboard's own P&L computation to call
  `reconcile_ledger.py` directly (fetch `get_crypto_orders` +
  `get_pnl_trade_history` live and derive everything from them) instead
  of reading its own `trades` collection's locally-maintained copy. The
  two new documents above close the *data* gap for now; closing the
  *architecture* gap (one true live source, not two parallel ones that
  can drift again) is a larger change to the artifact's own JS, left for
  a dedicated pass.
- Equity orders: the module supports them (`_unwrap_equity_orders`) but
  is untested against a real filled one, since none exist on this
  account yet (every stock signal to date has been `recommended` and
  never approved, or `excellent_watch`).
- Entry/exit holding-time, max-favorable/adverse-excursion, and
  detection-to-fill latency per trade (Codex's Priority 3) - the CRV and
  LINK/AVAX/DOT slippage findings above are a first, manual pass at
  exactly this, not yet a general per-trade computation.
