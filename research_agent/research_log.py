"""Append-only log of research findings - news articles, SEC filings, and
upcoming earnings dates - for the stocks the trading agent trades.

Modeled directly on trading_agent/cycle_log.py's CycleLogStore: same
shape (one JSON array, one entry per finding, freeform extra fields per
source_type rather than a fixed schema), same persistence pattern
(gitignored - runtime data, rebuilt by re-running the research Routine,
never hand-edited).

Deduplication is the caller's job, not this store's (same philosophy as
cycle_log.py - an append-only log doesn't second-guess what's written to
it). research_agent/PLAYBOOK.md's steps check entries_for_asset(symbol)'s
existing url/filing_id values before calling record() again for the same
article or filing - get_equity_news returns "recent" articles each call,
not just new ones since the last run, so without this check the same
article would get re-logged every day it stays in that recent window.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent / "research_log.json"

# Valid `source_type` values for record().
SOURCE_TYPES = {
    "news",               # a news article from get_equity_news
    "sec_filing",         # a new SEC filing from get_sec_filing_index/get_sec_filing
    "earnings_upcoming",  # an earnings report date within EARNINGS_LOOKAHEAD_DAYS
}


class ResearchLogStore:
    def __init__(self, path=LOG_PATH):
        self.path = path

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return []

    def _save(self, entries):
        self.path.write_text(json.dumps(entries, indent=2))

    def record(self, asset, source_type, summary, now=None, **extra):
        """Append one finding. `extra` carries whatever's relevant to this
        source_type - kept freeform rather than a fixed schema, same as
        cycle_log.py's record():
          news:              headline, url, published_at
          sec_filing:        form_type, filing_id, filed_at
          earnings_upcoming: report_date, estimate_eps, timing (am/pm)
        """
        entries = self._load()
        entries.append({
            "timestamp": (now or datetime.now(timezone.utc)).isoformat(),
            "asset": asset,
            "source_type": source_type,
            "summary": summary,
            **extra,
        })
        self._save(entries)

    def entries_for_asset(self, symbol, since=None):
        """All entries for one symbol, oldest first. since: an ISO date
        (YYYY-MM-DD) or datetime isoformat string - when given, only
        entries whose timestamp is on or after it are returned. This is
        the lookup trading_agent/PLAYBOOK.md calls when presenting a
        recommendation, to surface recent research alongside it."""
        entries = [e for e in self._load() if e["asset"] == symbol]
        if since is not None:
            entries = [e for e in entries if e["timestamp"] >= since]
        return entries

    def entries_for_date(self, date_iso):
        """All entries whose timestamp date (UTC) matches date_iso
        (YYYY-MM-DD) - mirrors CycleLogStore's method, for the daily
        digest."""
        return [e for e in self._load() if e["timestamp"][:10] == date_iso]
