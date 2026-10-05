import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.reconcile_ledger import (
    FLAT_TOLERANCE_USD,
    build_canonical_ledger,
    detect_quantity_gaps,
    reconcile_discrepancies,
    strategy_version_at,
    summarize_ledger,
)


def test_strategy_version_at_picks_the_regime_in_effect():
    # Before the first version ever existed.
    assert strategy_version_at("2026-09-20T00:00:00Z") is None
    # Exactly at v1's effective_at.
    assert strategy_version_at("2026-09-22T13:31:17Z")["stop_loss_pct"] == 0.10
    # Between v1 and v2.
    assert strategy_version_at("2026-09-24T00:00:00Z")["take_profit_pct"] == 0.15
    # The real LINK/AVAX/DOT trades Codex flagged as mislabeled
    # "pre-tightening" were all actually after the 4%/8% commit.
    v = strategy_version_at("2026-09-29T04:11:24+00:00")
    assert v["stop_loss_pct"] == 0.04
    assert v["take_profit_pct"] == 0.08
    v2 = strategy_version_at("2026-10-02T19:16:57+00:00")
    assert v2["stop_loss_pct"] == 0.04


def test_build_canonical_ledger_matches_sell_to_realized_gain():
    crypto_orders = {"data": {"results": [
        {"id": "buy-1", "currency_code": "BTC", "side": "buy", "state": "filled",
         "cumulative_quantity": "1.0", "average_price": "100.0",
         "total_executed_notional": "100.0", "rounded_executed_notional_with_fee": "100.0",
         "updated_at": "2026-09-30T15:13:55Z"},
        {"id": "sell-1", "currency_code": "BTC", "side": "sell", "state": "filled",
         "cumulative_quantity": "1.0", "average_price": "110.0",
         "total_executed_notional": "110.0", "rounded_executed_notional_with_fee": "110.0",
         "updated_at": "2026-10-05T20:11:22Z"},
    ]}}
    pnl_trades = {"data": {"trades": [
        {"timestamp": "2026-10-05T20:11:21Z", "symbol": "BTC", "side": "sell",
         "quantity": "1.0", "realized_gain": "10.0"},
    ]}}

    ledger = build_canonical_ledger(crypto_orders_payload=crypto_orders, pnl_trades_payload=pnl_trades)
    assert len(ledger) == 2
    buy_leg, sell_leg = ledger
    assert buy_leg["leg_type"] == "buy"
    assert buy_leg["realized_gain"] is None
    assert sell_leg["leg_type"] == "exit"
    assert sell_leg["realized_gain"] == 10.0
    assert sell_leg["strategy_version"] is not None


def test_build_canonical_ledger_flags_unmatched_disposal():
    # A sell with no matching get_pnl_trade_history entry within
    # tolerance - the disposal was never realized as a trade here.
    crypto_orders = {"data": {"results": [
        {"id": "sell-orphan", "currency_code": "XRP", "side": "sell", "state": "filled",
         "cumulative_quantity": "5.0", "average_price": "1.0",
         "total_executed_notional": "5.0", "rounded_executed_notional_with_fee": "5.0",
         "updated_at": "2026-09-27T10:00:00Z"},
    ]}}
    ledger = build_canonical_ledger(crypto_orders_payload=crypto_orders, pnl_trades_payload={"data": {"trades": []}})
    assert ledger[0]["leg_type"] == "unmatched_disposal"
    assert ledger[0]["realized_gain"] is None


def test_build_canonical_ledger_skips_non_filled_orders():
    crypto_orders = {"data": {"results": [
        {"id": "cancelled-1", "currency_code": "ETH", "side": "buy", "state": "canceled",
         "cumulative_quantity": "0", "average_price": "0",
         "total_executed_notional": "0", "rounded_executed_notional_with_fee": "0",
         "updated_at": "2026-09-27T10:00:00Z"},
    ]}}
    assert build_canonical_ledger(crypto_orders_payload=crypto_orders) == []


def test_summarize_ledger_uses_real_realized_gain_not_recomputed_cost_basis():
    ledger = [
        {"asset": "BTC", "side": "sell", "leg_type": "exit", "realized_gain": 0.17, "strategy_version": "v3"},
        {"asset": "CRV", "side": "sell", "leg_type": "exit", "realized_gain": -3.33, "strategy_version": "v3"},
        {"asset": "DOGE", "side": "sell", "leg_type": "exit", "realized_gain": -95.71, "strategy_version": "v3"},
        {"asset": "DOGE", "side": "buy", "leg_type": "unmatched_disposal", "realized_gain": None, "strategy_version": "v3"},
    ]
    summary = summarize_ledger(ledger)
    assert summary["num_exits"] == 3
    assert summary["num_wins"] == 1
    assert summary["num_losses"] == 2
    assert summary["total_realized"] == round(0.17 - 3.33 - 95.71, 2)
    assert len(summary["unmatched_disposals"]) == 1


def test_summarize_ledger_flat_tolerance_excludes_near_zero_from_win_loss():
    ledger = [
        {"asset": "HBAR", "side": "sell", "leg_type": "exit", "realized_gain": 0.005, "strategy_version": "v3"},
    ]
    summary = summarize_ledger(ledger, flat_tolerance_usd=FLAT_TOLERANCE_USD)
    assert summary["num_wins"] == 0
    assert summary["num_losses"] == 0
    assert summary["num_flat"] == 1


def test_detect_quantity_gaps_finds_transfer_out_not_explained_by_orders():
    # Mirrors the real 2026-09-27 DOGE case: a buy order exists, no sell
    # order exists for it, and the account no longer holds the asset -
    # the gap must be a transfer out, not a bug in this function's math.
    ledger = [
        {"asset": "DOGE", "side": "buy", "quantity": 1000.0},
    ]
    gaps = detect_quantity_gaps(ledger, current_positions_by_asset={})
    assert len(gaps) == 1
    assert gaps[0]["asset"] == "DOGE"
    assert gaps[0]["direction"] == "transfer_out"
    assert gaps[0]["gap"] == -1000.0


def test_detect_quantity_gaps_finds_transfer_in():
    # A sell order for more than any buy order on this account explains -
    # the extra units must have arrived by transfer in, not a purchase.
    ledger = [
        {"asset": "SOL", "side": "sell", "quantity": 1.66043295},
        {"asset": "SOL", "side": "buy", "quantity": 0.70931},
    ]
    gaps = detect_quantity_gaps(ledger, current_positions_by_asset={"SOL": 0.70931})
    assert len(gaps) == 1
    assert gaps[0]["asset"] == "SOL"
    assert gaps[0]["direction"] == "transfer_in"
    assert abs(gaps[0]["gap"] - 1.66043295) < 1e-6


def test_detect_quantity_gaps_no_gap_when_orders_fully_explain_position():
    ledger = [
        {"asset": "AVAX", "side": "buy", "quantity": 8.1531},
    ]
    gaps = detect_quantity_gaps(ledger, current_positions_by_asset={"AVAX": 8.1531})
    assert gaps == []


def test_reconcile_discrepancies_returns_the_three_flagged_items():
    items = reconcile_discrepancies()
    flagged_text = " ".join(item["flagged"] for item in items)
    assert "BTC" in flagged_text
    assert "CRV" in flagged_text
    assert "tightening" in flagged_text or "LINK" in flagged_text
    for item in items:
        assert item["explanation"]
