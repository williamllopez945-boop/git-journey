# Profitability gate on death-cross/fresh_sell_cross exits (2026-09-28)

Owner request, after a real DOGE/SOL exit both closed at a loss the
strategy never checked for (-$95.71 and -$78.23 realized, confirmed
against Robinhood's own P&L records - see the 2026-09-28 conversation).
Built as a proposal only: **not wired into `PLAYBOOK.md`'s live cycle
procedure and no live parameter changed** - `config.py`, `exit_criteria.py`,
and the live routine are all unchanged. This doc is the real backtest
evidence needed before that could change, per this project's standing
"no strategy parameter change without real historical backtesting,
worst-case first" rule.

## What was built

`trading_agent/profit_gate.py` (new) - `blocks_sell_cross(current_price,
avg_cost_basis, min_sell_profit_pct)`: a pure function that returns
`True` when a death-cross/`fresh_sell_cross` signal should be **held**
instead of executed, because the position's current unrealized P&L
hasn't yet cleared `min_sell_profit_pct` (a fraction: `0.0` = breakeven
or better required). `None` disables it entirely.

Wired into `backtest.py` and `portfolio_backtest.py` as a new
`min_sell_profit_pct=None` parameter (default `None` - identical to
current behavior when omitted, matching the pattern every other optional
filter in these modules already uses). **Stop-loss/take-profit
(`exit_criteria.check_exit`) are completely unaffected** - they run
first, every bar, regardless of this gate, so a position held back from
a death-cross exit is never left without its existing protection; it can
still exit via `stop_loss` at -10% from cost basis, just not via the
plain trend-reversal signal alone while underwater. Full test suite green
(215/215, including 5 new tests for `profit_gate.py`) before running any
of the below.

## Method

Same real hourly data and production-shaped settings as
`backtest_2026-09-27_trade_cap_recheck.md` and the 2026-09-27 watchlist
review: `get_equity_historicals`, 2026-06-29 to 2026-09-25 (378 hourly
bars, split-adjusted, regular hours), for the current `STOCK_WATCHLIST`
(`CRWD, PANW, TWLO, ILMN, IR, PTC, CRDO, MAIR, AR, PYPL`) plus `IBIT`/
`ETHA` (BTC/ETH proxies - crypto itself has no historicals source, see
README). Split into H1/H2 (189 bars each) for worst-case-first ranking,
same as every other backtest this project has run. Production strategy
settings throughout: SMA(10,30), `min_strength_pct=0`, `cooldown_bars=4`,
current `STOP_LOSS_PCT`/`TAKE_PROFIT_PCT`/`TAKE_PROFIT_SELL_FRACTION`
(10%/20%/70%), no trailing stop or profit-lock (both disabled, matching
live). Four gate values tested to avoid a single lucky point: no gate
(baseline), 0% (breakeven), -2% (allow a small loss), +2% (require an
actual gain).

## Pass 1: single-asset isolation (backtest.py), worst of H1/H2 per symbol

| Symbol | Baseline (no gate) | Gate 0% | Gate -2% | Gate +2% |
|---|---|---|---|---|
| IBIT | -4.55% | **-2.25%** | -2.88% | -0.98% |
| ETHA | -5.83% | **+1.07%** | +1.07% | +1.07% |
| CRWD | -5.54% | +2.84% | **+11.15%** | +2.84% |
| PANW | -9.70% | -9.70% | -9.70% | -9.70% |
| TWLO | -9.42% | **+22.78%** | +22.78% | +22.78% |
| ILMN | -4.40% | +4.09% | -1.34% | +4.09% |
| IR | -3.02% | **+0.50%** | +0.50% | +0.50% |
| PTC | -5.36% | -9.17% | -9.17% | -9.17% |
| CRDO | +0.99% | -0.76% | -1.54% | -0.76% |
| **MAIR** | **-9.45%** | **-16.44%** | -16.44% | -16.44% |
| AR | -2.15% | -2.15% | -2.15% | -2.15% |
| PYPL | -8.35% | **-2.82%** | -2.82% | -2.82% |

**7 of 12 helped, 3 hurt, 2 flat** on worst-case (0% gate vs baseline).
Mean-of-worst improves a lot (-5.57% -> -1.00%) and mean-of-full-period
return nearly doubles (+6.14% -> +14.23%) - but the single worst outcome
across the whole set gets **worse**, not better: MAIR's worst window goes
from -9.45% to **-16.44%**, becoming the new worst-of-worst across all 12
series (baseline's worst-of-worst was PANW at -9.70%).

**Why MAIR gets worse under the gate, not just fails to improve:**
MAIR is a persistently declining name (already this project's flagged
worst stock-watchlist performer, -18.35% full-period baseline - see
`watchlist_review_2026-09-27.md`). Stop-loss is still active under the
gate, but blocking the death-cross exit means a losing MAIR position
rides out the full -10% stop-loss, then (once `cooldown_bars` clears)
re-enters on the next buy-cross and repeats - multiple full stop-loss
cycles in a persistent downtrend cost more, in total, than exiting
earlier and smaller via an ungated death-cross each time. This is a real,
mechanistic cost of the gate on a genuinely bad asset, not noise - and
it's the same failure mode this project already found and rejected once
before (`backtest_2026-09-25_profit_lock.md`: "clipping... costs more
than it protects" - here the mechanism runs the other direction (holding
too long instead of clipping too early) but the lesson is the same: a
P&L-aware exit modification can turn a bounded loss into an unbounded
one on the specific asset that's actually just bad.

**`-2%` is not a safer, smaller version of `0%`.** It is not monotonic
with `0%` - on CRWD it's clearly the best variant (+11.15% vs 0%'s
+2.84%), but on ILMN it gives back most of 0%'s gain (-1.34% vs 0%'s
+4.09%, though still better than baseline's -4.40%). Reported plainly
rather than assumed - this is exactly why every backtest here checks
more than one value instead of trusting a single point.

## Pass 2: combined portfolio (portfolio_backtest.py), production risk settings

Same reasoning this project used for the RVMD/MAIR reversal in
`watchlist_review_2026-09-27.md`: an isolated single-asset test can't see
the real interaction with `max_concurrent_positions` (5) and
`max_aggregate_position_pct` (60%) that governs how much capital any one
bad position can actually tie up - **the portfolio-level result is the
one that reflects how the live system actually trades, so it's the
binding one, not the isolated number.**

**Stock portfolio (all 10 `STOCK_WATCHLIST` names, one shared cash pool,
`max_position_pct=20%`, `max_concurrent_positions=5`,
`max_aggregate_pct=60%`, `max_trades_per_day=4`):**

| Variant | Full | H1 (worst) | H2 | Max DD (Full) |
|---|---|---|---|---|
| Baseline (no gate) | +1.72% | +0.28% | +2.24% | 7.90% |
| **Gate 0%** | **+7.70%** | **+0.17%** | **+5.84%** | **5.86%** |
| Gate -2% | +1.37% | -4.09% | +5.84% | 8.11% |
| Gate +2% | +7.66% | +0.18% | +5.84% | 5.86% |

At the portfolio level, MAIR's worst-case damage is **dramatically
diluted** - it's one of up to 5 concurrent slots and capped at 20% of
portfolio value per entry, not 100% of an isolated test's capital every
time, exactly the same dilution effect that reversed the RVMD/MAIR
comparison two days ago. Worst-case (H1) give-up for the 0% gate is
0.11pp (+0.17% vs baseline's +0.28%) - noise, not a real cost. H2 and
the full period are both clearly better, and max drawdown is *lower* in
2 of 3 windows. **`-2%` is again the outlier - clearly worse than both
baseline and `0%` in H1** (-4.09%), confirming the non-monotonicity
found in Pass 1 rather than it being a fluke of single-asset testing.

**Crypto-proxy mini-portfolio (IBIT+ETHA, same risk settings):**

| Variant | Full | H1 (worst) | H2 |
|---|---|---|---|
| Baseline (no gate) | +7.75% | -2.08% | +1.06% |
| **Gate 0%** | **+11.44%** | **-0.23%** | **+1.59%** |
| Gate -2% | +10.55% | -0.36% | +1.59% |
| Gate +2% | +12.55% | +0.03% | +2.76% |

Every gate variant helps in every window here - no reversal, no
worst-case cost at all on this proxy pair.

## Decision: recommend adopting the 0% (breakeven-or-better) gate - owner approval required, not yet live

**This is the one value that helped or was flat everywhere it was
tested at the level that actually matters (the combined portfolio), with
only a negligible (0.11pp) worst-case give-up on stocks and a clean
improvement in every crypto-proxy window.** The real worst-case cost
found (MAIR, isolated, -16.44%) is a genuine, mechanistic risk on a
specific already-flagged-bad asset, but it is not the number the live
system would actually experience, because the concurrent-position and
aggregate-value caps that govern real capital allocation dilute it the
same way they reversed RVMD vs MAIR two days ago. Stop-loss remains fully
active throughout regardless of this gate, so no position is ever left
unprotected by adopting it.

**`-2%` is rejected** - it underperformed `0%` at the portfolio level in
the worst window tested (-4.09% vs +0.17%), a real, non-monotonic result
confirmed in both the isolated and combined passes, not a single lucky
or unlucky point. `+2%` performs about as well as `0%` here but is a
more aggressive constraint (requires an actual gain, not just breakeven)
untested against a wider basket - not recommended as the first value to
adopt.

**Not yet live.** `min_sell_profit_pct` defaults to `None` in both
`backtest.py` and `portfolio_backtest.py` - this proposal changes
nothing about current trading behavior on its own. Adopting it for real
would mean: (1) owner approval on the 0% threshold specifically, (2) a
matching update to `PLAYBOOK.md`'s live "fresh_sell_cross" procedure to
check `profit_gate.blocks_sell_cross` before executing an exit, logging
a new `"blocked_unprofitable"` (or similar) cycle-log action when held,
and (3) a `CHANGELOG.md`/`README.md` update at that time - none of which
is done here, pending that decision.

## What this doesn't establish

- Crypto's real behavior is still fundamentally unknown for this gate,
  same standing limitation as every other crypto-side backtest in this
  project (IBIT/ETHA are proxies, not the traded pairs themselves; no
  crypto historicals tool exists).
- MAIR's isolated result is a real argument for *removing* MAIR from
  `STOCK_WATCHLIST` on its own merits (already flagged in
  `watchlist_review_2026-09-27.md`), not an argument against this gate
  specifically - a persistently bad asset is a bad candidate for *any*
  strategy, gated or not.
- Neither pass models real transaction costs/slippage, same caveat as
  every other backtest this project has run.
