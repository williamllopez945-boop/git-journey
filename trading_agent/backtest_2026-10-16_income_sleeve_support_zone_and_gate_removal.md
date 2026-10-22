# Income sleeve: support-zone signal + entry-gate removal — 2026-10-16

## Context

Owner request (real-money, live account): remove the income sleeve's
ex-dividend timing gate, liquidity/spread filter, and post-exit cooldown
from the live entry path — "any entry is good based on analysis and
data." In the same request, add a real support-zone confirmation to the
entry signal ("good low with good support zones," not just the existing
rolling-range percentile), loosen the risk caps so more, smaller
positions can be open at once, and keep the exit side unchanged (15%
stop-loss, 10% trim, both still in effect).

This doc covers the entry-signal change only — the gate removal itself
has no backtest surface (a timing/liquidity/cooldown gate shifts *when*
an already-qualifying entry fires, not whether the underlying signal is
sound; income_backtest.py has never modeled those gates at all, by
design, same as before this change).

## What changed in the signal

`income_signals.py` adds:
- `near_support(closes, lookback_days=60, tolerance_pct=0.03)` — true
  when today's close is within 3% of the lowest close over the trailing
  60 days (a longer horizon than the existing 20-day dip percentile,
  meant to confirm the dip is a real support level, not just a short-term
  wiggle).
- `classify_entry(closes)` — `"dip_buy"` only when **both**
  `classify_dip` (unchanged, bottom 10% of the 20-day range) **and**
  `near_support` agree. This replaces `classify_dip` as `income_cycle.py`'s
  live entry signal.

## Method

`income_backtest.py` gained a `require_support` flag (default `False`,
reproduces the original dip-only behavior unchanged) that, when `True`,
applies the same `near_support` check the live signal now uses. Ran both
configurations (`require_support=False` = old, `require_support=True` =
new) over real daily closes for all 15 current `INCOME_WATCHLIST` names,
fee_pct=0.001, starting_cash=$100, worst-case-first per this project's
standing comparison rule.

**Known, stated limitation (same as every prior income-sleeve
backtest):** this models price action only, no distribution cash flow.
These are weekly-distribution funds whose entire appeal is the
distribution, which structurally marks the share price down every week
independent of any adverse move — the negative returns below
substantially understate real total return. Treat this as a mechanism
sanity-check (does the support filter help or hurt, worst-case-first),
not a tuned, proven parameter. Several names also have under 1.5 years
of real history (MINY: 160 bars, GOOW/AMDW/QDTY: ~310-420 bars) — thin
samples, same caveat every prior sleeve backtest has carried.

## Results (price-only, fee_pct=0.001)

| symbol | bars | old trades | old return % | old max DD % | new trades | new return % | new max DD % |
|---|---|---|---|---|---|---|---|
| YMAX | 690 | 12 | -57.89 | 62.11 | 12 | -56.52 | 59.20 |
| YMAG | 681 | 9 | -24.79 | 34.46 | 8 | -33.34 | 39.49 |
| ULTY | 660 | 25 | -81.71 | 81.71 | 22 | -80.75 | 81.94 |
| CHPY | 386 | 2 | 12.34 | 18.61 | 2 | 15.20 | 18.89 |
| GPTY | 435 | 4 | -8.94 | 25.83 | 5 | 6.95 | 18.52 |
| AMDW | 310 | 5 | 63.97 | 25.08 | 5 | 66.20 | 24.64 |
| GOOW | 310 | 2 | 5.16 | 17.07 | 4 | -7.46 | 19.43 |
| NVDW | 417 | 4 | -1.23 | 23.90 | 8 | 4.21 | 16.93 |
| LFGY | 441 | 15 | -51.77 | 54.13 | 10 | -46.46 | 50.64 |
| QDTY | 420 | 4 | -10.51 | 19.97 | 4 | -10.28 | 21.86 |
| RDTY | 406 | 5 | -29.33 | 29.96 | 3 | -23.05 | 26.89 |
| SDTY | 425 | 4 | -10.39 | 16.87 | 1 | -9.18 | 15.86 |
| MINY | 160 | 4 | -14.47 | 26.65 | 3 | -15.61 | 20.79 |
| SLTY | 290 | 9 | -54.98 | 55.58 | 7 | -47.88 | 47.88 |
| TOPW | 281 | 5 | -36.75 | 42.19 | 3 | -23.50 | 27.59 |

Worst-case return: old -81.71% (ULTY) vs. new -80.75% (ULTY) — mildly
better.
Mean return across all 15 names: old -20.09% vs. new -17.43% — mildly
better.

Mixed at the individual-symbol level (GOOW and MINY get modestly worse;
GPTY, NVDW, TOPW, RDTY, SLTY improve meaningfully; ULTY/YMAX/LFGY improve
only slightly on the biggest losers). No symbol gets dramatically worse.

## Verdict

**Mild net positive, worst-case-first, on a price-only basis** — the
support-zone filter doesn't fix this sleeve's price-only track record
(these are real losses once the distribution income this strategy exists
for is left out), but it also doesn't make the worst cases worse, and it
improves the aggregate mean. Combined with the owner's explicit choice
to size each entry much smaller (see `config.py`'s updated
`INCOME_RISK_LIMITS`), this is adopted for the live signal per owner
request, with the price-only-backtest and thin-history caveats above
carried forward plainly, same as every prior income-sleeve change.

## Not backtested here (and why)

- Ex-dividend gate removal, liquidity filter removal, cooldown removal:
  no backtest surface, as explained in Context above.
- `INCOME_RISK_LIMITS` sizing changes (smaller per-entry, higher
  aggregate ceiling): position-sizing/risk-cap changes, not a signal
  change — `income_backtest.py` always uses 100% of available cash per
  entry regardless of the live caps (see its own module docstring), so
  it can't evaluate a sizing change at all.
