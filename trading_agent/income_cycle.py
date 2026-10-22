"""Per-cycle helper for the income sleeve (YieldMax-style weekly-
distribution basket ETFs - see PLAYBOOK.md's "Income sleeve" section).
Mirrors run_cycle.py's shape and CLI conventions exactly (same
--record-only/--record-trade-*/overridable-state-path pattern), wired to
this sleeve's own signal (income_signals.classify_entry - dip percentile
AND a real support-zone check, see income_signals.py), own exit rule
(income_exit.check_income_exit), and own isolated state
(income_state.py - income_risk_state.json/income_position_state.json/
income_cycle_log.json, never the main bot's state.json/
position_state.json/cycle_log.json).

2026-10-16 owner request: the ex-dividend timing gate (income_ex_dividend.py),
the liquidity/spread filter (income_candidates.filter_by_liquidity), and
the post-exit cooldown (PositionStateStore.in_cooldown) no longer block
entries here - a classify_entry signal is trusted on its own, sized
smaller per entry (INCOME_RISK_LIMITS) instead. Those modules/functions
still exist and are still tested; they're just not called from this
script anymore. See CHANGELOG.md for the real-money risk this accepts
(an entry can now fill on a thin/crossed market, right before an
ex-dividend markdown, or immediately after a stop-out).

Read-only and side-effect-light, same posture as run_cycle.py: never
calls the RobinHood MCP tools or places orders - the calling session's
Routine still does the real place_equity_order/review_equity_order call
and then re-invokes this script with --record-only to log the fill.

Usage (a normal cycle):
    python3 trading_agent/income_cycle.py \\
        --quotes-file quotes.json --historicals-file historicals.json \\
        --portfolio-file portfolio.json --positions-file positions.json

Usage (recording an already-placed fill, in a SEPARATE invocation after
the real order call - see run_cycle.py's own module docstring for why
this is split out: recording must never re-run classify_entry a second
time in the same cycle):
    python3 trading_agent/income_cycle.py --record-only \\
        --record-trade-asset YMAX --record-trade-side buy \\
        --record-trade-quantity 12.5 --record-trade-price 7.68 \\
        --record-trade-notional 96.00 --record-trade-order-id <uuid>

Each *-file accepts either the raw MCP tool response or the already-
unwrapped payload, same convention as run_cycle.py.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json

from trading_agent.income_exit import check_income_exit
from trading_agent.income_signals import classify_entry
from trading_agent.income_institutional_flow import volume_surge_confirmed
from trading_agent.cycle_log import CycleLogStore
from trading_agent.position_state import PositionStateStore
from trading_agent.risk_manager import RiskManager
from trading_agent.income_state import (
    RISK_STATE_PATH as DEFAULT_RISK_STATE_PATH,
    POSITION_STATE_PATH as DEFAULT_POSITION_STATE_PATH,
    CYCLE_LOG_PATH as DEFAULT_CYCLE_LOG_PATH,
)


def _load_json(path):
    return json.loads(Path(path).read_text())


def _portfolio_equity(portfolio_json):
    data = portfolio_json.get("data", portfolio_json)
    return float(data["total_value"])


def _quotes_by_symbol(quotes_json):
    data = quotes_json.get("data", quotes_json)
    by_symbol = {}
    for row in data["results"]:
        quote = row["quote"]
        by_symbol[quote["symbol"]] = quote
    return by_symbol


def _closes_by_symbol(historicals_json):
    data = historicals_json.get("data", historicals_json)
    by_symbol = {}
    for row in data["results"]:
        bars = [b for b in row["bars"] if not b.get("interpolated", False)]
        by_symbol[row["symbol"]] = [float(b["close_price"]) for b in bars]
    return by_symbol


def _volumes_by_symbol(historicals_json):
    data = historicals_json.get("data", historicals_json)
    by_symbol = {}
    for row in data["results"]:
        bars = [b for b in row["bars"] if not b.get("interpolated", False)]
        by_symbol[row["symbol"]] = [float(b.get("volume", 0.0)) for b in bars]
    return by_symbol


def _positions_by_symbol(positions_json):
    data = positions_json.get("data", positions_json)
    by_symbol = {}
    for pos in data.get("positions", []):
        qty = float(pos.get("quantity", 0))
        if qty > 0:
            by_symbol[pos["symbol"]] = pos
    return by_symbol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quotes-file",
                         help="required unless --record-only (get_equity_quotes' raw response "
                              "for INCOME_WATCHLIST - supplies each symbol's live price for sizing "
                              "and marking held positions)")
    parser.add_argument("--historicals-file",
                         help="required unless --record-only (get_equity_historicals' raw response, "
                              "interval=day, for INCOME_WATCHLIST - real bars only, interpolated "
                              "padding is dropped)")
    parser.add_argument("--portfolio-file",
                         help="required unless --record-only")
    parser.add_argument("--positions-file",
                         help="required unless --record-only (get_equity_positions' raw response)")
    parser.add_argument("--no-log", action="store_true",
                         help="skip logging blocked/skip reasons to the income cycle log")
    parser.add_argument("--record-only", action="store_true",
                         help="only record an already-executed trade (--record-trade-* flags) - "
                              "skips the signal/exit checks entirely, so recording a fill never "
                              "re-runs classify_entry a second time this cycle.")
    parser.add_argument("--risk-state-path", default=str(DEFAULT_RISK_STATE_PATH),
                         help="override for tests - defaults to the real income_risk_state.json")
    parser.add_argument("--position-state-path", default=str(DEFAULT_POSITION_STATE_PATH),
                         help="override for tests - defaults to the real income_position_state.json")
    parser.add_argument("--cycle-log-path", default=str(DEFAULT_CYCLE_LOG_PATH),
                         help="override for tests - defaults to the real income_cycle_log.json")
    parser.add_argument("--record-trade-asset", default=None)
    parser.add_argument("--record-trade-side", choices=["buy", "sell"], default=None)
    parser.add_argument("--record-trade-quantity", type=float, default=None)
    parser.add_argument("--record-trade-price", type=float, default=None,
                         help="actual fill price, not the order's requested price")
    parser.add_argument("--record-trade-protective", action="store_true",
                         help="stop-loss/trim exit - does not consume a daily trade slot")
    parser.add_argument("--record-trade-action", default="executed")
    parser.add_argument("--record-trade-reason", default=None,
                         help="dip_buy / stop_loss / trim")
    parser.add_argument("--record-trade-notional", type=float, default=None)
    parser.add_argument("--record-trade-order-id", default=None)
    args = parser.parse_args()

    if args.record_only and not args.record_trade_asset:
        parser.error("--record-only has nothing to do without --record-trade-asset (and friends)")
    if not args.record_only:
        missing = [name for name in ("quotes_file", "historicals_file",
                                      "portfolio_file", "positions_file")
                   if getattr(args, name) is None]
        if missing:
            parser.error(f"--{missing[0].replace('_', '-')} is required unless --record-only")

    from trading_agent.config import (
        INCOME_WATCHLIST,
        INCOME_RISK_LIMITS,
        INCOME_INSTITUTIONAL_FLOW_GATED_SYMBOLS,
    )

    rm = RiskManager(INCOME_RISK_LIMITS, state_path=Path(args.risk_state_path))
    log = CycleLogStore(path=Path(args.cycle_log_path))
    pss = PositionStateStore(path=Path(args.position_state_path))

    if not args.record_only:
        equity = _portfolio_equity(_load_json(args.portfolio_file))
        rm.start_of_day(equity)
        halted = rm.check_circuit_breaker(equity)
        print(f"circuit_breaker_halted: {halted}")
        print(f"can_trade: {rm.can_trade()} "
              f"(trades_today={rm.state['trades_today']}/{INCOME_RISK_LIMITS['max_trades_per_day']})")

        quotes = _quotes_by_symbol(_load_json(args.quotes_file))
        closes_by_symbol = _closes_by_symbol(_load_json(args.historicals_file))
        volumes_by_symbol = _volumes_by_symbol(_load_json(args.historicals_file))
        positions = _positions_by_symbol(_load_json(args.positions_file))

        open_position_count = len(positions)
        total_open_position_value = 0.0
        for symbol, pos in positions.items():
            quote = quotes.get(symbol)
            if quote is not None:
                total_open_position_value += float(pos["quantity"]) * float(quote["last_trade_price"])

        print("--- protective exits (held positions only) ---")
        for symbol, pos in positions.items():
            quote = quotes.get(symbol)
            if quote is None:
                print(f"{symbol}: held but no quote this cycle, exit check skipped")
                continue
            price = float(quote["last_trade_price"])
            avg_cost = float(pos["average_buy_price"])
            trim_taken = pss.took_profit(symbol)
            reason, fraction = check_income_exit(price, avg_cost, trim_taken)
            pct = (price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0.0
            print(f"{symbol} exit -> {reason} {fraction} pct_change={pct:.3f}% "
                  f"(price={price}, avg_cost={avg_cost:.4f})")

        print("--- entry candidates (not currently held) ---")
        for symbol in INCOME_WATCHLIST:
            if symbol in positions:
                continue

            closes = closes_by_symbol.get(symbol)
            if not closes:
                print(f"{symbol}: no historicals this cycle, skipped")
                continue
            signal = classify_entry(closes)
            if signal != "dip_buy":
                print(f"{symbol}: hold (no dip+support signal)")
                continue

            if symbol in INCOME_INSTITUTIONAL_FLOW_GATED_SYMBOLS:
                volumes = volumes_by_symbol.get(symbol)
                if not volumes or not volume_surge_confirmed(volumes):
                    print(f"{symbol}: dip_buy signal but blocked_no_volume_surge "
                          f"(institutional-flow gate, see "
                          f"backtest_2026-10-13_institutional_flow_income_sleeve.md)")
                    if not args.no_log:
                        log.record(symbol, "dip_buy", None, "blocked_no_volume_surge")
                    continue

            if not rm.can_trade():
                print(f"{symbol}: dip_buy signal but blocked_cannot_trade (halted or daily cap reached)")
                continue
            if not rm.can_open_new_position(open_position_count):
                print(f"{symbol}: dip_buy signal but blocked_concurrent_cap")
                if not args.no_log:
                    log.record(symbol, "dip_buy", None, "blocked_concurrent_cap")
                continue

            price = float(quotes[symbol]["last_trade_price"])
            qty = rm.position_size(equity, price, 0.0, total_open_position_value=total_open_position_value)
            notional = qty * price
            if notional <= 0:
                print(f"{symbol}: dip_buy signal but blocked_aggregate_cap")
                if not args.no_log:
                    log.record(symbol, "dip_buy", None, "blocked_aggregate_cap")
                continue
            if not rm.can_auto_execute(notional, equity):
                print(f"{symbol}: dip_buy signal, sized ${notional:.2f}, but over "
                      f"auto_execute_max_pct - present as a recommendation instead")
                continue

            print(f"{symbol}: ENTER dip_buy, qty={qty:.4f} notional=${notional:.2f} @ ${price:.2f}")

    if args.record_trade_asset:
        rm.record_trade(args.record_trade_asset, args.record_trade_side,
                         args.record_trade_quantity, args.record_trade_price,
                         protective=args.record_trade_protective)
        if args.record_trade_side == "buy":
            pass  # a fresh entry does not touch took_profit/cooldown state
        elif args.record_trade_reason == "stop_loss":
            pss.reset(args.record_trade_asset)
            pss.record_exit(args.record_trade_asset)
        elif args.record_trade_reason == "trim":
            pss.mark_took_profit(args.record_trade_asset)

        extra = {"price": args.record_trade_price, "quantity": args.record_trade_quantity}
        if args.record_trade_notional is not None:
            extra["notional"] = args.record_trade_notional
        if args.record_trade_order_id is not None:
            extra["order_id"] = args.record_trade_order_id
        log.record(args.record_trade_asset, args.record_trade_reason or "dip_buy",
                   None, args.record_trade_action, **extra)
        print(f"recorded: {args.record_trade_side} {args.record_trade_quantity} "
              f"{args.record_trade_asset} @ {args.record_trade_price} "
              f"(trades_today now {rm.state['trades_today']})")


if __name__ == "__main__":
    main()
