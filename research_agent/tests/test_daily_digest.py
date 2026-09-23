import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research_agent.daily_digest import format_daily_digest


def _entry(asset, source_type, summary, timestamp="2026-09-24T13:00:00+00:00", **extra):
    return {"asset": asset, "source_type": source_type, "summary": summary,
            "timestamp": timestamp, **extra}


def test_format_daily_digest_no_findings():
    digest = format_daily_digest([], "2026-09-24")
    assert "2026-09-24" in digest
    assert "No new findings today." in digest


def test_format_daily_digest_groups_by_asset():
    entries = [
        _entry("CRWD", "news", "Beats Q2 estimates"),
        _entry("PANW", "news", "New product launch"),
    ]
    digest = format_daily_digest(entries, "2026-09-24")
    assert "## CRWD" in digest
    assert "## PANW" in digest
    assert digest.index("## CRWD") < digest.index("## PANW")  # alphabetical


def test_format_daily_digest_labels_each_source_type():
    entries = [
        _entry("HUBS", "news", "Beats estimates", url="https://example.com/a"),
        _entry("HUBS", "sec_filing", "Material event disclosed", form_type="8-K", filed_at="2026-09-24"),
        _entry("HUBS", "earnings_upcoming", "Q3 report", report_date="2026-10-01", timing="am"),
    ]
    digest = format_daily_digest(entries, "2026-09-24")
    assert "**News**" in digest
    assert "https://example.com/a" in digest
    assert "**SEC filing**" in digest
    assert "[8-K, filed 2026-09-24]" in digest
    assert "**Upcoming earnings**" in digest
    assert "Reports 2026-10-01 (am)" in digest


def test_format_daily_digest_orders_entries_chronologically_within_asset():
    entries = [
        _entry("CRWD", "news", "second", timestamp="2026-09-24T15:00:00+00:00"),
        _entry("CRWD", "news", "first", timestamp="2026-09-24T10:00:00+00:00"),
    ]
    digest = format_daily_digest(entries, "2026-09-24")
    assert digest.index("first") < digest.index("second")
