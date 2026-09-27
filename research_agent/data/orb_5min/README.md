# ORB five-minute equity data

Data-only handoff for Claude Code. No strategy, configuration, execution, or backtest was changed or run. These files are historical market data, not proof that ORB is profitable.

## Source and retrieval

- Source: authenticated Alpaca market-data connector, `get_stock_bars`, explicitly requesting the consolidated `sip` feed and `timeframe="5Min"`.
- Fetch date: 2026-09-27 UTC (2026-09-27 America/Chicago). Finalized: 2026-09-27T05:24:31.921352+00:00.
- Watchlist verified directly from `trading_agent/config.py` on `main` at `9b661576030655c57c9b5ef78ec6b3a0cbdbbd56`: SMCI, MARA, OKLO, CLSK, RGTI, ASST, NVDL, SEDG.
- Each symbol was queried independently, starting at `2000-01-01T00:00:00Z`, ending at `2026-09-26T00:00:00Z` (after the last completed regular session, September 25). No earlier history was returned by this source/query; first returned dates are NOT necessarily IPO or listing dates.
- Production retrieval used page limits of 5,000 and 10,000, `sort="asc"`, and default currency/asof. After each nonempty response, the next request started one second after its last timestamp. Retrieval continued until a successful EMPTY response, even when an earlier response contained fewer than the limit. The connector does not expose a page token. Every returned five-minute timestamp was checked for alignment and order. Temporary internal errors were retried from the unchanged cursor; failed requests contributed no rows.
- Initial capability probes, including larger requests and an explicit-asof attempt, are not included in these files. Successful paginated responses alone produced the CSVs.
- Session calendar: Alpaca `get_calendar`, 2000-01-01 through 2026-09-25. Filtered in `America/New_York`, with daylight-saving transitions, holidays, and early closes. Include a bar only when its entire five-minute interval falls within calendar open/close; regular open is inclusive and close is exclusive. Thus a 16:00 bar is excluded on a normal day, and 13:00 is excluded on a 13:00 early close.
- No forward filling, interpolation, resampling, fabricated pre-listing rows, price adjustment, gap repair, or smoothing was performed. Extended-hours rows were discarded. The source exposes no interpolation flag here: these are vendor-supplied SIP aggregates, not independently verified individual exchange prints.

## CSV schema

`timestamp,open,high,low,close,volume`

Timestamp is the UTC interval START in ISO-8601 with `Z`. OHLC is USD per share; volume is shares. Values were preserved from connector numeric responses. Files are chronological, UTF-8, comma-separated, with LF line endings. `trade_count` and `vwap` were available during validation but are omitted to meet the requested six-column schema.

## Coverage

| Symbol | Earliest regular bar (UTC) | Latest regular bar (UTC) | Regular bars | Sessions with bars | Raw retrieved bars | Pages, including empty terminator |
|---|---|---|---:|---:|---:|---:|
| SMCI | 2016-01-04T14:30:00Z | 2026-09-25T19:55:00Z | 178,029 | 2,349 | 258,333 | 43 |
| MARA | 2017-10-30T13:30:00Z | 2026-09-25T19:55:00Z | 162,240 | 2,238 | 331,500 | 54 |
| OKLO | 2021-07-08T14:10:00Z | 2026-09-25T19:55:00Z | 61,372 | 1,279 | 120,044 | 26 |
| CLSK | 2020-01-24T14:30:00Z | 2026-09-25T19:55:00Z | 127,551 | 1,676 | 240,852 | 45 |
| RGTI | 2021-04-22T14:45:00Z | 2026-09-25T19:55:00Z | 96,363 | 1,343 | 175,370 | 37 |
| ASST | 2023-02-03T15:45:00Z | 2026-09-25T19:55:00Z | 53,000 | 914 | 94,579 | 20 |
| NVDL | 2022-12-13T15:45:00Z | 2026-09-25T19:55:00Z | 68,849 | 947 | 146,970 | 31 |
| SEDG | 2016-01-04T14:30:00Z | 2026-09-25T19:55:00Z | 209,256 | 2,698 | 254,583 | 38 |

Total: **956,660 regular-session bars**, from 1,622,231 retrieved bars.

## Missing observations and quality checks

Counts below use all exchange sessions between each file's first and last dates, including those endpoints. Incomplete includes fully absent sessions and initial partial listing days. A missing opening range means at least one of the 09:30, 09:35, or 09:40 New York bars is absent. These are data-availability counts, not a diagnosis: inactivity, halts, listing changes, and source gaps may contribute. Later analysis must skip incomplete opening ranges or define an explicit policy before testing.

| Symbol | Missing 5-minute slots | Incomplete sessions | Entire sessions absent | Missing opening ranges | Outside-session rows removed | Flat OHLC bars retained |
|---|---:|---:|---:|---:|---:|---:|
| SMCI | 31,659 | 1,219 | 349 | 524 | 80,304 | 9,767 |
| MARA | 11,640 | 551 | 0 | 124 | 169,260 | 8,876 |
| OKLO | 40,526 | 687 | 32 | 598 | 58,672 | 7,659 |
| CLSK | 2,823 | 89 | 1 | 36 | 113,301 | 1,161 |
| RGTI | 9,669 | 325 | 21 | 128 | 79,007 | 3,147 |
| ASST | 18,004 | 527 | 0 | 231 | 41,579 | 8,534 |
| NVDL | 4,885 | 187 | 2 | 47 | 78,121 | 2,076 |
| SEDG | 432 | 169 | 0 | 8 | 45,327 | 1,494 |

Longest consecutive runs of exchange sessions with no returned regular bars:

- SMCI: 2018-08-23 through 2020-01-13 (349 sessions). Cause not independently diagnosed; do not bridge this gap with fabricated prices.
- OKLO: 2022-08-31 through 2022-09-02 (3 sessions). Cause not independently diagnosed; do not bridge this gap with fabricated prices.
- CLSK: 2024-11-08 through 2024-11-08 (1 sessions). Cause not independently diagnosed; do not bridge this gap with fabricated prices.
- RGTI: 2021-09-27 through 2021-09-30 (4 sessions). Cause not independently diagnosed; do not bridge this gap with fabricated prices.
- NVDL: 2022-12-19 through 2022-12-19 (1 sessions). Cause not independently diagnosed; do not bridge this gap with fabricated prices.

Validation checked chronological and unique timestamps, five-minute boundaries, finite positive OHLC, `low <= min(open,close) <= max(open,close) <= high`, nonnegative volume, and exchange-session membership. Flat OHLC alone does not establish synthetic data; a traded bar may have only one eligible price. No such rows were discarded solely for being flat.

| Symbol | Duplicate timestamps | Invalid OHLCV rows | Retained bars with nonpositive volume or trade count |
|---|---:|---:|---:|
| SMCI | 0 | 0 | 0 |
| MARA | 0 | 0 | 0 |
| OKLO | 0 | 0 | 0 |
| CLSK | 0 | 0 | 0 |
| RGTI | 0 | 0 | 0 |
| ASST | 0 | 0 | 0 |
| NVDL | 0 | 0 | 0 |
| SEDG | 0 | 0 | 0 |

## Volatility coverage (descriptive only)

To show variation in available volatility conditions without implementing a strategy, compare quarterly medians of each complete session's `(session high - session low) / first-bar open * 100`. Only quarters with at least 40 complete sessions qualify. The lowest and highest available quarters are reported below. This is a coverage diagnostic, not a formal regime model, performance test, or instruction to select favorable dates. Business/product changes can also affect these differences.

| Symbol | Lower-range quarter | Median daily range | Complete sessions | Higher-range quarter | Median daily range | Complete sessions |
|---|---|---:|---:|---|---:|---:|
| SMCI | 2016Q3 | 2.5111% | 42 | 2025Q1 | 8.1850% | 60 |
| MARA | 2025Q3 | 5.5365% | 64 | 2021Q1 | 14.5054% | 61 |
| OKLO | 2026Q3 | 6.1442% | 61 | 2024Q4 | 11.8393% | 64 |
| CLSK | 2025Q3 | 6.1467% | 64 | 2020Q3 | 12.4138% | 63 |
| RGTI | 2026Q3 | 5.6650% | 61 | 2024Q4 | 17.2148% | 62 |
| ASST | 2026Q3 | 6.8744% | 61 | 2025Q3 | 13.9702% | 58 |
| NVDL | 2025Q3 | 4.1592% | 64 | 2024Q3 | 8.3836% | 64 |
| SEDG | 2017Q3 | 2.9186% | 58 | 2025Q2 | 8.8095% | 62 |

## Interpretation caveats

1. **Corporate actions / unadjusted prices:** The connector has no adjustment parameter; Alpaca documents `raw` as the bars endpoint default. No adjustment was requested or applied locally. Confirm this assumption before cross-date return work; splits, reverse splits, and dividends can introduce jumps. Reconcile actions separately rather than silently changing these files. See [Alpaca historical bars](https://docs.alpaca.markets/us/v1.1/reference/stockbars).
2. **Symbol mapping:** Default `asof` mapping can include predecessor symbols. Preserve that genuine vendor history, but do not interpret it as the same operating business throughout. [Alpaca symbol-mapping documentation](https://docs.alpaca.markets/us/reference/stockbarsingle-1).
3. **OKLO:** Bars before 2024-05-10 precede trading under OKLO after the AltC business combination. Treat them as predecessor history, not operating-Oklo history. [Issuer announcement](https://oklo.com/newsroom/oklo-inc-begins-trading-on-the-new-york-stock-exchange).
4. **RGTI:** Bars before 2022-03-02 precede trading under RGTI after the Supernova business combination. Segment that predecessor period. [Issuer announcement](https://investors.rigetti.com/news-releases/news-release-details/rigetti-computing-announces-closing-business-combination).
5. **NVDL:** This is a leveraged daily-reset ETF. Its objective changed from 1.5x to 2x in 2024, and it has undergone splits. Full-history behavior is not one unchanged product. [Issuer leverage announcement](https://graniteshares.com/press/graniteshares-amplifies-leverage-in-single-stock-etfs-to-200/) and [split announcement](https://graniteshares.com/press/graniteshares-announces-forward-split-of-nvdl-and-fbl/).
6. Earliest source availability varies by ticker. Missing bars were never padded; full lifetime coverage, cross-vendor accuracy, and a complete corporate-action audit are not claimed.
7. Selecting today's watchlist introduces selection/survivorship bias for any broad strategy claim. These data answer the requested current-watchlist evaluation, not an unbiased historical universe study.
8. OHLCV bars contain neither executable bid/ask quotes nor intrabar event ordering. They do not establish fill prices, short availability, options profitability, or whether stop or target occurred first within a bar. Historical corrections may change future downloads.

## Integrity

SHA-256 hashes of delivered CSV bytes:

| File | Bytes | SHA-256 |
|---|---:|---|
| SMCI.csv | 9,238,066 | `91cbd92ab6d45a06465bd35ffed7785422036156d4485bfec98a4be4e8aa75ab` |
| MARA.csv | 8,482,081 | `72c0f13c9ec46ce3a2504e013f1ff9030f0fde744caedabb6ede21194e2d3ad8` |
| OKLO.csv | 3,180,458 | `ec46ba9ebfb6892d34110e5cb3e5abe7b6ef27d6067e2ef9b1e946d73fc85f26` |
| CLSK.csv | 6,560,999 | `a687c14d6bf90a4565580d4a89de61abafad8b111c46373f4bfe1a474ddd11bf` |
| RGTI.csv | 4,935,648 | `0263b3c4835f81df25cf76ffc813113cf6658388c2a7a66bff2a2e44f1ffeaf7` |
| ASST.csv | 2,691,270 | `7c1c785c2ab489f1bd2aeb803bd420383569ad2a02f8c780df4933218fb4e015` |
| NVDL.csv | 3,636,913 | `1c4b514e86a0cd5b993b8f45fecad1da5f7a4e4dfe7e7c79da62bdfea6973e53` |
| SEDG.csv | 10,954,423 | `062f6acd332b77792f34a149d53f39ffca0d2eeffd19b01161aa44d4fc5bbc32` |

From the repository root, verify hashes with `sha256sum research_agent/data/orb_5min/*.csv`. The task handoff records repository tests and exact commit information.
