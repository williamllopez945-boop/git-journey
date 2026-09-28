# Gate floor + tighter stop-loss/take-profit (2026-09-28)

Owner request, after watching the profit gate hold XLM/CRV/AVAX through the
sell-off earlier today: (1) should the gate have a floor so it can't hold a
losing position forever, and (2) test tighter stop-loss/take-profit. Owner's
explicit direction: floor = "whichever is best from backtesting", stop-loss/
take-profit = "tighter (smaller moves)".

## What was built

`profit_gate.gate_floor_should_force_exit(current_price, avg_cost_basis,
bars_since_blocked, max_hold_bars=None, price_floor_pct=None)` - a new, separate
check from `blocks_sell_cross`. Important mechanical point: `blocks_sell_cross`
is only ever consulted once, at the bar a death-cross signal actually fires
(`sma_crossover_signal`/`scanner_signals.classify` report "sell" as a one-time
event, not a continuing state) - so once a signal is blocked, nothing re-checks
the decision again until price recovers to `min_sell_profit_pct` or the
position hits `stop_loss_pct`. The floor is therefore a separate, every-bar
check that runs for as long as a position stays in that blocked state,
independent of whether a fresh sell signal exists that bar. Two independent
floor types, either or both settable:

- `max_hold_bars`: force the exit once the position has been stuck this many
  bars, regardless of P&L (a time-based backstop).
- `price_floor_pct`: force the exit once the loss reaches this threshold
  (typically tighter than `stop_loss_pct`) - a secondary, tighter stop that
  only applies to a position already stuck under the gate.

Wired into `backtest.py` and `portfolio_backtest.py` via new
`gate_max_hold_bars`/`gate_price_floor_pct` parameters (both `None` by
default - unchanged pre-floor behavior). A forced floor exit logs reason
`"gate_floor"`, counts toward `max_trades_per_day` like any other sell, and
does not fire on a position that was never blocked in the first place. Full
test suite green (239/239, 16 new tests: 9 for `gate_floor_should_force_exit`
plus integration tests in both backtest modules) before running any of the
below.

## Method

Real hourly data, `get_equity_historicals`, extended through **today**
(2026-06-29 to 2026-09-28, 381 bars - a few days past the last profit-gate
backtest's window, deliberately including the recent sell-off this whole
discussion started from) for `STOCK_WATCHLIST`
(`CRWD, PANW, TWLO, ILMN, IR, PTC, CRDO, MAIR, AR, PYPL`) plus `IBIT`/`ETHA`
(BTC/ETH proxies). Split H1/H2 (190/191 bars) for worst-case-first ranking,
same as every other backtest this project has run. Production strategy
settings throughout: SMA(10,30), `min_strength_pct=0`, `cooldown_bars=4`,
gate at the current live value (0%, breakeven). Both isolated (`backtest.py`,
12 series) and portfolio-level (`portfolio_backtest.py`, stocks and
crypto-proxy separately, production risk settings: `max_position_pct=20%`,
`max_concurrent_positions=5`, `max_aggregate_pct=60%`, `max_trades_per_day=4`)
passes run throughout, per this project's standing "isolated can reverse at
the portfolio level" rule.

## Part 1: gate floor, tested first at the (then-current) 10%/20% stop-loss/take-profit

| Variant | Fires (12 series) | Isolated Full worst | Isolated H2 worst | Stocks portfolio H1 (worst) | Crypto portfolio H1 (worst) |
|---|---|---|---|---|---|
| No floor (baseline) | - | -35.87% (MAIR) | -17.92% (MAIR) | +0.46% | -0.26% |
| Time floor 24h | 11 | -31.78% | -17.92% | +0.04% | +0.16% |
| Time floor 48h | 5 | -35.87% | -17.92% | -0.09% | +0.07% |
| Time floor 72h | 3 | -35.87% | -17.92% | +0.46% | -0.22% |
| Price floor 3% | 29 | -26.30% | -11.50% (PYPL) | **-4.73%** | +8.57% |
| Price floor 5% | 19 | -28.72% | -8.22% | **+3.31%** | -0.26% |
| Price floor 7% | 13 | -31.05% | -12.29% | +1.46% | -0.26% |

3% price floor clearly rejected (stocks portfolio worst case goes negative,
-4.73%). Time floors 24-48h cost real return with modest benefit; 72h barely
fires (3 times total) so it's mostly inert. Price floor 5% looked best at
this stop-loss/take-profit level - but **this changed once the stop-loss
itself got tightened** (see Part 3).

## Part 2: stop-loss/take-profit tightening sweep (floor=none, gate=0%)

Swept pairs preserving the current 1:2 risk/reward ratio (the same reasoning
`backtest_2026-09-25_stop_take.md` used to adopt 10%/20% in the first place),
worst-case-first:

| SL/TP | Isolated Full worst | Isolated H1 worst | Isolated H2 worst | Stocks H1 (worst) | Crypto H1 (worst) |
|---|---|---|---|---|---|
| 10%/20% (current) | -35.87% | -12.27% | -17.92% | +0.46% | -0.26% |
| 8%/16% | -33.80% | -16.34% | -14.38% | +1.56% | -0.26% |
| 6%/12% | -28.36% | -13.31% | -11.44% | +4.57% | -0.26% |
| 5%/10% | -28.70% | -16.78% | -8.19% | +4.76% | -0.26% |
| **4%/8%** | **-25.59%** | -14.60% | **-6.63%** | **+5.63%** | **+0.42%** |
| 3%/6% | -11.82%* | -11.77%* (TWLO) | -7.99%* (PYPL) | -1.00% | -1.92% |
| 2.5%/5% | -8.68%* | -11.07%* (TWLO) | -7.82%* (PYPL) | +0.50% | -2.44% |
| 2%/4% | -8.44%* | -11.38%* (IBIT) | -3.95%* | +0.98% | -2.95% |

\* The isolated Full-window number keeps improving below 4%/8%, but that's
misleading on its own - the worst-performing *symbol* shifts from MAIR
(the project's already-flagged chronic underperformer) to TWLO/IBIT, meaning
normally-fine assets start taking real whipsaw losses. The portfolio numbers
show this plainly: both stocks and crypto worst-case (H1) **reverse and get
worse** below 4%/8% (crypto H1 down to -2.95% at 2%/4%, worse than the
10%/20% baseline). This is the same "clipping a position before a trend
plays out costs more than it protects" pattern this project has found before
(the rejected trailing-stop and profit-lock studies).

**4%/8% is the tightest point that still improves the worst case on both
portfolios simultaneously** - the sweet spot, not an endpoint of a monotonic
trend. It's also the single best isolated H2 worst-case and best stocks-H1
worst-case of every candidate tested, tight or loose.

## Part 3: floor re-checked at the new 4%/8% baseline

A price floor becomes mechanically pointless once the stop-loss itself is
tightened to 4% - a 4-5% price floor never gets a chance to fire before the
now-tighter stop-loss already would have (confirmed directly: 5%/10% + a 5%
price floor produces byte-identical results to 5%/10% alone, since the floor
equals the stop-loss threshold and never wins the race). Testing price
floors *below* the new 4% stop-loss instead:

| Variant | Stocks H1 (worst) | Crypto H1 (worst) | Crypto maxDD |
|---|---|---|---|
| No floor | +5.63% | +0.42% | 2.05% |
| Price floor 1.5% | +0.62% | -1.56% | 3.58% |
| Price floor 2% | -0.07% | -1.69% | 3.98% |
| Price floor 2.5% | -0.83% | -1.75% | 4.04% |
| Time floor 12h | +7.08% | -0.18% | 2.38% |
| Time floor 18h | +7.11% | +0.67% | 2.32% |
| **Time floor 24h** | +5.63% (unchanged - never fires here) | **+0.85%** | **1.68%** |
| Time floor 30h | +5.63% (unchanged) | +0.21% | 2.05% |
| Time floor 36h | +5.63% (unchanged) | +0.11% | 2.10% |

Any price floor now makes things **worse** at this tighter stop-loss - the
gate's "held too long at a shallow loss" problem mostly no longer exists once
the real stop-loss is already close, so a secondary price floor just adds
whipsaw cost with no benefit. A **24-hour time floor** is the one setting
that improves the true worst window (crypto H1: +0.42% -> +0.85%, max
drawdown 2.05% -> 1.68%) without ever touching the stocks portfolio (it
simply never fires there in this window - a real position gets resolved by
the tighter stop-loss or recovery well before 24 hours in this data) - a
genuinely free improvement, not a tradeoff, unlike the price-floor options.
12h/18h show a better stocks number but a worse-or-flat crypto number - a
real tradeoff between the two portfolios rather than a clean win, so 24h
(better on the binding worst-case metric, neutral everywhere else) was
chosen over them.

## Decision: recommend adopting STOP_LOSS_PCT=4%, TAKE_PROFIT_PCT=8%, and a 24-hour gate time floor - owner approval required, not yet live

- `STOP_LOSS_PCT`: 10% -> 4%
- `TAKE_PROFIT_PCT`: 20% -> 8% (keeps the 1:2 ratio; `TAKE_PROFIT_SELL_FRACTION`
  stays 70%, untested for change this round)
- New: a 24-hour (`gate_max_hold_bars=24`) time floor on the profit gate -
  price floors were tested and rejected at this stop-loss level

All three numbers are the ones that actually improved the binding worst-case
metric (portfolio-level, both books) rather than just the flattering
full-period mean, and all three held up against neighboring values rather
than being a single lucky point.

**Not yet live.** No code path currently defaults to these values -
`exit_criteria.py`'s `STOP_LOSS_PCT`/`TAKE_PROFIT_PCT` and `profit_gate.py`
are unchanged; `backtest.py`/`portfolio_backtest.py`'s new
`gate_max_hold_bars`/`gate_price_floor_pct` parameters default to `None`.
Adopting this for real would mean: (1) owner approval on these specific
numbers, (2) updating `exit_criteria.py`'s live constants and adding a tuned
`GATE_MAX_HOLD_BARS` default to `profit_gate.py`, (3) wiring the time floor
into `PLAYBOOK.md`'s live per-position exit procedure - this needs new
persisted state (a "blocked since" timestamp per asset in
`position_state.json`, since the live cycle has no bar index to count from,
only real wall-clock time between hourly firings) and a new `"gate_floor"`
cycle-log action, (4) `README.md`/`CHANGELOG.md` updates - none of which is
done here, pending that decision.

## What this doesn't establish

- Same standing crypto-data gap as every other backtest here: IBIT/ETHA are
  proxies, not the actual traded pairs (XLM/CRV/AVAX/etc. have no
  historicals source at all).
- `TAKE_PROFIT_SELL_FRACTION` (70%) was held fixed throughout - a genuinely
  independent axis this sweep didn't re-test at the new, tighter levels.
- Neither pass models real transaction costs/slippage. A 4%/8% stop-loss/
  take-profit means meaningfully more trades than 10%/20% - worth a plain
  reminder that real crypto/equity spreads and fees eat into a tighter
  system's edge more than a looser one's, even though this backtest can't
  quantify that directly.
- The 24h time floor's benefit is real but small (crypto worst-case
  +0.42%->+0.85%) and only demonstrated on the IBIT/ETHA proxy pair - it
  never fired in the stocks data at all in this window, so its stocks-side
  behavior is untested by real firings, only proven not to hurt.
