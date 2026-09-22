# Crypto watchlist snapshot — 2026-09-22T10:xx UTC

**Update:** later the same day, `config.py`'s `WATCHLIST` was expanded to
include this snapshot's top 10 (PEPE, WIF, BONK, PENGU, FLOKI, XCN, MEW,
POPCAT, SHIB) alongside the original BTC/ETH/SOL/DOGE. The "not changed"
note below describes this document's state at the time it was written,
not the current config.

Point-in-time analysis, not live state — re-run scan `8f2ca450-1f7f-4e69-b015-daafe494c14e`
(via the RobinHood MCP `run_scan` tool) for current numbers.

Screened all 49 crypto pairs Robinhood offers (`FILTER_TYPE_INSTRUMENT_TYPE = CRYPTO`),
using Robinhood's server-side `closeAvg` over real hourly candles with this repo's exact
strategy parameters (`STRATEGY.short_window=10`, `STRATEGY.long_window=30` from
`config.py`, interpreted as 1h bars). Ranked by crossover strength
`(SMA10 - SMA30) / SMA30`.

This ranks *current bullish-regime strength*, not a fresh crossover *event* — a true
event needs the prior bar too, which the per-asset hourly poller
(`price_history.py` + `strategy.py`) is building up for BTC/ETH/SOL/DOGE specifically.

## Top 10 by crossover strength

| Rank | Symbol | Name | Last | SMA10(1h) | SMA30(1h) | Crossover |
|---|---|---|---|---|---|---|
| 1 | PEPE | Pepe | $0.00000494 | 0.00000508 | 0.00000470 | +8.12% |
| 2 | WIF | dogwifhat | $0.2510 | 0.2496 | 0.2339 | +6.68% |
| 3 | BONK | Bonk | $0.00000344 | 0.00000349 | 0.00000334 | +4.51% |
| 4 | PENGU | Pudgy Penguins | $0.009072 | 0.008966 | 0.008634 | +3.85% |
| 5 | FLOKI | Floki Inu | $0.0000295 | 0.0000295 | 0.0000284 | +3.78% |
| 6 | XCN | Onyxcoin | $0.004262 | 0.003760 | 0.003635 | +3.44% |
| 7 | DOGE | Dogecoin | $0.098322 | 0.099685 | 0.096444 | +3.36% |
| 8 | MEW | cat in a dogs world | $0.000474 | 0.000473 | 0.000460 | +2.86% |
| 9 | POPCAT | Popcat | $0.057076 | 0.056809 | 0.055304 | +2.72% |
| 10 | SHIB | Shiba Inu | $0.00000602 | 0.00000603 | 0.00000588 | +2.52% |

9 of 10 are highly volatile meme coins. This list is informational — the agent's live
`WATCHLIST` in `config.py` was not changed and remains BTC/ETH/SOL/DOGE only.

## Required watchlist assets (BTC/ETH/SOL/DOGE) — confirmed present in the screener

| Symbol | Rank (of 49) | Crossover | State |
|---|---|---|---|
| DOGE | 7 | +3.36% | bullish |
| BTC | 26 | +0.63% | bullish |
| SOL | 28 | +0.32% | bullish |
| ETH | 29 | +0.24% | bullish |

All four are currently in a bullish SMA(10,30) regime, consistent across the board, but
none of this is a fresh crossover signal from the agent's own per-asset history (which
only has 1 bar recorded so far — see PLAYBOOK.md).
