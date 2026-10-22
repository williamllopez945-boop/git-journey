# Income sleeve: full real-history backtest (2026-10-07)

Requested after today's live income-sleeve cycle (`income_cycle.py`,
all four candidates held "hold - no dip signal" on real data, no
entry). That cycle only pulls a 20-trading-day window (the dip
signal's own lookback) - this re-runs the sleeve's mechanism
(`income_signals.classify_dip` + `income_exit.check_income_exit`,
via `income_backtest.income_backtest`, same production code paths,
not a re-implementation) against each candidate's **entire real
daily-close history since its own inception**, not just the last 20
days, to get a longer-window sanity check now that the sleeve is
live with real money.

## Method

`get_equity_historicals(symbols=INCOME_WATCHLIST, interval="day",
bounds="regular", start_time=2023-01-01)`, filtered to `interpolated
!= true` bars only (pre-inception padding dropped - confirms each
fund's real first trading day, see below). `income_backtest.income_backtest(
closes, starting_cash=100.0, fee_pct=0.001)` at the live production
constants (`DIP_LOOKBACK_DAYS=20`, `DIP_ENTRY_THRESHOLD=0.10`,
`INCOME_STOP_LOSS_PCT=0.15`, `INCOME_TRIM_TRIGGER_PCT=0.10`,
`INCOME_TRIM_SELL_FRACTION=0.50`), summarized with `backtest.summarize`
unchanged. 100% of cash sized per entry (not the live sleeve's
`INCOME_RISK_LIMITS` caps) - isolates signal quality, same convention
`backtest.py` itself uses.

**Binding caveat, stated plainly per `income_backtest.py`'s own
docstring and not buried below:** this models **price only** - it
does not simulate the weekly cash distribution these ETFs pay out,
which is the entire point of holding them. YieldMax-style covered-call
funds are expected to show NAV erosion in price alone (the price drop
funds the distribution); a negative price-only return here is not
proof the real (price + distribution) total return is negative. It is
a read on how well the *dip-entry/stop/trim timing mechanism* performs
on top of that structural decay - which is exactly what this sleeve's
signal is supposed to do (buy low in the decay, exit before it gets
worse), and that's the question this doc answers.

## Real history available per candidate

| Symbol | Real first bar | Real bars | Calendar span |
|---|---|---|---|
| YMAX | 2024-01-17 | 683 | ~2.7 years |
| YMAG | 2024-01-30 | 674 | ~2.7 years |
| ULTY | 2024-02-29 | 653 | ~2.6 years |
| CHPY | 2025-04-03 | 379 | ~1.5 years |

(Everything before each symbol's real first bar in the raw response
was `interpolated: true` padding - dropped, not real trading data.)

## A real limitation in `backtest.summarize()`'s win-rate, found and
corrected before reporting results below

`backtest.summarize()` pairs each `sell` with the most recent `buy`
and clears that pairing on any sell whose `reason != "take_profit"` -
written for `backtest.py`'s model, where every exit fully closes the
position. This sleeve's `trim` sells only **half** the position and
keeps the rest open; `summarize()` still clears the pairing on a trim
sell, so when the remaining half later hits its own `stop_loss`, that
sell finds no tracked entry and is **silently dropped from
`round_trips` entirely** - not counted as a win or a loss. Caught by
tracing ULTY's raw trade list bar-by-bar: `summarize()` reported 10
`round_trips` off 12 real sells; the 2 missing ones were exactly the
stop-outs on the untrimmed remainder of ULTY's 2 trims. Every trade in
`income_backtest.py`'s own simulation was independently re-verified
against `income_exit.check_income_exit` and is correct - this is a gap
in reusing `backtest.summarize()` for a partial-exit strategy, not a
bug in the trade simulation itself.

**`final_equity`/`total_return_pct`/`max_drawdown_pct` are unaffected**
- those come straight from the bar-by-bar `equity_curve`, not trade
pairing. Only win rate needed correcting, and since every sell here is
either a `trim` (always a win, by construction - it only fires on
`pct_change >= +10%`) or a `stop_loss` (always a loss, `pct_change <=
-15%`), the real win rate is simply `trim_count / total_sell_count` -
computed that way below instead of from `summarize()`'s `round_trips`.

## Results

| Symbol | Entries | Real sells (stop / trim) | Real win rate | Price-only return | Buy & hold | Max DD |
|---|---|---|---|---|---|---|
| YMAX | 6 | 6 (5 stop / 1 trim) | **16.7%** | **-56.8%** | -61.5% | 62.1% |
| YMAG | 4 | 5 (3 stop / 2 trim) | **40.0%** | **-22.5%** | -41.8% | 34.5% |
| ULTY | 11 | 12 (10 stop / 2 trim) | **16.7%** | **-80.2%** | -86.6% | 80.9% |
| CHPY | 1 | 1 (0 stop / 1 trim) | **100.0%** | **+20.8%** | +56.8% | 18.6% |

Full trade-by-trade detail saved to
`income_full_backtest_results.json` (scratchpad, not committed - raw
intermediate data; its `summary.round_trips`/`win_rate_pct` fields are
the uncorrected `summarize()` numbers, superseded by the table above).

## Observations

- **The mechanism beats buy-and-hold on price alone in 3 of 4 names**
  (YMAX, YMAG, ULTY all lose less than simply holding), which is the
  one encouraging signal here: the dip-entry + 15%-stop/10%-trim rule
  is doing real work cushioning the structural price decay, not making
  it worse. CHPY is the exception - its single trade exited via a
  10% trim far too early relative to buy-and-hold's +56.8%, but that's
  one trade on 379 bars, not a pattern.
- **ULTY is the worst performer by a wide margin** (-80.2% price-only,
  80.9% max drawdown, 16.7% real win rate). Of its 12 real sells, only
  2 were profitable trims; the other 10 were 15%-21% stop-losses,
  including stop-outs on both trims' untrimmed remainders. This is the
  strongest and most concerning finding in this doc: on real data,
  ULTY's dip signal led to a trim-level profit only twice in 653 bars,
  and both of those positions still gave the remaining half back to a
  later stop-loss.
- **YMAG is the best-behaved of the four** - 40.0% real win rate (2 of
  5 real sells were profitable trims), clearly ahead of YMAX's and
  ULTY's 16.7%. Its price-only decay (-22.5%) is also the mildest of
  the three longer-history names, consistent with it tracking a
  mega-cap-tech basket rather than ULTY's broader/choppier book. Still
  a losing mechanism in absolute terms, just the least bad of the
  three.
- **CHPY's 379 bars produced exactly one trade, a trim, with the
  position's other half still open at the end of the window** - far
  too little signal to say anything about its mechanism specifically;
  it has simply never dipped 10% off a trailing 20-day high since
  inception until the one time it did. Treat it as unproven, not
  validated, not as the sleeve's best performer.
- None of this changes today's "hold" outcome: all four currently read
  "no dip signal" on the live 20-day window regardless of what their
  multi-year history shows.

## What this doesn't establish

Same limitation the sleeve's own docs already state and this doc does
not resolve: no distribution cash flow is modeled, so none of the
price-only returns above are the real total return an actual holder
received. Every candidate's real history is still well under 3 years,
most under 2 - these are mechanism sanity-checks, not tuned parameters
the way `exit_criteria.py`'s numbers are, and ULTY's 16.7% real win
rate, while real, is also only 12 data points.

## Decision

No parameter change proposed. `INCOME_STOP_LOSS_PCT`/
`INCOME_TRIM_TRIGGER_PCT`/`INCOME_TRIM_SELL_FRACTION`/
`DIP_LOOKBACK_DAYS`/`DIP_ENTRY_THRESHOLD` are unchanged - this is a
reportable finding, not a recommendation, per this project's standing
practice of surfacing negative/concerning results plainly rather than
quietly tuning around them. **Flagging for the owner specifically**:
ULTY's 16.7% real-history win rate (2 wins in 12 completed sells, both
of which still lost the other half later) is worth knowing now that
the sleeve trades it live with real auto-execute money, even though
today's live cycle found no entry signal on any of the four
candidates.
