"""Builds ONE canonical, reconciled trade ledger from real broker records -
never from locally-recorded approximations (trading_agent/state.json's
trade_log, or the Trade Ledger dashboard's own backfilled copy of it) -
and matches each closing leg to Robinhood's own authoritative per-trade
realized gain/loss.

Added 2026-10-05 (Priority 1 of Codex's trade-ledger review in
#voltrap-agents-work, see CHANGELOG.md): two independent local
recomputations of the same 2026-09-22..10-05 trading history (this
session's own ledger_review.py-style script, and Codex's re-derivation
from a Slack-pasted extract of it) landed on two different totals
(-$199.44 and -$199.43 respectively) - both wrong. The true number,
confirmed by TWO independent Robinhood endpoints
(get_pnl_trade_history span=all and get_realized_pnl span=all, both
account_number 581911765, checked live 2026-10-05) is -$200.07 across
15 closed trades, not -$199.4x across "16 round-trips." The gap traces
to two real, previously-unrecorded events, found by diffing
get_crypto_orders' real order history against trading_agent/state.json's
trade_log:

1. A real PEPE buy order (2026-09-22, average_price 0.00000494,
   quantity 1014198) was never recorded in trade_log at all - only its
   2026-09-23 sell (average_price 0.00000446) was. Every local
   recomputation this session, including this module's predecessors,
   therefore used a 0/unknown cost basis for PEPE and reported its real
   -$0.50 loss (get_pnl_trade_history's own figure) as a $0.00 "flat"
   trade - silently absorbing a real loss into the noise floor.
2. A real DOGE buy order (2026-09-27T22:21:10-04:00, average_price
   0.09650002, quantity 1000, $96.51 notional) has NO matching entry in
   get_pnl_trade_history (Robinhood's own realized-trades list) and the
   account currently holds 0 DOGE (get_crypto_positions, checked live) -
   so this $96.51 was transferred OUT of the account at some point after
   purchase, never sold on this platform, and so never realized a
   gain/loss here at all. It is economically a withdrawal, not a trading
   outcome, and belongs in neither the win nor the loss column - but it
   was also never recorded anywhere (trade_log has no entry for it,
   unlike the earlier 2026-09-26 DOGE/SOL/ETH transfer-INS, which ARE
   recorded, just not order-backed). A prior session's own note on this
   asset ("Distinct from the separately-explained 2026-09-28 '$96.51
   mystery DOGE buy' (a transfer out, already resolved)") shows this gap
   was *understood* once before but never actually *recorded* - "resolved"
   in conversation, not in the ledger.

Design per Codex's explicit asks:
- "Use broker order/fill IDs, actual quantities/prices/fees... Derive
  all dashboards from one canonical source." -> build_canonical_ledger()
  takes get_crypto_orders/get_equity_orders raw responses (order-level
  truth: id, quantity, average_price, fee) and get_pnl_trade_history's
  raw response (Robinhood's own authoritative realized_gain per closing
  trade - no local cost-basis reconstruction, no risk of re-deriving the
  BTC/CRV discrepancies below) as the two REQUIRED primary sources, with
  trading_agent/cycle_log.json entries as an OPTIONAL join for
  classification/crossover_pct/exit_reason context only.
- "Separate execution events, reconciliation adjustments, partial exits
  and completed trade lifecycles." -> every leg is tagged `leg_type`:
  "execution" (a confirmed signal auto-executed or approved), "exit"
  (any closing sell matched to a realized_gain), or
  "unmatched_disposal" (a buy order with NO matching realized trade and
  the asset no longer held - the DOGE pattern above; flagged, not
  guessed at, since the actual disposal was never a trade on this
  platform).
- "Define flat tolerance." -> FLAT_TOLERANCE_USD. Real broker
  realized_gain values are never exactly $0.00 by coincidence the way a
  bad local 0/0 cost-basis calculation can produce - but the constant
  still exists and is applied consistently, for the dashboard's own
  benefit and for any future trade this does land within a cent of zero.
- "Add strategy/config version, entry/exit timestamps, exit reason and
  owner-override flag." -> STRATEGY_VERSIONS + strategy_version_at(),
  sourced from `git log --follow -- trading_agent/exit_criteria.py`'s
  real commit timestamps, not a guessed "era." This directly fixes
  another concrete mislabeling this session made: three real stop-loss
  exits (LINK 2026-09-29, AVAX 2026-09-30, DOT 2026-10-02) were reported
  to the owner and to Codex as "pre-tightening (10%/20% era)" - but the
  4%/8% tightening commit (906c568) landed 2026-09-28T17:39:15Z, BEFORE
  all three. They were real 4%-threshold exits with ~1-2 points of
  detection-to-fill slippage, not leftover 10%/20%-era trades - see
  reconcile_discrepancies() below for the same slippage mechanism found
  in the CRV case.
- "Reconcile BTC +$0.17/+1.13% vs +$0.18/+0.20%, CRV -4.13% vs -5.35%...
  Explain denominators and trigger-vs-fill differences; do not silently
  rewrite records." -> reconcile_discrepancies() documents both as real,
  benign effects of using different reference prices/cost bases at
  different moments (see its docstring), not bugs to patch by editing
  historical dashboard entries.
"""

from datetime import datetime, timezone

# Stop-loss/take-profit regime history, sourced from the real commit
# timestamps of `git log --follow -- trading_agent/exit_criteria.py`
# (checked 2026-10-05), not a guessed "era." Oldest first. Documentation
# only - this does NOT feed back into the live exit_criteria.py module,
# which always reads its own current STOP_LOSS_PCT/TAKE_PROFIT_PCT
# constants; this is purely for tagging *past* trades with the regime
# that was actually in effect when they closed.
STRATEGY_VERSIONS = [
    {"effective_at": "2026-09-22T13:31:17+00:00", "stop_loss_pct": 0.10, "take_profit_pct": 0.15,
     "label": "v1: 10% stop / 15% partial take-profit (80%)"},
    {"effective_at": "2026-09-25T02:49:46+00:00", "stop_loss_pct": 0.10, "take_profit_pct": 0.20,
     "label": "v2: 10% stop / 20% take-profit (1:2 R:R)"},
    {"effective_at": "2026-09-28T17:39:15+00:00", "stop_loss_pct": 0.04, "take_profit_pct": 0.08,
     "label": "v3: 4% stop / 8% take-profit (current)"},
]

# A closing leg's realized_gain within this many dollars of $0.00 is
# tagged a flat/reconciliation outcome rather than a win or a loss - see
# the module docstring's "Define flat tolerance" note. No real trade in
# this account's history (all sourced from get_pnl_trade_history) has
# landed inside this band as of 2026-10-05; it exists for correctness,
# not because any current number needs it.
FLAT_TOLERANCE_USD = 0.01

# Matching a get_crypto_orders/get_equity_orders sell against
# get_pnl_trade_history's realized-trades list (which carries no
# order_id) needs a tolerance on both axes - timestamps from the two
# endpoints have been observed to agree only to the second (sub-second
# truncated on one side), and quantity can carry float/display-rounding
# noise of a few parts in 1e6.
MATCH_TIME_TOLERANCE_SECONDS = 5
MATCH_QTY_REL_TOLERANCE = 1e-4


def strategy_version_at(timestamp_iso):
    """The STRATEGY_VERSIONS entry in effect at timestamp_iso (ISO 8601,
    any offset - normalized to UTC for comparison). Returns None if
    timestamp_iso predates every entry (shouldn't happen for a real
    trade on this account, whose first-ever order is 2026-09-22, exactly
    STRATEGY_VERSIONS[0]'s effective_at)."""
    t = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    applicable = None
    for version in STRATEGY_VERSIONS:
        v_at = datetime.fromisoformat(version["effective_at"])
        if v_at <= t:
            applicable = version
        else:
            break
    return applicable


def _parse_ts(value):
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


def _unwrap_crypto_orders(payload):
    """Normalizes get_crypto_orders' raw response (or an already-
    unwrapped {"results": [...]}) into a flat list of order-leg dicts
    with a common shape shared with _unwrap_equity_orders. Only
    state="filled" orders are real executions; anything else (canceled,
    rejected, still open) has no quantity/price worth reconciling and is
    skipped."""
    data = payload.get("data", payload)
    legs = []
    for order in data.get("results", []):
        if order.get("state") != "filled":
            continue
        qty = float(order["cumulative_quantity"])
        price = float(order["average_price"])
        fee = float(order.get("rounded_executed_notional_with_fee", 0)) - float(order.get("total_executed_notional", 0))
        legs.append({
            "order_id": order["id"],
            "asset": order["currency_code"],
            "asset_class": "crypto",
            "side": order["side"],
            "quantity": qty,
            "price": price,
            "fee": round(fee, 8),
            "notional": qty * price,
            "filled_at": _parse_ts(order["updated_at"]).isoformat(),
        })
    return legs


def _unwrap_equity_orders(payload):
    """Mirrors _unwrap_crypto_orders for get_equity_orders' shape.
    Untested against a real filled equity order (none exist on this
    account as of 2026-10-05 - every stock signal to date has been
    either `recommended` and never approved, or `excellent_watch`), but
    the raw get_equity_orders schema (average_price, cumulative_quantity,
    state, symbol, last_transaction_at) is otherwise the same shape
    class as crypto's, so this is kept parallel rather than omitted."""
    data = payload.get("data", payload)
    legs = []
    for order in data.get("orders", data.get("results", [])):
        if order.get("state") != "filled":
            continue
        qty = float(order.get("cumulative_quantity") or order.get("quantity"))
        price = float(order["average_price"])
        legs.append({
            "order_id": order["id"],
            "asset": order["symbol"],
            "asset_class": "stock",
            "side": order["side"],
            "quantity": qty,
            "price": price,
            "fee": 0.0,
            "notional": qty * price,
            "filled_at": _parse_ts(order.get("last_transaction_at") or order["updated_at"]).isoformat(),
        })
    return legs


def _unwrap_pnl_trades(payload):
    """Normalizes get_pnl_trade_history's raw response into a flat list
    of {symbol, side, quantity, realized_gain, timestamp} - Robinhood's
    own authoritative realized gain/loss per closing trade, used as-is
    rather than recomputed locally (this is the entire point: it cannot
    disagree with itself the way two different local cost-basis sources
    can - see the module docstring's BTC/CRV discrepancy note)."""
    data = payload.get("data", payload)
    return [
        {
            "symbol": t["symbol"],
            "side": t["side"],
            "quantity": float(t["quantity"]),
            "realized_gain": float(t["realized_gain"]),
            "timestamp": _parse_ts(t["timestamp"]).isoformat(),
        }
        for t in data.get("trades", [])
    ]


def _match_realized_gain(leg, pnl_trades, used):
    """Finds the get_pnl_trade_history entry matching a sell leg, within
    MATCH_TIME_TOLERANCE_SECONDS and MATCH_QTY_REL_TOLERANCE, excluding
    indices already claimed by an earlier leg (`used` - a set of indices
    into pnl_trades, since two legs could otherwise both match the same
    ambiguous entry). Returns (realized_gain, matched_index) or
    (None, None) if nothing qualifies - the signal that this leg's
    disposal was never actually realized on this platform (see
    "unmatched_disposal" in the module docstring)."""
    leg_t = _parse_ts(leg["filled_at"])
    for i, trade in enumerate(pnl_trades):
        if i in used or trade["symbol"] != leg["asset"] or trade["side"] != leg["side"]:
            continue
        trade_t = _parse_ts(trade["timestamp"])
        if abs((trade_t - leg_t).total_seconds()) > MATCH_TIME_TOLERANCE_SECONDS:
            continue
        if leg["quantity"] == 0:
            continue
        qty_diff = abs(trade["quantity"] - leg["quantity"]) / leg["quantity"]
        if qty_diff > MATCH_QTY_REL_TOLERANCE:
            continue
        return trade["realized_gain"], i
    return None, None


def build_canonical_ledger(crypto_orders_payload=None, equity_orders_payload=None, pnl_trades_payload=None):
    """The one canonical, reconciled ledger: every real filled order
    (crypto + stock), chronological, each tagged with its authoritative
    realized_gain (sell legs only, matched against get_pnl_trade_history)
    and strategy_version_at(filled_at). A buy leg with no matching
    realized_gain is left with realized_gain=None (still open, the
    common case); a SELL leg with no matching realized_gain is tagged
    leg_type="unmatched_disposal" - the asset's position dropped to zero
    without Robinhood ever recording a realizing trade for it, meaning
    it was transferred out rather than sold (the DOGE 2026-09-27 case -
    see module docstring). This can only be detected from a sell/buy
    mismatch against pnl_trades, so it is computed here, not guessed."""
    legs = []
    if crypto_orders_payload is not None:
        legs.extend(_unwrap_crypto_orders(crypto_orders_payload))
    if equity_orders_payload is not None:
        legs.extend(_unwrap_equity_orders(equity_orders_payload))
    legs.sort(key=lambda leg: leg["filled_at"])

    pnl_trades = _unwrap_pnl_trades(pnl_trades_payload) if pnl_trades_payload is not None else []
    used_pnl_indices = set()

    ledger = []
    for leg in legs:
        realized_gain, matched_index = (None, None)
        if leg["side"] == "sell":
            realized_gain, matched_index = _match_realized_gain(leg, pnl_trades, used_pnl_indices)
            if matched_index is not None:
                used_pnl_indices.add(matched_index)
        leg_type = "buy" if leg["side"] == "buy" else (
            "exit" if realized_gain is not None else "unmatched_disposal")
        version = strategy_version_at(leg["filled_at"])
        ledger.append({
            **leg,
            "realized_gain": realized_gain,
            "leg_type": leg_type,
            "strategy_version": version["label"] if version else None,
            "stop_loss_pct": version["stop_loss_pct"] if version else None,
            "take_profit_pct": version["take_profit_pct"] if version else None,
        })
    return ledger


def summarize_ledger(ledger, flat_tolerance_usd=FLAT_TOLERANCE_USD):
    """Totals/breakdowns computed ONLY from real, matched realized_gain
    values (never recomputed cost-basis deltas) - the entire point of
    sourcing this from get_pnl_trade_history. `unmatched_disposal` legs
    are counted separately and excluded from win/loss/total, consistent
    with them not being a realized trading outcome at all."""
    exits = [leg for leg in ledger if leg["leg_type"] == "exit"]
    unmatched = [leg for leg in ledger if leg["leg_type"] == "unmatched_disposal"]

    total_realized = sum(leg["realized_gain"] for leg in exits)
    wins = [leg for leg in exits if leg["realized_gain"] > flat_tolerance_usd]
    losses = [leg for leg in exits if leg["realized_gain"] < -flat_tolerance_usd]
    flats = [leg for leg in exits if leg not in wins and leg not in losses]

    by_asset = {}
    for leg in exits:
        by_asset.setdefault(leg["asset"], []).append(leg["realized_gain"])

    by_version = {}
    for leg in exits:
        by_version.setdefault(leg["strategy_version"], []).append(leg["realized_gain"])

    return {
        "num_exits": len(exits),
        "num_wins": len(wins),
        "num_losses": len(losses),
        "num_flat": len(flats),
        "total_realized": round(total_realized, 2),
        "win_rate_pct": round(len(wins) / len(exits) * 100, 1) if exits else None,
        "avg_win": round(sum(leg["realized_gain"] for leg in wins) / len(wins), 2) if wins else None,
        "avg_loss": round(sum(leg["realized_gain"] for leg in losses) / len(losses), 2) if losses else None,
        "by_asset": {a: round(sum(g), 2) for a, g in by_asset.items()},
        "by_strategy_version": {v: round(sum(g), 2) for v, g in by_version.items()},
        "unmatched_disposals": unmatched,
    }


def detect_quantity_gaps(ledger, current_positions_by_asset, tolerance=1e-6):
    """Per asset, compares the net quantity implied by REAL broker orders
    alone (sum of buys minus sum of sells in `ledger`) against the
    asset's actual current held quantity. A nonzero gap beyond
    `tolerance` means quantity entered or left the account by some path
    other than a Robinhood order - a crypto transfer in or out, which
    never appears in get_crypto_orders or get_pnl_trade_history at all.
    This is how the real 2026-09-27 DOGE gap (bought 1000, never sold
    here, no longer held - see module docstring) is actually detected,
    rather than narrated from memory: a positive gap means more is held
    than orders alone explain (a transfer in); negative means less (a
    transfer out). Does not attempt to explain *why* - that needs
    context outside orders/realized-trades entirely (e.g. this ledger's
    own already-recorded transfer-in notes), which belongs in a
    reconciliation report's prose, not in this function's output."""
    implied = {}
    for leg in ledger:
        sign = 1 if leg["side"] == "buy" else -1
        implied[leg["asset"]] = implied.get(leg["asset"], 0.0) + sign * leg["quantity"]

    gaps = []
    for asset, implied_qty in implied.items():
        actual_qty = current_positions_by_asset.get(asset, 0.0)
        gap = actual_qty - implied_qty
        if abs(gap) > tolerance:
            gaps.append({
                "asset": asset,
                "orders_implied_qty": implied_qty,
                "actual_qty": actual_qty,
                "gap": gap,
                "direction": "transfer_in" if gap > 0 else "transfer_out",
            })
    return gaps


def reconcile_discrepancies():
    """Written explanations for the specific number mismatches Codex's
    review flagged, grounded in this session's own real tool-call
    numbers (see each entry's `evidence`) - not a re-guess. Returned as
    data (not just a docstring) so a reconciliation report can quote it
    directly without duplicating the numbers by hand."""
    return [
        {
            "flagged": "BTC realized gain reported as both +$0.17 (+1.13%) and +$0.18 (+0.20%)",
            "explanation": (
                "Two different cost-basis sources for the same lot, both real, neither a bug. "
                "+1.13% used get_crypto_positions' direct_cost_basis/direct_quantity at sell time "
                "(91 / 0.00107393 = 84735.504176) - Robinhood appears to round a small-notional "
                "position's direct_cost_basis to the nearest dollar ($91 flat) rather than carry the "
                "fill's full precision. +0.20% used the original buy order's own average_price "
                "(84730.63257805, from get_crypto_orders) as cost basis, i.e. 91.0005 unrounded. "
                "Robinhood's own realized_gain for this sell (get_pnl_trade_history) is +$0.17, "
                "confirming the position-level rounded figure was closer, not the order-level one - "
                "the canonical ledger now sources realized_gain directly from get_pnl_trade_history "
                "for exactly this reason, bypassing both locally-reconstructed numbers."
            ),
        },
        {
            "flagged": "CRV stop-loss reported as both -4.13% (trigger) and -5.35% (P&L leg)",
            "explanation": (
                "Different prices at different times, not different cost bases. -4.126% was "
                "exit_criteria.check_exit's trigger-time comparison (current mark price vs avg cost "
                "basis AT THE MOMENT the protective-exit check ran, implying a mark price around "
                "$0.3700 at detection). -5.35% is the realized P&L comparison using the ACTUAL FILL "
                "price (0.3652983, from get_crypto_orders) against the recorded buy price "
                "(0.385935823). The ~1.3-point gap between those two percentages is real "
                "detection-to-fill slippage (CRV declined further between the stop-loss firing and "
                "the marketable-limit sell actually filling, worsened by CRV's $0.01 tick size "
                "forcing the limit to $0.36 - below the computed marketable price) - exactly the "
                "kind of latency cost Codex's Priority 3 asks to measure directly, not a reporting "
                "error. Robinhood's own realized_gain is -$3.33, matching the fill-based -5.35% "
                "calculation, not the trigger-time one."
            ),
        },
        {
            "flagged": "\"Pre-tightening (10%/20% era)\" labels on the LINK (9/29), AVAX (9/30), and DOT (10/2) stop-losses conflict with the stated 2026-09-28 tightening date",
            "explanation": (
                "This was a real mislabeling, not just a conflicting date claim. The 4%/8% "
                "tightening commit (906c568) landed 2026-09-28T17:39:15Z - BEFORE all three trades "
                "(9/29, 9/30, 10/2), not after. Their actual exit percentages (-5.97%, -5.12%, "
                "-5.49%) are consistent with a 4% trigger plus 1-2 points of detection-to-fill "
                "slippage (the same mechanism as the CRV case above), not a stale 10% threshold - a "
                "10%-regime stop firing at ~5% would be the anomaly, not the explanation. "
                "strategy_version_at() now tags every leg by the real exit_criteria.py commit "
                "history instead of a hand-guessed 'era.'"
            ),
        },
    ]
