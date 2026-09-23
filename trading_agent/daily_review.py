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

    return {
        "date": date_iso,
        "num_executed": len(executed_trades),
        "num_buys": len(buys),
        "num_sells": len(sells),
        "total_notional": total_notional,
        "executed_trades": executed_trades,
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


def format_markdown_report(summary, notes=None):
    """summary: summarize_day's return value.

    notes: optional extra markdown appended as an "Observations" section
    - where the qualitative after-action-review commentary goes, kept
    separate from the mechanical counts above it.
    """
    d = summary
    lines = [f"# Daily trading review — {d['date']}", ""]

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
