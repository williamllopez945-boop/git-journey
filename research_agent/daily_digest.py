"""Assembles the daily research digest from research_log.py's findings -
mirrors trading_agent/daily_review.py's shape (mechanical assembly from
recorded data, not an LLM improvising from memory each run).
"""

SOURCE_LABELS = {
    "news": "News",
    "sec_filing": "SEC filing",
    "earnings_upcoming": "Upcoming earnings",
}


def _describe_entry(entry):
    source_type = entry["source_type"]
    summary = entry["summary"]
    if source_type == "news":
        count = entry.get("article_count")
        if count:
            return f"{summary} ({count} new article{'s' if count != 1 else ''})"
        url = entry.get("url")
        return f"{summary}" + (f" ({url})" if url else "")
    if source_type == "sec_filing":
        form_type = entry.get("form_type", "?")
        filed_at = entry.get("filed_at", "?")
        return f"[{form_type}, filed {filed_at}] {summary}"
    if source_type == "earnings_upcoming":
        report_date = entry.get("report_date", "?")
        timing = entry.get("timing")
        when = f"{report_date}" + (f" ({timing})" if timing else "")
        return f"Reports {when} - {summary}"
    return summary


def format_daily_digest(entries, date_iso):
    """entries: ResearchLogStore.entries_for_date(date_iso) - every
    finding logged that day, already filtered to that date by the
    caller (same convention as daily_review.summarize_day).

    Returns markdown, grouped by asset, each entry as one bullet
    labeled by its source type.
    """
    lines = [f"# Research digest — {date_iso}", ""]

    if not entries:
        lines.append("No new findings today.")
        return "\n".join(lines)

    by_asset = {}
    for e in entries:
        by_asset.setdefault(e["asset"], []).append(e)

    for asset in sorted(by_asset):
        lines.append(f"## {asset}")
        for e in sorted(by_asset[asset], key=lambda x: x["timestamp"]):
            label = SOURCE_LABELS.get(e["source_type"], e["source_type"])
            lines.append(f"- **{label}**: {_describe_entry(e)}")
        lines.append("")

    return "\n".join(lines)
