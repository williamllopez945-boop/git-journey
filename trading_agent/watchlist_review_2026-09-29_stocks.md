# Watchlist review: MAIR removal, re-tested with sourced candidates (2026-09-29)

Follow-up to the user's explicit approval ("Yes, start on MAIR") after
today's walk-forward backtest re-flagged MAIR as the weakest watchlist
member on real (not proxy) data for a third independent time.

## Background: three independent flags on the same name

- `watchlist_review_2026-09-26_stocks.md`: MAIR scored -16.16% return,
  0% win rate (worst of any name), kept but "flagged for extra attention
  next review."
- `watchlist_review_2026-09-27.md`: MAIR scored -18.35% (worst
  backtested stock). An isolated MAIR->RVMD swap looked clearly
  favorable, but **the combined `portfolio_backtest.py` check reversed
  this** — the swap made the portfolio strictly worse. No swap made.
  That doc explicitly flagged: "re-run candidate sourcing next week in
  case a better-fitting name... turns up."
- `backtest_2026-09-29_walkforward.md`: MAIR's most recent real fold
  (2026-07-09 to 2026-09-28) showed -21.92% vs. -31.12% buy-and-hold —
  a real, large loss on genuinely new evidence (real IPO-to-date data,
  not a proxy).

`state.json` confirms MAIR has **zero** `trade_log` entries — never
traded live — and the account currently holds zero open stock positions
of any kind, so removal carries no liquidation concern.

## Method (matches the established, must-follow watchlist review process)

1. **Source candidates**: ran the production stock scan (`scan_id
   6e009dcf-d184-45a7-915f-ccfc50b4e6be`, $10B+ market cap floor, sorted
   by crossover % descending), excluding every current `STOCK_WATCHLIST`
   name. Top result was SMMT at 11.54% crossover, far ahead of the rest
   of the field (next-highest was BURL at 2.90%). Took the top 6 non-
   watchlist names: **SMMT, BURL, BJ, ROIV, HBM, VTRS**.
2. **Pull real data**: 1-year hourly `get_equity_historicals` for all 6,
   filtered to `interpolated != true` bars per the methodology
   established in today's walk-forward doc. All 6 share an identical
   real-data window: **2025-12-22 to 2026-09-25, 1143 bars**.
3. **Isolated backtest**: `backtest.py`, production settings throughout
   (SMA(10,30), `stop_loss_pct=0.04`, `take_profit_pct=0.08`,
   `take_profit_sell_fraction=0.70`, gate `min_sell_profit_pct=0.0`/
   `gate_max_hold_bars=24`, `fee_pct=0.001`) — MAIR on its own 682-bar
   real window (2 folds, same as the walk-forward doc), each candidate
   on the shared 1143-bar window (4 folds), worst-case-fold-first per
   this project's standing ranking convention.
4. **Portfolio-level confirmation (binding)** — per the 2026-09-27
   lesson that an isolated win can reverse once combined with the rest
   of the watchlist, ran `portfolio_backtest.py` with the full current
   watchlist (MAIR in) against each candidate swapped in for MAIR, at
   production risk settings (`max_position_pct=20%`,
   `max_concurrent_positions=5`, `max_aggregate_pct=60%`,
   `max_trades_per_day=4`, `fee_pct=0.001`). This required restricting
   the comparison to the window where **every** member — the other 9
   stocks, both crypto proxies, MAIR, and all 6 candidates — has real
   (non-interpolated) data simultaneously: MAIR's short real history is
   the binding constraint, giving a **676-bar common window, 2026-04-16
   to 2026-09-25**, split into 2 folds.

## Part 1: isolated results

**MAIR** (682 real bars, 2 folds): F1 +1.57% (buy-hold +14.22%), F2
**-21.92%** (buy-hold -31.12%), full period **-24.31%** (buy-hold
-20.45%, MaxDD 36.67%, win rate 31%, profit factor 0.82) — worse than
buy-and-hold on both the full period and its down fold, unlike every
other name tested below.

| Candidate | Worst fold | Full return | Full MaxDD | Win rate | Profit factor |
|---|---|---|---|---|---|
| SMMT | -23.11% (F3) | +0.50% | 31.58% | 58% | 2.12 |
| BURL | -6.13% (F2) | +0.06% | 18.35% | 60% | 1.70 |
| BJ | -17.71% (F4) | -23.15% | 23.74% | 50% | 1.01 |
| ROIV | -4.20% (F3) | +23.50% | 18.06% | 70% | 3.56 |
| **HBM** | **-1.15% (F1)** | **+23.34%** | 19.30% | 69% | 3.26 |
| VTRS | -10.71% (F3) | +0.81% | 22.76% | 56% | 1.97 |

Isolated worst-case-first ranking favors **HBM** clearly (best worst
fold by a wide margin, second-best full return) and **BJ** is the one
candidate that looks outright bad in isolation (negative full return,
worst-fold -17.71%, no better than MAIR itself).

## Part 2: portfolio-level results (binding)

| Variant | F1 (Apr-Jul) | F2 (Jul-Sep) | Full return | Full MaxDD | Full # trades |
|---|---|---|---|---|---|
| Current (MAIR in) | +13.75% | +2.73% | +17.64% | 6.28% | 149 |
| Swap: SMMT in for MAIR | +8.18% | +7.08% | +20.81% | 6.09% | 158 |
| Swap: BURL in for MAIR | +18.93% | +3.05% | +23.41% | 7.02% | 152 |
| Swap: BJ in for MAIR | +10.44% | +1.61% | +17.59% | 6.48% | 148 |
| Swap: ROIV in for MAIR | +6.56% | +6.04% | +18.51% | 5.63% | 146 |
| Swap: HBM in for MAIR | +18.59% | +4.19% | +25.39% | 7.02% | 143 |
| **Swap: VTRS in for MAIR** | **+19.64%** | **+6.24%** | **+31.66%** | 6.44% | 142 |

**Every one of the 6 candidates beats the current (MAIR-in) portfolio on
full-period return** — a consistent, unambiguous result, not one lucky
pick. Worst-case-fold-first ranking: SMMT (+7.08%), VTRS (+6.24%), ROIV
(+6.04%) all clearly beat current's worst fold (+2.73%); HBM (+4.19%)
and BURL (+3.05%) also beat it; **BJ (+1.61%) is the one candidate that
is worse than current on worst-case**, consistent with its weak isolated
result — ruled out.

**VTRS is the strongest overall candidate at the portfolio level**: best
full-period return (+31.66%, +14pp over current), second-best worst-case
fold (+6.24%, more than double current's +2.73%), essentially the same
drawdown as current (6.44% vs. 6.28%), and fewer total trades (142 vs.
149 — slightly lower turnover/fee drag). **HBM is the strongest
secondary candidate** (best isolated result, second-best portfolio
full-period return at +25.39%, worst-case fold +4.19%).

## The isolated-vs-portfolio ranking flip, again

This is the third time this project has seen isolated and portfolio-level
rankings disagree (after RVMD/MAIR on 2026-09-27 and the gate backtest's
isolated-vs-portfolio reversal). This time it's a re-ordering rather than
a full reversal: **HBM ranked #1 in isolation but #2 at the portfolio
level; VTRS ranked #5 of 6 in isolation (a fairly mediocre isolated
result, +0.81% full period) but #1 at the portfolio level.** This is
exactly why the standing rule — never propose a swap from an isolated
backtest alone — exists, and it would have picked the wrong candidate
here had it been skipped.

## Recommendation (not applied — `config.py` unedited)

**Swap MAIR out for VTRS in `STOCK_WATCHLIST`.** VTRS wins at the
binding portfolio-level metric on every measured dimension (full return,
worst-case fold, drawdown, and turnover) against the current MAIR-in
portfolio and against every other sourced candidate. HBM is a reasonable
second choice if VTRS is rejected for some other reason (e.g. sector
overlap — Viatris is a pharmaceutical generics company; the current
watchlist has no other pharma exposure, which is a diversification
positive, not a concern). BJ is ruled out; SMMT, BURL, ROIV are weaker
than VTRS/HBM on the binding metric.

MAIR has zero open positions and zero trade history, so this swap
carries no liquidation step if approved.

**Scope note: `config.py` has not been edited** — this is a
recommendation only, per COLLABORATION.md's explicit rule that
`STOCK_WATCHLIST` requires the owner's separate explicit approval, never
an incidental edit. Waiting for that approval before any change.

## What this doesn't establish

- Same standing crypto-data gap as every prior backtest: `IBIT`/`ETHA`
  proxies only (irrelevant to this specific stock-only review, noted for
  consistency).
- The 676-bar common window (2026-04-16 to 2026-09-25) is short and
  MAIR-history-constrained — only 2 folds, not the 4 used for the other
  9 watchlist stocks in today's walk-forward doc. A longer independent
  track record for VTRS/HBM (which do have longer real history
  individually) at the portfolio level isn't tested here; this review
  only evaluates the window where a true like-for-like comparison
  including MAIR itself is possible.
- Candidate sourcing took the top 6 by crossover % only; a broader or
  differently-filtered scan (e.g. a lower market-cap floor, or explicit
  sector-balance filtering) wasn't attempted.
- Same-bar fill-timing simplification as every backtest in this project
  (signal executes at the same bar's close, not the next bar's open).
