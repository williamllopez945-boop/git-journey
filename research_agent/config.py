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
RobinHood's SEC-filing/earnings tools are equity-specific, and the owner
explicitly declined adding a web-search source that would cover crypto
- see README.md's "Known gap: crypto" section. VOLTRAP is in scope
DESPITE being an options strategy, not a stock one, because every
VOLTRAP candidate IS a stock or ETF underneath the option (a CSP/covered
call is written on real shares) - the exact same equity news/SEC-filing/
earnings tools already apply, no new data source needed. WATCHLIST
(crypto) remains the one asset class with no research coverage.

News source change (2026-09-29): `get_equity_news`, the tool this
module's news step originally called, does not exist in this session's
RobinHood MCP toolset (confirmed via a full tool-catalog search, not a
transient connectivity issue) - it apparently existed when the first
`research_log.json` "news" entries were recorded 2026-09-23/24 (they
carry real `article_ids`) but is gone now. Owner approved (2026-09-29,
AskUserQuestion) swapping in `WebSearch` restricted to
NEWS_ALLOWED_DOMAINS below as the replacement - a real, deliberate scope
change from "RobinHood's tools only, no new APIs" for the *stock* news
source specifically. This does NOT reopen the crypto question above -
WATCHLIST (crypto) is still out of scope; only the stocks/VOLTRAP news
mechanism changed. See PLAYBOOK.md step 2a.
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
NEWS_LIMIT = 5           # results per symbol per WebSearch call - kept small since news is
                         # logged as one consolidated summary per symbol per cycle,
                         # not one entry per article (see PLAYBOOK.md's dedup step)
# WebSearch's allowed_domains filter (2026-09-29) - reputable financial
# news/wire sources only, so a symbol search doesn't surface random
# blogs/forums as "news." Not exhaustive; add a domain here (not
# elsewhere) if a real gap shows up in practice.
#
# reuters.com, wsj.com, and marketwatch.com were tried first and removed
# the same day: WebSearch's allowed_domains fails the ENTIRE call with a
# 400 error if even one listed domain is inaccessible to Anthropic's
# crawler (confirmed live, all 3 named in one error together - not a
# per-domain partial filter), not just excluded from results. All 7
# domains below were confirmed working via a live WebSearch call before
# being kept in this list.
NEWS_ALLOWED_DOMAINS = [
    "bloomberg.com",
    "cnbc.com",
    "businesswire.com",
    "prnewswire.com",
    "finance.yahoo.com",
    "investing.com",
    "benzinga.com",
]
FORM_TYPES = ["8-K", "10-Q", "10-K"]  # 8-K first - the "material event" filing type
                                       # most relevant to sudden price moves
EARNINGS_LOOKAHEAD_DAYS = 14  # flag an upcoming earnings date within this many days -
                               # targets the exact gap-risk pattern backtest_2026-09-23.md
                               # found on HUBS (-20.01% overnight, an earnings reaction)
                               # and MDLN (-15.2%) - an advance flag, not a fix, but visible
                               # to the owner and the trading agent's recommendation flow
                               # before it happens rather than only explained after.
