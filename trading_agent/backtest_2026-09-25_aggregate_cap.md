# Aggregate-cap backtest: 50% vs 75% vs 75%+awesome-trade override (2026-09-25)

## Request

Owner raised `RISK_LIMITS["max_aggregate_position_pct"]` from 0.50 to
0.75 (plus a new "awesome trade" override to 1.00 for a `crossover_pct`
>= 5%) same-day, based on live evidence: the 50% cap bound twice in one
day (once from a live HBAR buy, once from pure appreciation of
DOT/LINK/HBAR before a BCH cross). The change shipped un-backtested at
the time — explicitly flagged as a risk-tolerance call, not something
`backtest.py`/`portfolio_backtest.py` modeled yet. Owner then asked to
"keep an eye on it and conduct a backtest." This is that backtest.

`portfolio_backtest.py` was extended (same commit) with
`awesome_trade_min_crossover_pct`/`awesome_trade_aggregate_pct` so the
override itself could be tested, not just the flat 75% cap - see that
module's docstring and `tests/test_portfolio_backtest.py` for the new
parameter's own test coverage (3 new tests, all passing).

## What was tested

**Series**: `IBIT`, `ETHA` (crypto proxies — no crypto historicals
source exists, same substitution used throughout this project's prior
backtests) plus the current 10-name `STOCK_WATCHLIST` (`CRWD`, `PANW`,
`TWLO`, `ILMN`, `IR`, `PTC`, `CHKP`, `MAIR`, `AR`, `HUBS`) — 12 series,
matching the *current* live watchlist composition exactly.

**Two independent samples**, per this project's standing practice of not
trusting a single window:
1. 372 real hourly bars (~90 days, 2026-06-29 to 2026-09-24) — the most
   recent, most representative-of-today window.
2. 935 real daily bars (2023-01-03 to 2026-09-24, ~3.7 years), split into
   3 roughly-equal regimes so a mean result can't hide a bad worst case.

**Config held fixed at production values**: `short_window=10`,
`long_window=30`, `max_position_pct=0.20`, `max_concurrent_positions=5`,
`min_strength_pct=0`, `cooldown_bars=4`, `max_trades_per_day=3`,
default stop-loss (10%)/take-profit (15%, sell 70%). Only
`max_aggregate_pct` (and the awesome-trade params) varied across the
three configs below.

## Result 1: the awesome-trade override never fired — in either sample

Across all 4 backtest runs (90-day hourly + 3 daily regimes, 935 bars
total), **zero buy trades were sized differently between "75% aggregate"
and "75% aggregate + awesome-trade override to 100%."** The override
requires both (a) the normal 75% aggregate budget to already be fully
consumed by other open positions AND (b) a fresh buy strong enough to
independently qualify as `excellent_watch`-tier (5%+ crossover) to land
at exactly the same moment — a genuinely rare conjunction that this
~4-year combined sample never produced once. This isn't evidence the
mechanism is broken (it's the same sizing code path,
`RiskManager.position_size`'s `max_aggregate_pct` argument, already
covered by unit tests) — it's evidence the *scenario* it's built for is
rare. Live, it fired zero times too (the BCH block earlier today was
correctly NOT an awesome trade — its crossover_pct was 0.23%, nowhere
near the 5% bar). Left in place, undamaging, but essentially dormant
infrastructure at current thresholds.

## Result 2: the 75% cap itself is a real, worst-case-negative tradeoff — not backtest-supported as-is

| Window | 50% (old) | 75% (new) | Delta |
|---|---|---|---|
| 90-day hourly (current) | return unknown\* | — | see note |
| Full 3.7yr daily | **+50.71%**, 9.70% dd | +37.27%, **17.54% dd** | -13.4pp return, +7.8pp dd |
| Regime 1 (2023-01 to 2024-03) | +19.71%, 5.42% dd | +20.39%, 5.23% dd | ~flat, slightly better |
| Regime 2 (2024-04 to 2025-06) | +9.22%, 7.40% dd | **+18.43%**, 9.17% dd | +9.2pp return, +1.8pp dd |
| Regime 3 (2025-06 to 2026-09, most recent) | **+12.98%**, 9.54% dd | **-4.25%**, **14.87% dd** | **-17.2pp return, +5.3pp dd** |

\*The 90-day hourly run showed 75% beating 50% (+6.26% vs +4.33%,
7.24% vs 5.70% dd) — but that window is a subset of daily Regime 3
above, which flips negative over its full span. The hourly run's short
window happened to land in a favorable stretch inside a regime that
loses money over its complete span; this is exactly the kind of
single-window trap this project's own methodology exists to catch.

**Every regime with `peak_concurrent_positions_held == 5`** (all of
them) — meaning the concurrent-positions cap, not the aggregate cap,
was consistently the practical binding constraint on *how many* assets
could be held; the aggregate cap only controls *how much* each one gets
sized to. Raising it from 50% to 75% doesn't add more diversification,
it makes each of the same ~5 positions bigger — concentrating risk
rather than spreading it, which is exactly why drawdown rose in 3 of 4
windows tested (all but Regime 1) while return only improved in 1 of 4
(Regime 2) and got meaningfully worse in the most recent, most
current-market-relevant regime.

## Assessment

This is not a clean win, and the backtest evidence points a different
direction than the live evidence that motivated the change: one day of
the 50% cap binding twice is a real signal worth acting on, but a single
day is also exactly the sample size this project's standing practice
says not to trust — and a 3.7-year, 3-regime backtest now shows the 75%
cap trading a meaningfully worse worst case (Regime 3: -17pp return,
+5.3pp drawdown) for a benefit that only shows up in one of four windows
tested. Flagging back to the owner rather than silently reverting the
already-shipped change or leaving it in place unremarked — this is a
risk-tolerance call, same as the original 50%→75% change was, and the
new evidence changes the picture materially enough to warrant another
look before the next real trade sizes against it.

**Owner decision (same day, after reviewing the above): try a value
between 60-65% rather than reverting outright or keeping 75%.** Swept
below.

## Sweep: 50/55/60/65/70/75%, same 5 windows (90-day hourly + full
   3.7yr daily + its 3 regimes)

| Window | 50% | 55% | 60% | 65% | 70% | 75% |
|---|---|---|---|---|---|---|
| hourly_90d | +4.33%/5.70dd | +4.22%/6.27dd | +4.41%/6.84dd | +13.77%/6.19dd | +12.60%/7.53dd | +6.26%/7.24dd |
| daily_full | +50.71%/9.70dd | +55.07%/8.98dd | +56.40%/9.94dd | +45.23%/16.38dd | +38.95%/17.61dd | +37.27%/17.54dd |
| regime1_2023 | +19.71%/5.42dd | +20.48%/5.54dd | +21.23%/5.67dd | +22.62%/5.54dd | +18.91%/5.38dd | +20.39%/5.23dd |
| regime2_2024 | +9.22%/7.40dd | +11.42%/7.00dd | +13.63%/7.11dd | +17.54%/6.93dd | +16.15%/9.93dd | +18.43%/9.17dd |
| regime3_2025-26 | +12.98%/9.54dd | +9.67%/10.49dd | +6.09%/11.47dd | +3.24%/12.44dd | -0.31%/13.39dd | -4.25%/14.87dd |

**Worst-case across all 5 windows, per candidate** (this project's
standing ranking rule — worst case first, not mean):

| pct | worst-case return | worst-case drawdown | mean return |
|---|---|---|---|
| 50% | +4.33% | 9.70% | +19.39% |
| 55% | +4.22% | 10.49% | +20.17% |
| **60%** | **+4.41%** | 11.47% | +20.35% |
| 65% | +3.24% | 16.38% | +20.48% |
| 70% | -0.31% | 17.61% | +17.26% |
| 75% | -4.25% | 17.54% | +15.62% |

**60% wins clearly.** It has the *best* worst-case return of all six
candidates (even beating 50%, +4.41% vs +4.33%) and a better mean than
50%/55% (+20.35% vs +19.39%/+20.17%), for a modest, bounded worst-case
drawdown increase (11.47% vs 50%'s 9.70%, +1.77pp). **65% is where the
tradeoff turns bad**: worst-case drawdown jumps sharply (11.47% → 16.38%,
+4.91pp) while worst-case return actually *drops* (+4.41% → +3.24%) —
no benefit for the added risk. 70%/75% are strictly worse than 60% on
every axis tested.

**Decision: `RISK_LIMITS["max_aggregate_position_pct"]` set to 0.60.**
`awesome_trade_aggregate_pct` (100%) and `awesome_trade_min_crossover_pct`
(5%) unchanged — the override was dormant at every aggregate-cap value
tested, not specifically tied to 75%, and remains cheap, tested
insurance for the rare case it does apply.
