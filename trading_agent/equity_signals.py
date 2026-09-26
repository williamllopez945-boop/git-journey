"""Computes SMA(10,30) 1h crossover inputs for STOCK_WATCHLIST symbols
directly from get_equity_historicals/get_equity_quotes, bypassing the
production stock scan (scan_id 6e009dcf-d184-45a7-915f-ccfc50b4e6be)'s
200-row pagination cap.

Found 2026-09-25: that scan's universe is ~398 stocks, sorted by price
descending, with no pagination parameter exposed. On every market-hours
cycle observed on both 2026-09-24 and 2026-09-25, only ILMN (of the
10-name STOCK_WATCHLIST) ever landed on the returned page - the other 9
names were silently never evaluated for a crossover, not because nothing
happened, just because they never appeared on the page. This module
computes the same signal inputs directly per watchlist symbol instead
(get_equity_historicals accepts up to 10 symbols per call, exactly the
STOCK_WATCHLIST size, so one call covers the whole watchlist), so every
cycle actually evaluates all 10 names.

Mirrors scanner_signals.classify's input shape (sma10, sma30, pct_change,
relative_volume) exactly - classify() itself is asset-class-agnostic and
needs no changes; only the data source for stocks changes. Crypto keeps
using the production scan unchanged (its 49-instrument universe is well
under the 200-row cap, so it isn't affected by this gap).
"""

from .volume_filter import average_volume, DEFAULT_VOLUME_PERIOD


def sma_pair(closes, short_window=10, long_window=30):
    """closes: oldest-to-newest 1h close prices for one symbol (from
    get_equity_historicals' `bars`, each bar's close_price, in the order
    returned). Returns (sma_short, sma_long), or (None, None) if there
    isn't yet enough history for the long window - the caller's signal to
    skip this symbol silently this cycle (a newly-added watchlist symbol
    still warming up), not an error."""
    if len(closes) < long_window:
        return None, None
    return sum(closes[-short_window:]) / short_window, sum(closes[-long_window:]) / long_window


def relative_volume(volumes, period=DEFAULT_VOLUME_PERIOD):
    """volumes: oldest-to-newest 1h bar volumes for one symbol, same order
    as closes. Returns the current bar's volume over the preceding
    period's average - the same quantity the production crypto scan's own
    "Relative volume" column reports (volume(1h,1)/volumeAvg(14,1h)), so
    classify()'s volume gate behaves identically for stocks. None if
    there isn't enough history yet (don't block a fresh buy cross on
    warm-up alone - matches volume_filter.py's own default)."""
    avg = average_volume(volumes, period)
    if avg is None or avg <= 0:
        return None
    return volumes[-1] / avg


def pct_change_from_quote(last_price, previous_close):
    """(last - previous_close) / previous_close - the change since the
    last completed session's close, matching the production scan's own
    "% Change" column semantics (a daily change, not bar-over-bar).
    last_price/previous_close come from get_equity_quotes
    (quote.last_trade_price and quote.previous_close respectively). None
    if previous_close is falsy (e.g. a data gap)."""
    if not previous_close:
        return None
    return (last_price - previous_close) / previous_close
