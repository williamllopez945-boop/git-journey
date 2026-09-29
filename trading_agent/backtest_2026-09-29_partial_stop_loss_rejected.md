# Partial (70%) stop-loss, once per position — rejected (2026-09-29)

Owner proposed changing stop-loss from a full 100% exit to a 70%
partial exit (mirroring take-profit's existing shape), firing once per
position. Backtested before any implementation, per COLLABORATION.md's
rule that a strategy parameter change needs real backtesting first.

## The real mechanism concern, before any backtest ran

Once a 70% stop-loss fires and doesn't refire, the remaining 30% has no
further stop-loss protection for that position - it stays exposed until
a death-cross or the 24h gate floor eventually closes it. In a real
downtrend that gap can cost more than a clean full exit would have.

## Method

Standalone scratch implementation (`check_exit`/`backtest`/
`portfolio_backtest` variants with a `stop_loss_sell_fraction` +
`stop_loss_already_taken` flag added, mirroring `take_profit`'s existing
mechanics exactly) - not a change to production code. Same data as
today's fresh walk-forward re-run (12 symbols incl. `VTRS`, 1149-bar
real aligned window, 4 folds), same production settings otherwise
(SMA(10,30), 4% SL, 8% TP/70% partial, gate 0%/24h, `fee_pct=0.001`,
production risk limits for the portfolio pass).

## Result: worse in the down-market fold, not clearly better anywhere else

**All 12 combined, portfolio-level (binding metric):**

| Variant | F1 (down-mkt) | F2 | F3 | F4 | Full MaxDD |
|---|---|---|---|---|---|
| 100% SL (current) | **+10.84%** | +8.97% | +12.16% | +6.34% | 6.44% |
| 70% SL (proposed) | +3.34% | +12.40% | +10.56% | +9.87% | 6.71% |

F1 - the one real down-market fold, exactly the regime stop-loss exists
to protect - drops from +10.84% to +3.34%, confirming the mechanism
concern above. F2/F4 favor the partial version instead (giving back
less upside since a smaller chunk gets stopped out), and full-period
drawdown is slightly worse, not better, under the partial version.
Stocks alone show the same F1 pattern (+10.82% -> +4.71%).

**Isolated per-symbol, full period**: mostly lower under 70% SL (CRWD
66.65%->41.55%, PANW 47.69%->15.27%, TWLO 73.64%->40.78%, IR
15.85%->5.42%, CRDO 87.97%->49.85%, AR 14.80%->8.54%, PYPL
0.04%->-7.61%) - a broad, consistent pull-down, not a clean tradeoff.
Worst-fold comparison is mixed (a few names improve slightly, several
get worse, e.g. IR -7.21%->-14.84%, PYPL -6.51%->-14.45%).

## Decision: rejected, not adopted

Worst-case-first (this project's standing ranking rule), the partial
stop-loss weakens exactly the protection it exists to provide, in
exactly the regime that matters most, without a consistent full-period
upside to offset it. No code change made - `exit_criteria.py`,
`backtest.py`, `portfolio_backtest.py` are all unchanged.

## What this doesn't establish

- Only one partial fraction (70%, matching take-profit's) was tested -
  a different fraction, or a partial stop-loss paired with a *tighter*
  re-entry trigger for the remaining position, wasn't tried.
- Same standing gaps as every backtest this session: crypto proxies
  only, same-bar fill timing, one fee level not a sweep.
