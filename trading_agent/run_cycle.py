"""Per-cycle helper: given this cycle's already-fetched scan output,
portfolio, and positions (each saved to a JSON file), prints circuit-
breaker/trade-cap state, watchlist classifications, and protective-exit
checks in one pass.

Added 2026-09-25 (owner request, token efficiency): the trading cycle
used to be run by hand-writing ~40-60 lines of Python per cycle (hardcoded
price/SMA dicts copied out of the scan response) in a Bash heredoc. This
script is that same logic - the same functions PLAYBOOK.md already calls
(scanner_signals.classify, exit_criteria.check_exit, RiskManager) - wired
together once instead of retyped every cycle.

Read-only and side-effect-light: it never calls the RobinHood MCP tools
or places orders (those still need the calling session's own tool calls),
and its only write is logging excellent_watch entries to CycleLogStore
(skippable with --no-log) - the same logging PLAYBOOK.md's cycle-logging
table already requires every cycle. Acting on a fresh_buy_cross/
fresh_sell_cross (cooldown check, concurrent-cap check, sizing, order
placement, RiskManager.record_trade, CycleLogStore logging of the
outcome) is still the calling session's job - this script only reports
what the signal was and what can_trade()/the circuit breaker currently
allow.

Usage:
    python3 trading_agent/run_cycle.py --asset-class crypto \\
        --scan-file scan.json --portfolio-file portfolio.json \\
        --positions-file positions.json

Each *-file accepts either the raw MCP tool response (e.g.
{"data": {"result": {"results": [...]}}}) or the already-unwrapped
payload - so a file saved automatically when a tool result overflows the
context window can be passed straight through with no manual unwrapping.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json

from trading_agent.config import RISK_LIMITS, WATCHLIST, STOCK_WATCHLIST
from trading_agent.cycle_log import CycleLogStore, LOG_PATH as DEFAULT_CYCLE_LOG_PATH
from trading_agent.exit_criteria import check_exit
from trading_agent.position_state import PositionStateStore, STATE_PATH as DEFAULT_POSITION_STATE_PATH
from trading_agent.risk_manager import RiskManager, STATE_PATH as DEFAULT_RISK_STATE_PATH
from trading_agent.scanner_signals import STATE_PATH as DEFAULT_SCANNER_STATE_PATH, classify


def _load_json(path):
    return json.loads(Path(path).read_text())


def _scan_rows(scan_json):
    if isinstance(scan_json, list):
        return scan_json
    return scan_json["data"]["result"]["results"]


def _portfolio_equity(portfolio_json):
    data = portfolio_json.get("data", portfolio_json)
    return float(data["total_value"])


def _crypto_avg_cost(position):
    """Mirrors get_crypto_positions' own weighted-average calculation
    across direct_quantity/direct_cost_basis. Returns None when
    direct_quantity sums to 0 (the known cost-basis gap PLAYBOOK.md's
    "Per-position exit rules" step 1 documents) - the caller falls back
    to cost_basis_fallback itself; this script does not attempt that
    fallback (it needs RiskManager.state["trade_log"], already available
    to the calling session without another file)."""
    total_qty = sum(float(cb["direct_quantity"]) for cb in position.get("cost_bases", []))
    total_cost = sum(float(cb["direct_cost_basis"]) for cb in position.get("cost_bases", []))
    if total_qty <= 0:
        return None
    return total_cost / total_qty


def _numeric_or_none(value):
    if value in ("", None):
        return None
    return float(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-class", choices=["crypto", "stock"], required=True)
    parser.add_argument("--scan-file", required=True)
    parser.add_argument("--portfolio-file", required=True)
    parser.add_argument("--positions-file", required=True)
    parser.add_argument("--no-log", action="store_true",
                         help="skip logging excellent_watch entries to CycleLogStore")
    parser.add_argument("--risk-state-path", default=str(DEFAULT_RISK_STATE_PATH),
                         help="override for tests - defaults to the real trading_agent/state.json")
    parser.add_argument("--scanner-state-path", default=str(DEFAULT_SCANNER_STATE_PATH),
                         help="override for tests - defaults to the real trading_agent/scanner_state.json")
    parser.add_argument("--position-state-path", default=str(DEFAULT_POSITION_STATE_PATH),
                         help="override for tests - defaults to the real trading_agent/position_state.json")
    parser.add_argument("--cycle-log-path", default=str(DEFAULT_CYCLE_LOG_PATH),
                         help="override for tests - defaults to the real trading_agent/cycle_log.json")
    args = parser.parse_args()

    watchlist = WATCHLIST if args.asset_class == "crypto" else STOCK_WATCHLIST

    equity = _portfolio_equity(_load_json(args.portfolio_file))
    rm = RiskManager(RISK_LIMITS, state_path=Path(args.risk_state_path))
    rm.start_of_day(equity)
    halted = rm.check_circuit_breaker(equity)
    can_trade = rm.can_trade()
    print(f"circuit_breaker_halted: {halted}")
    print(f"can_trade: {can_trade} (trades_today={rm.state['trades_today']}/{RISK_LIMITS['max_trades_per_day']})")

    rows = _scan_rows(_load_json(args.scan_file))
    by_ticker = {r["columns"].get("Symbol", r.get("ticker")): r["columns"] for r in rows if r.get("ticker") or r.get("columns", {}).get("Symbol")}

    pss = PositionStateStore(path=Path(args.position_state_path))
    log = CycleLogStore(path=Path(args.cycle_log_path))
    awesome_bar = RISK_LIMITS.get("awesome_trade_min_crossover_pct", 5.0)

    print("--- classifications (non-hold only) ---")
    for asset in watchlist:
        cols = by_ticker.get(asset)
        if cols is None:
            print(f"{asset}: not in this cycle's scan page, skipped")
            continue
        sma10 = float(cols["SMA 10 (1h)"])
        sma30 = float(cols["SMA 30 (1h)"])
        pct_change = _numeric_or_none(cols.get("% Change"))
        relative_volume = _numeric_or_none(cols.get("Relative volume"))
        cls, crossover_pct = classify(asset, sma10, sma30, pct_change, path=Path(args.scanner_state_path),
                                       relative_volume=relative_volume)
        if cls == "hold":
            continue
        tag = ""
        if cls == "fresh_buy_cross" and abs(crossover_pct) >= awesome_bar:
            tag = " [AWESOME - qualifies for the last 25% of aggregate budget]"
        print(f"{asset}: {cls} (crossover_pct={crossover_pct:.4f}%, pct_change={pct_change}, "
              f"relative_volume={relative_volume}){tag}")
        if cls == "excellent_watch" and not args.no_log:
            log.record(asset, "excellent_watch", crossover_pct, "excellent_watch")

    positions_json = _load_json(args.positions_file)
    positions_data = positions_json.get("data", positions_json)
    print("--- protective-exit checks (held positions only) ---")
    if args.asset_class == "crypto":
        for pos in positions_data.get("results", []):
            asset = pos["currency"]["code"]
            qty = float(pos.get("quantity_transferable", 0))
            if qty <= 0:
                continue
            cols = by_ticker.get(asset)
            if cols is None:
                print(f"{asset}: held but not in this cycle's scan page, exit check skipped")
                continue
            price = float(cols["Last"])
            avg_cost = _crypto_avg_cost(pos)
            if avg_cost is None:
                print(f"{asset}: zero cost basis from get_crypto_positions - use "
                      f"cost_basis_fallback.average_cost_basis_from_trade_log before skipping")
                continue
            took_profit = pss.took_profit(asset)
            reason, fraction = check_exit(current_price=price, avg_cost_basis=avg_cost,
                                           take_profit_already_taken=took_profit)
            pct = (price - avg_cost) / avg_cost * 100
            print(f"{asset} exit -> {reason} {fraction} pct_change={pct:.3f}% "
                  f"(price={price}, avg_cost={avg_cost:.6f})")
    else:
        for pos in positions_data.get("positions", []):
            asset = pos["symbol"]
            qty = float(pos.get("quantity", 0))
            if qty <= 0:
                continue
            cols = by_ticker.get(asset)
            if cols is None:
                print(f"{asset}: held but not in this cycle's scan page, exit check skipped")
                continue
            price = float(cols["Last"])
            avg_cost = float(pos["average_buy_price"])
            took_profit = pss.took_profit(asset)
            reason, fraction = check_exit(current_price=price, avg_cost_basis=avg_cost,
                                           take_profit_already_taken=took_profit)
            pct = (price - avg_cost) / avg_cost * 100
            print(f"{asset} exit -> {reason} {fraction} pct_change={pct:.3f}% "
                  f"(price={price}, avg_cost={avg_cost:.6f})")


if __name__ == "__main__":
    main()
