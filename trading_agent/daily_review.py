"""Assembles the end-of-day after-action review from cycle_log.py's
signal/gate history and RiskManager's trade_log - the mechanical part of
"what happened today" computed from real recorded data, not an LLM
improvising from memory each night. The qualitative "here's what to
consider changing" part still belongs to whoever (or whatever) reads
this summary, the same way this session has treated every other
backtest write-up: real numbers first, judgment on top of them.
"""


def summarize_day(cycle_entries, trade_log_entries, date_iso):
    """cycle_entries: CycleLogStore.entries_for_date(date_iso) - every
    non-hold classification and gate outcome that day.

    trade_log_entries: RiskManager.state["trade_log"], already filtered
    or not - this function filters to date_iso itself so callers can
    pass the whole log.

    Returns a plain dict of counts and the raw matching entries, not
    prose - format_markdown_report turns this into the actual report.
    """
    executed_trades = [t for t in trade_log_entries if t["timestamp"][:10] == date_iso]
    buys = [t for t in executed_trades if t["side"] == "buy"]
    sells = [t for t in executed_trades if t["side"] == "sell"]
    total_notional = sum(t["quantity"] * t["price"] for t in executed_trades)

    blocked = [e for e in cycle_entries if e["action"].startswith("blocked_")]
    blocked_by_gate = {}
    for e in blocked:
        blocked_by_gate.setdefault(e["action"], []).append(e)

    recommended = [e for e in cycle_entries if e["action"] == "recommended"]
    excellent_watch = [e for e in cycle_entries if e["action"] == "excellent_watch"]
    protective_exits = [e for e in cycle_entries if e["action"] == "protective_exit"]
    # cycle_log's own "executed" entries (classification/crossover_pct/price/
    # quantity/notional/order_id) - the reasoning behind each executed trade,
    # richer than trade_log_entries' bare {asset, side, quantity, price},
    # which stays the ground truth for what money actually moved. Both are
    # kept: trade_log_entries drives num_executed/num_buys/num_sells/
    # total_notional above (unaffected by this), cycle_log's copy feeds the
    # executive summary's per-decision "why" below.
    executed_entries = [e for e in cycle_entries if e["action"] == "executed"]

    return {
        "date": date_iso,
        "num_executed": len(executed_trades),
        "num_buys": len(buys),
        "num_sells": len(sells),
        "total_notional": total_notional,
        "executed_trades": executed_trades,
        "executed_entries": executed_entries,
        "num_blocked": len(blocked),
        "blocked_by_gate": {gate: len(entries) for gate, entries in blocked_by_gate.items()},
        "blocked_entries": blocked,
        "num_recommended_pending": len(recommended),
        "recommended_entries": recommended,
        "num_excellent_watch": len(excellent_watch),
        "excellent_watch_entries": excellent_watch,
        "num_protective_exits": len(protective_exits),
        "protective_exit_entries": protective_exits,
    }


def _fmt_pct(value):
    return f"{value:+.2f}%" if isinstance(value, (int, float)) else "n/a"


def _describe_event(entry):
    """One human-readable sentence for a single cycle_log entry: what was
    considered (the classification/crossover_pct the strategy actually
    saw) and why the resulting decision (buy/sell/hold-in-place) was
    made - the reasoning trail an "executed"/"blocked_*"/"excellent_watch"/
    "protective_exit" action alone doesn't spell out."""
    asset = entry["asset"]
    action = entry["action"]
    classification = entry.get("classification")
    cross = _fmt_pct(entry.get("crossover_pct"))

    if action == "executed":
        side = "bought" if classification == "fresh_buy_cross" else "sold"
        notional = entry.get("notional")
        amount = f" (${notional:.2f})" if isinstance(notional, (int, float)) else ""
        return (f"**{asset}** — confirmed `{classification}` (crossover {cross}): "
                f"auto-executed, {side}{amount}.")
    if action == "recommended":
        notional = entry.get("notional")
        amount = f" (${notional:.2f})" if isinstance(notional, (int, float)) else ""
        return (f"**{asset}** — confirmed `{classification}` (crossover {cross}){amount}, "
                f"sized above `auto_execute_max_usd`: presented as a recommendation, "
                f"awaiting approval rather than bought/sold automatically.")
    if action == "blocked_cooldown":
        return (f"**{asset}** — confirmed `{classification}` (crossover {cross}) but held, "
                f"not bought: still inside the post-exit whipsaw cooldown.")
    if action == "blocked_concurrent_cap":
        return (f"**{asset}** — confirmed `{classification}` (crossover {cross}) but held, "
                f"not bought: `max_concurrent_positions` was already reached.")
    if action == "blocked_aggregate_cap":
        return (f"**{asset}** — confirmed `{classification}` (crossover {cross}) but sized to "
                f"zero and held: `max_aggregate_position_pct` was already fully deployed.")
    if action == "blocked_volume":
        return (f"**{asset}** — crossover strength cleared the threshold (crossover {cross}) "
                f"but held, not bought: relative volume was below the confirmation minimum, "
                f"an unconvincing breakout.")
    if action == "excellent_watch":
        return (f"**{asset}** — a large move (crossover {cross}) was worth a look, but never "
                f"confirmed as a fresh crossover: held, no action taken.")
    if action == "protective_exit":
        reason = entry.get("reason", "?")
        pnl = entry.get("pnl_pct")
        pnl_str = f", P/L {_fmt_pct(pnl)}" if isinstance(pnl, (int, float)) else ""
        label = "stop-loss" if reason == "stop_loss" else "take-profit" if reason == "take_profit" else reason
        return f"**{asset}** — {label} fired on the open position: sold{pnl_str}."
    return f"**{asset}** — {action}."


def format_executive_summary(summary, watchlist=None):
    """A plain-language, chronological account of every buy/sell/hold
    decision the strategy made this day and why - what was considered
    (the classification and crossover_pct the scanner actually saw) set
    against the decision that followed (executed, recommended, held by a
    gate, or just watched). Built entirely from cycle_log.py's recorded
    entries (summarize_day's return value), not reconstructed from memory.

    watchlist: optional full list of symbols in scope that day (WATCHLIST
    + STOCK_WATCHLIST) - when given, appends one closing line naming any
    symbol with zero events, which held all day with nothing notable to
    report (a plain "hold" is deliberately never logged per-cycle - see
    cycle_log.py - so this is the only place that's said explicitly).
    Omitted (default) skips that line rather than guessing the universe.

    Returns a list of markdown bullet lines, oldest first.
    """
    events = (
        summary["executed_entries"]
        + summary["recommended_entries"]
        + summary["blocked_entries"]
        + summary["excellent_watch_entries"]
        + summary["protective_exit_entries"]
    )
    events.sort(key=lambda e: e["timestamp"])

    lines = [f"- {e['timestamp']}: {_describe_event(e)}" for e in events]

    if watchlist:
        mentioned = {e["asset"] for e in events}
        quiet = sorted(set(watchlist) - mentioned)
        if quiet:
            lines.append(f"- Everything else ({', '.join(quiet)}) showed no notable signal all "
                          f"day and was held throughout, unchanged.")

    if not lines:
        lines.append("- No signals of any kind were logged today - a fully quiet day across the "
                      "whole watchlist.")

    return lines


def format_markdown_report(summary, notes=None, watchlist=None):
    """summary: summarize_day's return value.

    notes: optional extra markdown appended as an "Observations" section
    - where the qualitative after-action-review commentary goes, kept
    separate from the mechanical counts above it.

    watchlist: passed through to format_executive_summary - see there.
    """
    d = summary
    lines = [f"# Daily trading review — {d['date']}", ""]

    lines.append("## Executive summary")
    lines.append("What was considered each cycle and why it was bought, sold, or held - "
                  "chronological, built from the same recorded cycle log the counts below "
                  "come from.")
    lines.append("")
    lines.extend(format_executive_summary(summary, watchlist=watchlist))
    lines.append("")

    lines.append("## Executed trades")
    lines.append(f"- {d['num_executed']} total ({d['num_buys']} buy, {d['num_sells']} sell), "
                  f"${d['total_notional']:.2f} combined notional")
    if d["executed_trades"]:
        lines.append("")
        lines.append("| Time | Asset | Side | Quantity | Price | Notional |")
        lines.append("|---|---|---|---|---|---|")
        for t in d["executed_trades"]:
            notional = t["quantity"] * t["price"]
            lines.append(f"| {t['timestamp']} | {t['asset']} | {t['side']} | "
                          f"{t['quantity']} | {t['price']} | ${notional:.2f} |")
    lines.append("")

    lines.append("## Protective exits")
    lines.append(f"- {d['num_protective_exits']} fired today")
    for e in d["protective_exit_entries"]:
        lines.append(f"  - {e['timestamp']}: {e['asset']} — {e.get('reason', '?')}")
    lines.append("")

    lines.append("## Blocked / skipped signals")
    lines.append(f"- {d['num_blocked']} total")
    for gate, count in sorted(d["blocked_by_gate"].items()):
        lines.append(f"  - {gate}: {count}")
    lines.append("")

    lines.append("## Awaiting approval")
    lines.append(f"- {d['num_recommended_pending']} recommendation(s) presented, oversized for auto-execute")
    lines.append("")

    lines.append("## Excellent-watch alerts (not strategy-confirmed)")
    lines.append(f"- {d['num_excellent_watch']}")
    lines.append("")

    if notes:
        lines.append("## Observations / possible improvements")
        lines.append(notes)
        lines.append("")

    return "\n".join(lines)
