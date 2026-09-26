"""Static configuration for the research agent - a separate agent whose
sole job is to scan news and SEC filings for the stocks the trading
agent (trading_agent/) trades, and log findings to a file the trading
agent can reference for extra context. It never places, previews, or
recommends a trade itself - see research_agent/README.md.

The watchlist itself is NOT duplicated here - it's the union of
trading_agent.config's STOCK_WATCHLIST and VOLTRAP_WATCHLIST, imported
directly so all three agents (trading, VOLTRAP, research) can never
drift out of sync with each other (the stock watchlist has already
changed twice in one day this session, and VOLTRAP's own watchlist is
now reviewed/refreshed the same way - see CHANGELOG.md, 2026-09-26).

v1 (and still, as of the 2026-09-26 watchlist work) is stocks-only:
RobinHood's news/SEC-filing tools are equity-specific, and the owner
explicitly declined adding a web-search source that would cover crypto
- see README.md's "Known gap: crypto" section. VOLTRAP is in scope
DESPITE being an options strategy, not a stock one, because every
VOLTRAP candidate IS a stock or ETF underneath the option (a CSP/covered
call is written on real shares) - the exact same equity news/SEC-filing/
earnings tools already apply, no new data source needed. WATCHLIST
(crypto) remains the one asset class with no research coverage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_agent.config import STOCK_WATCHLIST, VOLTRAP_WATCHLIST  # noqa: E402

# Union, de-duplicated, sorted for a stable/predictable iteration order.
# A symbol that's on both lists (a stock the trading agent trades AND a
# VOLTRAP candidate) is researched once, not twice.
WATCHLIST = sorted(set(STOCK_WATCHLIST) | set(VOLTRAP_WATCHLIST))

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
