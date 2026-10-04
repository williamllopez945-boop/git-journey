# Weekly watchlist review — 2026-10-04

Owner-requested ad-hoc run of the standing weekly review ("Run the weekly
watchlist review now") rather than waiting for its regular Sunday 15:00
UTC firing. **Decision: no change recommended** for either watchlist —
a real, scoreable underperformance on the crypto side (DOGE, AVAX) with
no backtestable replacement (same real data gap flagged every prior
review), and a stock-side swap that wins on mean/full-period return but
loses the binding worst-case-first portfolio check, exactly the kind of
reversal this process exists to catch.

## Method

Same procedure as `watchlist_review_2026-09-27.md` and
`watchlist_review_2026-09-29_stocks.md` (see `PLAYBOOK.md`'s "Weekly
watchlist review" section):

1. Score every current `WATCHLIST`/`STOCK_WATCHLIST` member by trailing
   performance: `watchlist_review.trailing_trade_pnl` (real trade
   history, `trading_agent/state.json`) where it exists, else a
   90-day-hourly `backtest.py` pass against real historicals.
2. Rank worst-case-first; bottom 1-2 (skipping any currently open
   position) become removal candidates.
3. Source addition candidates from both production scans
   (`watchlist_review.rank_by_crossover_strength`), excluding the
   current watchlist and, for crypto, the meme/political/stablecoin
   list from `watchlist_2026-09-23_meme_removal.md`.
4. Backtest every addition candidate in isolation, then confirm with a
   combined `portfolio_backtest.py` run against the current watchlist —
   binding per the 2026-09-27 precedent, where an isolated win reversed
   at the portfolio level.
5. Propose a swap only where the candidate clearly beats the removal
   candidate worst-case-first.

Current open positions (per `get_crypto_positions`, 2026-10-04 21:08 UTC
cycle): **BTC, BCH, SOL** — none eligible as removal candidates this
week regardless of score.

## Crypto: current holdings scored

Real trade P&L via `trailing_trade_pnl(asset, trade_log, current_price)`,
current prices from the 2026-10-04 21:08 UTC crypto scan:

| Asset | Score | Open position? |
|---|---|---|
| **DOGE** | **-$95.70** | No |
| SOL | -$79.55 | **Yes — skip** |
| **AVAX** | **-$11.23** | No |
| CRV | -$5.21 | No |
| LINK | -$2.80 | No |
| XLM | -$2.80 | No |
| DOT | -$2.33 | No |
| ETH | $0.00 (dust, net-zero) | No |
| HBAR | +$0.04 | No |
| BTC | +$1.23 | **Yes — skip** |
| BCH | +$1.85 | **Yes — skip** |
| LIT, AERO, ZORA, ASTER | **not scoreable** | — |

DOGE's loss is the back-calculated price-correction trade documented in
`pnl_reconciliation_2026-09-29.md` (bought near a local high at $0.1804,
corrected to the real Robinhood fill basis, later sold near $0.096) —
a real, large realized loss, not a data artifact.

**Real data gap, same one flagged in every prior review**: there is no
crypto historicals tool, and only BTC/ETH have a usable equity-ETF proxy
(IBIT/ETHA) — both already scored above via real trade history, not
useful as swap-in candidates. LIT, AERO, ZORA, ASTER have never traded
and have no proxy, so 4 of 15 `WATCHLIST` assets remain unscoreable this
week too.

**Removal candidates: DOGE (-$95.70) and AVAX (-$11.23)** — the two
largest real realized/unrealized losses, neither currently held.

**Addition candidates** (crypto scan `8f2ca450-...`, excluding
watchlist + meme/political/stablecoin list), top by crossover strength:
SEI (+2.05%), XTZ (+1.87%), SUI (+1.82%).

**No crypto swap can be responsibly proposed.** None of SEI/XTZ/SUI (or
any other candidate) can be backtested — the same historicals gap that
blocks scoring 4 current holdings blocks validating any replacement.
Per the standing rule ("never swap on a screener snapshot alone"), a
real, clearly-underperforming asset (DOGE, AVAX) is not enough by
itself to justify a swap without a backtested replacement. **DOGE and
AVAX stay on the watchlist this week**, flagged again for re-review
once a crypto data source exists.

## Stocks: current holdings scored (90-day-hourly `backtest.py`, real data)

None of the 10 `STOCK_WATCHLIST` names have ever traded, so all 10 are
scored by backtest (production settings: SMA(10,30), `min_strength_pct=0`,
`cooldown_bars=4`, current stop-loss/take-profit/gate defaults). Window:
2026-07-06T14:00Z–2026-10-02T19:00Z, 384 hourly bars, split at the
midpoint (2026-08-19T14:00Z) for H1/H2.

| Symbol | Full return | H1 | H2 | Worst (split) | Max DD | Trades |
|---|---|---|---|---|---|---|
| **PTC** | **-4.44%** | +6.48% | **-8.09%** | **-8.09%** | 12.17% | 14 |
| **PYPL** | **-2.59%** | +4.88% | **-7.60%** | **-7.60%** | 10.12% | 9 |
| AR | +9.22% | +8.41% | -4.95% | -4.95% | 6.39% | 9 |
| VTRS | +6.13% | -2.67% | +2.01% | -2.67% | 8.06% | 9 |
| IR | +1.07% | +3.30% | -2.16% | -2.16% | 9.97% | 7 |
| CRWD | +6.69% | +7.04% | -0.34% | -0.34% | 11.18% | 10 |
| CRDO | +6.60% | +6.09% | +0.48% | +0.48% | 12.54% | 13 |
| PANW | +16.42% | +6.33% | +9.50% | +6.33% | 7.90% | 11 |
| TWLO | +35.63% | +17.60% | +8.24% | +8.24% | 7.69% | 14 |
| ILMN | +26.38% | +9.93% | +8.37% | +8.37% | 7.24% | 10 |

**Removal candidates: PTC (-4.44% full, -8.09% worst-case) and PYPL
(-2.59% full, -7.60% worst-case)** — the clear bottom 2 on both full-
period and worst-case ranking, neither currently held.

**Addition candidates** (stock scan `6e009dcf-...`, excluding watchlist,
$10B+ market cap floor), top by crossover strength: IBRX (+6.35%),
INIO (+5.52%), MTSI (+4.73%). Isolated 90-day backtests, same window:

| Symbol | Full return | H1 | H2 | Worst (split) | Max DD | Trades |
|---|---|---|---|---|---|---|
| IBRX | -1.06% | -1.77% | -7.29% | -7.29% | 16.73% | 17 |
| INIO | -11.90% | +1.21% | -12.96% | -12.96% | 16.27% | 12 |
| **MTSI** | **+11.48%** | +7.79% | +3.42% | **+3.42%** | 16.55% | 13 |

**IBRX and INIO are not beaten by either removal candidate's weakness**
— both score worse than PTC/PYPL on worst-case, full-period, or both.
No swap considered for them.

**MTSI, isolated: clearly beats both PTC and PYPL** (worst-case +3.42%
vs. PTC's -8.09% and PYPL's -7.60%; full-period +11.48% vs. -4.44%/
-2.59%). This looked like a real, decisive swap — the same shape as the
2026-09-27 MAIR→RVMD isolated comparison.

### The combined portfolio check reverses it

Per the required step 4, ran `portfolio_backtest.py` with the full
10-name watchlist (current settings: `max_position_pct=20%`,
`max_concurrent_positions=5`, `max_aggregate_pct=60%`,
`max_trades_per_day=4`), same 384-bar window, split H1/H2:

| Variant | Full return | H1 | H2 | Worst (split) |
|---|---|---|---|---|
| **Current (PTC+PYPL in)** | +0.14% | -1.18% | -1.18% | **-1.18%** |
| PTC→MTSI | **+5.96%** | +2.66% | -1.74% | **-1.74%** |
| PYPL→MTSI | +2.46% | -3.11% | +1.42% | -3.11% |
| Both PTC&PYPL→MTSI,IBRX | +4.70% | -3.88% | +2.87% | -3.88% |

**Every swap variant's full-period return beats the current watchlist**
(PTC→MTSI +5.96% vs. +0.14% is the strongest), but **none beats the
current watchlist's worst-case** — PTC→MTSI's worst split-window result
(-1.74%) is slightly *worse* than the current watchlist's (-1.18%), and
the other two variants are clearly worse (-3.11%, -3.88%). Same
interaction effect documented 2026-09-27: MTSI's entries compete with
the other 9 names for the same concurrent-position/aggregate-cap room
in a way isolated single-asset backtesting can't see, and it shows up
specifically in the H2 window where the current watchlist already holds
up better than it looks in isolation.

**No stock swap recommended.** PTC and PYPL remain the two weakest
backtested names and the one sourced candidate (MTSI) that looked
genuinely superior in isolation does not clearly beat them once tested
worst-case-first at the portfolio level — a mean/full-period win is not
sufficient under this project's standing rule.

## Decision

**No change recommended this week**, for both watchlists — a genuine,
evidence-based outcome on both sides, not a failure to look. Flagged
for next week:
- Crypto: re-score DOGE and AVAX (now the two flagged names) and the 4
  untestable names (LIT, AERO, ZORA, ASTER) the moment any crypto
  historicals source becomes available.
- Stocks: PTC and PYPL remain the weakest 2; MTSI is a strong isolated
  candidate that failed only the portfolio-level worst-case check — worth
  re-testing next week with a different removal pairing or a wider
  candidate set, in case a less-correlated name clears the same bar.

No `config.py` change made or proposed as a specific edit — `WATCHLIST`
and `STOCK_WATCHLIST` are unchanged. No order placed, previewed, or
cancelled at any point in this review.
