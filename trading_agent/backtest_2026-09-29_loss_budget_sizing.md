# Loss-budget position sizing evaluation (2026-09-29)

Fourth and last of the concrete follow-ups from the 2026-09-29 ChatGPT
second-opinion review (Slack `#voltrap-agents-work`): "Size by loss
budget, not allocation alone... evaluate 0.25-0.5% planned account risk
per trade... Treat these as hypotheses, not validated optimum settings."

## The key structural fact, before any backtest: in this system, "loss-budget sizing" IS "smaller flat allocation %"

`RiskManager.position_size` sizes a fresh entry as a **fraction of
portfolio value** (`max_position_pct`, currently 20%), not by a target
dollar risk. `volatility_sizing.py` (built 2026-09-23) exists to scale
that cap down per-asset by relative volatility, but **only applies on
the polling path** - the live scanner-based cycle that actually drives
every real trade this project has placed always sizes at the flat cap
(`PLAYBOOK.md`'s own documented scope note: "A scanner-detected
`fresh_buy_cross` still sizes at the flat cap"). Combined with
`stop_loss_pct` being a single fixed value (4%) for every asset, not
volatility-adjusted:

```
risk_pct_of_portfolio = max_position_pct x stop_loss_pct
```

is exact algebra, not an approximation, for the system as it actually
trades today. A "0.5% risk-per-trade" target and a "12.5% max_position_pct"
cap are **the same setting**, not two different sizing philosophies to
choose between:

| Target risk/trade | Implied `max_position_pct` |
|---|---|
| 0.8% (current, 20% x 4%) | 20% (current) |
| 0.5% | 12.5% |
| 0.4% | 10% |
| 0.25% | 6.25% |

So "evaluate loss-budget sizing" reduces exactly to "backtest smaller
`max_position_pct` candidates" in this codebase - no new sizing
mechanism needed to test the hypothesis's real-world effect; a genuinely
different loss-budget calculation would only diverge from this if
`stop_loss_pct` varied per asset, which it doesn't on the path that
actually trades live.

## Method

Reused the exact real, interpolated-bar-filtered dataset from
`backtest_2026-09-29_walkforward.md` (9 `STOCK_WATCHLIST` symbols +
`IBIT`/`ETHA`, 2025-12-22 to 2026-09-28, 1149 real hourly bars, MAIR
excluded to keep the aligned window - see that doc for the interpolation
finding) and the same 4 chronological folds, plus the full period.
Production settings held fixed throughout (SMA(10,30), current 4%/8%
stop-loss/take-profit, gate 0%/24h floor, `fee_pct=0.001`,
`max_concurrent_positions=5`, `max_aggregate_pct=60%` unchanged,
`max_trades_per_day=4`) - only `max_position_pct` varied, worst-case-fold-
first per this project's standing convention, portfolio-level results
treated as binding over isolated ones (same as every prior sizing/cap
backtest here).

## Result: not a clean win either way - genuinely regime-dependent

**All 11 combined, full period:** 12.5% (+30.57%, MaxDD 5.78%) actually
*beats* the current 20% (+29.06%, MaxDD 7.02%) on both return and
drawdown. But **per-fold this is not monotonic** - the opposite of a
clean "smaller is better" story:

| Variant | F1 (down mkt) | F2 | F3 | F4 | Full | Full MaxDD |
|---|---|---|---|---|---|---|
| 20% (current) | **+7.13%** | +9.63% | +14.27% | +6.24% | +29.06% | 7.02% |
| 12.5% | +3.40% | +3.55% | +10.01% | **+9.49%** | +30.57% | 5.78% |
| 10% | +2.44% | +2.92% | +8.21% | +7.85% | +24.32% | 4.81% |
| 6.25% | +1.53% | +1.83% | +5.09% | +4.87% | +14.70% | 3.04% |

**F1 (the one real down-market window) clearly favors the current 20%**
(+7.13% vs. 12.5%'s +3.40%) - smaller sizing gives up real outperformance
in exactly the regime where this strategy's downside protection matters
most. **F4 favors smaller sizing instead** (12.5%'s +9.49% beats 20%'s
+6.24%). Full-period numbers alone would have hidden this reversal - the
same "check more than one window" lesson this project has learned
repeatedly (RVMD/MAIR, the gate backtest's isolated-vs-portfolio
reversal) applies here too.

**Stocks alone scale down close to linearly with size** (54.45% -> 13.71%
full-period as allocation shrinks 20% -> 6.25%, drawdown 6.13% -> 2.86%)
- a straightforward risk/return tradeoff, no surprises.

**Crypto-proxy shows the strongest case for smaller sizing**: full-period
return is *negative* at 20% (-0.37%) and closer to flat at 6.25%
(-0.04%), while max drawdown improves dramatically (13.17% -> 4.29%) -
smaller sizing cut real losses here more than it cut gains, because the
full-period result was already a near-wash at the current size.

## A real mechanism found along the way: the aggregate cap already blocks 2 of 5 concurrent slots at 20% sizing

`max_concurrent_positions=5` allows up to 5 simultaneous positions, but
`max_aggregate_pct=60%` means at the current 20% per-position size, only
**3** positions (3 x 20% = 60%) can ever be open before the aggregate
cap itself blocks a 4th entry - 2 of the 5 nominally-allowed slots are
structurally unreachable. At 12.5%, up to 4 positions fit under the same
60% ceiling; at 6.25%, up to 5 (the full intended concurrency) fit with
room to spare. This is very likely why 12.5%'s full-period return
slightly *beats* 20%'s despite each position being smaller - more
genuinely diversified concurrent exposure, not just smaller individual
bets, on strong signal-rich stretches. This is a real, previously
unnoticed interaction between `max_position_pct` and
`max_aggregate_pct` that exists independent of any "loss budget"
framing, worth naming on its own.

## Structural check: the aggregate cap's implied worst-case loss, vs. the circuit breaker

Pure arithmetic from `config.py`'s current values, not a backtest -
ChatGPT's own calculation, verified: if every open position hit its
stop-loss on the same day (a fully correlated crash, the scenario a
diversification cap can't protect against),

```
max_aggregate_pct x stop_loss_pct = worst-case same-day loss from stops alone
        60%        x     4%      =              2.40%
```

**2.40% sits uncomfortably close to the 3.00% daily circuit breaker** -
a correlated stop-out day would burn 80% of the day's entire loss budget
on protective exits alone, leaving almost no room for any other losing
activity (a death-cross exit, a gate-floor forced exit, slippage) before
the breaker trips anyway. Tightening either `max_aggregate_pct` or
`stop_loss_pct` widens this margin; the table below shows the aggregate-cap
side of that lever (stop-loss is already backtested and adopted at 4% -
see `backtest_2026-09-28_gate_floor_and_tighter_stops.md`, not re-opened
here):

| `max_aggregate_pct` | Implied worst-case same-day loss (at 4% stop) |
|---|---|
| 60% (current) | 2.40% |
| 50% | 2.00% |
| 40% | 1.60% |
| 30% | 1.20% |

This is a structural finding, not a backtested one - it doesn't say
whether a tighter aggregate cap costs more return than it saves in
worst-case risk (that would need its own worst-case-first backtest
sweep, not done here, since ChatGPT's ask was specifically about
per-trade sizing, not the aggregate cap itself).

## Decision: hypothesis-stage evidence, not a proposal - matches ChatGPT's own framing

**No `RISK_LIMITS` change recommended from this doc alone.** The
evidence is genuinely mixed: smaller position sizing helps in some
regimes (F4, crypto-proxy full-period) and hurts in others (F1, the
exact down-market regime this strategy's risk management exists to
protect), and the one full-period portfolio "win" for 12.5% comes with
a real confound (more usable concurrent slots under the same aggregate
cap) that a from-scratch redesign of `max_aggregate_pct` could address
more directly than shrinking `max_position_pct` does. The current 20%/
60% combination was itself already worst-case-tested and adopted
deliberately (`backtest_2026-09-23.md`'s concurrent-positions sweep,
`backtest_2026-09-25_aggregate_cap.md`'s aggregate sweep) - this doc
adds new evidence to weigh against that prior work, it doesn't
supersede it on its own.

**As a genuine paper-test candidate** (ChatGPT's own suggested framing):
12.5% `max_position_pct` (0.5% implied risk/trade) is the one value
tested here with real, if mixed, portfolio-level support - not 0.25%,
which gave up return broadly without a correspondingly large worst-case
win in this data. Worth a longer live-parallel or paper-trading
comparison before any real change, not a switch flipped from this
backtest alone.

## What this doesn't establish

- Same standing crypto-data gap as every prior backtest: `IBIT`/`ETHA`
  proxies only.
- Doesn't test `max_aggregate_pct` itself as an independent lever (see
  the structural-check section) - only `max_position_pct`, per
  ChatGPT's specific ask.
- Doesn't model "reserve exposure for pending orders atomically"
  (ChatGPT's concurrency-safety point) - that's an execution-ordering
  concern in the live cycle's own order-placement sequencing, not
  something a backtest against historical closes can evaluate.
- A true volatility-adjusted (not flat) stop-loss/sizing combination
  would make "loss-budget sizing" a genuinely distinct mechanism from
  "smaller flat allocation," not the identical one found here - out of
  scope for this pass, which evaluates the system exactly as it
  currently trades live.
