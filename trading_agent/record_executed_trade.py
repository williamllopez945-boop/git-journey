"""Record one already-executed trade (a real order that has already been
placed and filled) into RiskManager's trade_log/trades_today counter and
CycleLogStore's audit trail - in one call, same as run_cycle.py wires
together the read-only classification/circuit-breaker logic.

Added 2026-09-29 (owner request): run_cycle.py deliberately never places
orders or records trades - by its own docstring, that stays "the calling
session's job." That job used to mean hand-writing a RiskManager.record_trade
+ CycleLogStore.record call per execution, the same ad-hoc-script pattern
run_cycle.py itself replaced for the classification step on 2026-09-25.
This script is that same fix applied to the recording step: one small,
reviewed, fixed command whose own invocation pattern can be allow-listed,
instead of an inline script whose shape changes every time.

Usage (a fresh entry or a death-cross exit - counts toward trades_today):
    python3 trading_agent/record_executed_trade.py \\
        --asset AVAX --side buy --quantity 7.9511 --price 11.560665 \\
        --classification fresh_buy_cross --crossover-pct 1.7211 \\
        --notional 91.92 --order-id 6abb8587-7a90-4230-8127-ad18b8e59b4a

Usage (a protective stop-loss/take-profit exit - never consumes a daily
trade slot, per PLAYBOOK.md "Per-position exit rules"):
    python3 trading_agent/record_executed_trade.py \\
        --asset BTC --side sell --quantity 1.0 --price 90.0 --protective \\
        --action protective_exit --reason stop_loss --avg-cost-basis 100.0 \\
        --pnl-pct -10.0 --order-id <id>

classification/crossover-pct are optional (omit for a protective exit,
where PLAYBOOK.md's own convention already logs None/None - see
CycleLogStore's call sites in PLAYBOOK.md "Per-position exit rules").
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_agent.config import RISK_LIMITS
from trading_agent.cycle_log import CycleLogStore, LOG_PATH as DEFAULT_CYCLE_LOG_PATH
from trading_agent.risk_manager import RiskManager, STATE_PATH as DEFAULT_RISK_STATE_PATH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", required=True)
    parser.add_argument("--side", required=True, choices=["buy", "sell"])
    parser.add_argument("--quantity", required=True, type=float)
    parser.add_argument("--price", required=True, type=float,
                         help="actual fill price/cost basis per unit - not the order's requested/entered price")
    parser.add_argument("--protective", action="store_true",
                         help="stop-loss/take-profit exit - never consumes a daily trade slot (RiskManager.record_trade's protective=True)")
    parser.add_argument("--action", default="executed",
                         help="CycleLogStore action field - 'executed' (default), 'protective_exit', 'gate_floor', etc.")
    parser.add_argument("--classification", default=None,
                         help="CycleLogStore classification field - e.g. fresh_buy_cross. Omit for a protective exit (None/None is this project's own convention there).")
    parser.add_argument("--crossover-pct", default=None, type=float)
    parser.add_argument("--notional", default=None, type=float)
    parser.add_argument("--order-id", default=None)
    parser.add_argument("--reason", default=None, help="e.g. stop_loss, take_profit, gate_floor")
    parser.add_argument("--avg-cost-basis", default=None, type=float)
    parser.add_argument("--pnl-pct", default=None, type=float)
    parser.add_argument("--risk-state-path", default=str(DEFAULT_RISK_STATE_PATH),
                         help="override for tests - defaults to the real trading_agent/state.json")
    parser.add_argument("--cycle-log-path", default=str(DEFAULT_CYCLE_LOG_PATH),
                         help="override for tests - defaults to the real trading_agent/cycle_log.json")
    args = parser.parse_args()

    rm = RiskManager(RISK_LIMITS, state_path=Path(args.risk_state_path))
    before_trades_today = rm.state["trades_today"]
    rm.record_trade(args.asset, args.side, args.quantity, args.price, protective=args.protective)

    extra = {"price": args.price, "quantity": args.quantity}
    if args.notional is not None:
        extra["notional"] = args.notional
    if args.order_id is not None:
        extra["order_id"] = args.order_id
    if args.reason is not None:
        extra["reason"] = args.reason
    if args.avg_cost_basis is not None:
        extra["avg_cost_basis"] = args.avg_cost_basis
    if args.pnl_pct is not None:
        extra["pnl_pct"] = args.pnl_pct

    CycleLogStore(path=Path(args.cycle_log_path)).record(
        args.asset, args.classification, args.crossover_pct, args.action, **extra)

    print(f"recorded: {args.side} {args.quantity} {args.asset} @ {args.price} (protective={args.protective})")
    print(f"trades_today: {before_trades_today} -> {rm.state['trades_today']}")
    print(f"trade_log entries for {args.asset}: "
          f"{sum(1 for t in rm.state['trade_log'] if t['asset'] == args.asset)}")


if __name__ == "__main__":
    main()
