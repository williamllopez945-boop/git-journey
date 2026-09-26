import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research_agent.research_log import ResearchLogStore


def _new_store():
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.unlink()  # start with no existing file
    return ResearchLogStore(path=tmp)


def test_record_appends_an_entry_with_freeform_extra_fields():
    store = _new_store()
    store.record("CRWD", "news", "Beats Q2 estimates", now=_dt("2026-09-24T13:00:00+00:00"),
                 headline="CrowdStrike beats Q2 estimates", url="https://example.com/a")
    entries = store.entries_for_asset("CRWD")
    assert len(entries) == 1
    assert entries[0]["source_type"] == "news"
    assert entries[0]["url"] == "https://example.com/a"


def test_entries_for_asset_filters_to_that_symbol_only():
    store = _new_store()
    store.record("CRWD", "news", "a", now=_dt("2026-09-24T13:00:00+00:00"))
    store.record("PANW", "news", "b", now=_dt("2026-09-24T13:00:00+00:00"))
    assert len(store.entries_for_asset("CRWD")) == 1
    assert len(store.entries_for_asset("PANW")) == 1
    assert store.entries_for_asset("MAIR") == []


def test_entries_for_asset_respects_since():
    store = _new_store()
    store.record("CRWD", "news", "old", now=_dt("2026-09-01T00:00:00+00:00"))
    store.record("CRWD", "news", "new", now=_dt("2026-09-24T00:00:00+00:00"))
    recent = store.entries_for_asset("CRWD", since="2026-09-20")
    assert len(recent) == 1
    assert recent[0]["summary"] == "new"


def test_entries_for_date_filters_by_utc_date():
    store = _new_store()
    store.record("CRWD", "news", "today", now=_dt("2026-09-24T13:00:00+00:00"))
    store.record("CRWD", "news", "yesterday", now=_dt("2026-09-23T13:00:00+00:00"))
    todays = store.entries_for_date("2026-09-24")
    assert len(todays) == 1
    assert todays[0]["summary"] == "today"


def test_sec_filing_and_earnings_entries_carry_their_own_extra_fields():
    store = _new_store()
    store.record("HUBS", "sec_filing", "Filed an 8-K", now=_dt("2026-09-24T13:00:00+00:00"),
                 form_type="8-K", filing_id="xyz", filed_at="2026-09-24")
    store.record("HUBS", "earnings_upcoming", "Reports next week",
                 now=_dt("2026-09-24T13:00:00+00:00"), report_date="2026-10-01", timing="am")
    entries = store.entries_for_asset("HUBS")
    filing = next(e for e in entries if e["source_type"] == "sec_filing")
    earnings = next(e for e in entries if e["source_type"] == "earnings_upcoming")
    assert filing["form_type"] == "8-K"
    assert earnings["report_date"] == "2026-10-01"


def _dt(iso):
    from datetime import datetime
    return datetime.fromisoformat(iso)
