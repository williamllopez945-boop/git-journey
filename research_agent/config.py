"""Static configuration for the research agent - a separate agent whose
sole job is to scan news and SEC filings for the stocks the trading
agent (trading_agent/) trades, and log findings to a file the trading
agent can reference for extra context. It never places, previews, or
recommends a trade itself - see research_agent/README.md.

The watchlist itself is NOT duplicated here - it's imported directly
from trading_agent.config so the two agents can never drift out of
sync with each other (the stock watchlist has already changed twice in
one day this session).

v1 is stocks-only: RobinHood's news/SEC-filing tools are equity-specific,
and the owner explicitly declined adding a web-search source that would
cover crypto - see README.md's "Known gap: crypto" section.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_agent.config import STOCK_WATCHLIST as WATCHLIST  # noqa: E402

LOOKBACK_DAYS = 7        # how far back to check for new SEC filings since the last run
NEWS_LIMIT = 5           # articles per symbol per run - kept small since news is
                         # logged as one consolidated summary per symbol per cycle,
                         # not one entry per article (see PLAYBOOK.md's dedup step)
FORM_TYPES = ["8-K", "10-Q", "10-K"]  # 8-K first - the "material event" filing type
                                       # most relevant to sudden price moves
EARNINGS_LOOKAHEAD_DAYS = 14  # flag an upcoming earnings date within this many days -
                               # targets the exact gap-risk pattern backtest_2026-09-23.md
                               # found on HUBS (-20.01% overnight, an earnings reaction)
                               # and MDLN (-15.2%) - an advance flag, not a fix, but visible
                               # to the owner and the trading agent's recommendation flow
                               # before it happens rather than only explained after.
