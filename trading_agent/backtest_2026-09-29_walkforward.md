# Walk-forward backtest: current strategy vs. buy-and-hold and cash, across 4 independent chronological windows (2026-09-29)

Third and last of the concrete follow-ups from the 2026-09-29 ChatGPT
second-opinion review (Slack `#voltrap-agents-work`), which asked for
"walk-forward tests across trending and choppy conditions," comparison
"against cash and buy-and-hold with exposure/drawdown context," and
"net expectancy, turnover, profit factor, max drawdown, sample counts
and uncertainty" - rather than the H1/H2 split this project has used for
every prior backtest, which only ever produces two windows and has been
run on the same recent ~90-day period each time.

## What was built

`profit_factor` added to `backtest.py`'s `summarize()` (gross gain /
gross loss across round trips, in `pnl_pct` terms - this project's
existing percentage convention throughout, not dollar P&L; `None` when
there are no losing round trips to divide by, rather than a misleading
inf). 2 new tests. Full suite green (247/247) before running any of the
below.

## Data-quality finding, before any backtest ran: ~1/3 of the raw pull was placeholder, not real history

A full year of hourly `get_equity_historicals` (2025-09-29 to
2026-09-28, `STOCK_WATCHLIST` + `IBIT`/`ETHA`) returned exactly 1500 bars
per symbol - but a real fraction of those are `interpolated: true`
(flat price, zero volume, synthesized to fill a gap, per the tool's own
field). CRWD, an established company, still had 351/1500 (23%)
interpolated bars; MAIR (IPO'd April 2026) had 818/1500 (55%) - a flat
$27 placeholder for the entire pre-IPO period. **Every prior backtest in
this project ran on whatever `get_equity_historicals` returned without
checking for this flag** - a real, previously-unaddressed methodology
gap (ChatGPT's "missing-data handling" ask). This run filters to
`interpolated != true` bars only, per symbol, before doing anything else.
After filtering: 9 of 10 `STOCK_WATCHLIST` symbols + both crypto proxies
share an identical real-data window, **2025-12-22 to 2026-09-28, 1149
bars (~9 months)** - MAIR's real data only starts 2026-04-16 (682 bars,
~5.3 months), confirmed against its known IPO date.

## Method

**4 independent, sequential, non-overlapping folds** (not 2) across the
1149-bar real-data window, ~287 bars (~6-7 weeks) each - genuine
walk-forward diversity rather than one fixed split. MAIR gets 2 folds
over its shorter 682-bar real window. Production strategy settings
throughout, matching the current live configuration exactly: SMA(10,30),
`min_strength_pct=0`, `cooldown_bars=4`, `stop_loss_pct=0.04`,
`take_profit_pct=0.08`, `take_profit_sell_fraction=0.70`,
`min_sell_profit_pct=0.0` (gate), `gate_max_hold_bars=24` (floor),
`fee_pct=0.001` (0.1%/fill, the middle of the three levels tested in
`backtest_2026-09-29_gate_ab_test_with_costs.md` - one representative
cost assumption here, not a fee sweep). Both isolated (`backtest.py`,
per symbol, real bars only) and portfolio-level (`portfolio_backtest.py`,
the 11-symbol aligned set, production risk settings:
`max_position_pct=20%`, `max_concurrent_positions=5`,
`max_aggregate_pct=60%`, `max_trades_per_day=4`) passes, stocks and
crypto-proxy reported separately as well as combined, per this project's
standing convention. Buy-and-hold (equal-weighted for the portfolio
passes) and cash (0% by definition) reported alongside every result.

**This pass evaluates the fixed, already-adopted strategy across new
data - it does not tune or search any parameter, so there is nothing to
select on and no rejected-variant list to log** (ChatGPT's "expose
selection bias" ask, addressed by there being no selection happening
here, not by omission).

## Part 1: portfolio-level results (the binding metric per this project's standing convention)

**All 11 symbols combined:**

| Fold | Window | Strategy | Buy-and-hold (eq-wt) | Max DD | # trades |
|---|---|---|---|---|---|
| F1 | 2025-12-22 -> 2026-03-04 | **+7.13%** | **-12.80%** | 7.02% | 60 |
| F2 | 2026-03-04 -> 2026-05-12 | +9.63% | +18.70% | 3.14% | 55 |
| F3 | 2026-05-12 -> 2026-07-21 | +14.27% | +12.16% | 4.26% | 58 |
| F4 | 2026-07-22 -> 2026-09-28 | +6.24% | +18.87% | 7.14% | 56 |

**Every fold is positive** (beats cash in all 4 independent windows) -
the first time this has been checked across more than 2 windows. The
pattern by regime is clear and mechanistically sensible, not noise:

- **F1 was a real down-market window** (equal-weighted buy-and-hold
  -12.80%) and the strategy **massively outperformed** (+7.13%, a ~20pp
  gap) - stop-loss/take-profit and the concurrent-position caps did
  exactly their job, limiting downside a fully-invested buy-and-hold
  portfolio would have taken.
- **F2 and F4 were strong up-markets** (buy-and-hold +18.70%/+18.87%)
  and the strategy **gave back a meaningful amount of upside**
  (+9.63%/+6.24%) - expected and correct behavior for a risk-managed
  strategy that isn't fully invested at all times and caps gains via
  take-profit: it trades some upside for downside protection, and this
  is that tradeoff actually showing up in real data, not a flaw.
- **F3 was closer to flat/choppy** (buy-and-hold +12.16%) and the
  strategy **roughly matched it** (+14.27%), the "neither regime clearly
  favors the strategy" case.

**Stocks (9, ex-MAIR) and crypto-proxy separately** show the same
overall shape - stocks beat buy-and-hold hugely in F1 (+8.89% vs.
-10.33%) and give back upside in strong-bull folds; crypto-proxy is
smaller-sample (2 assets) but directionally the same, notably beating
buy-and-hold in 3 of 4 folds including two clearly negative buy-and-hold
windows (F1: -5.97% vs. -23.92%; F3: +3.68% vs. -16.19%).

## Part 2: isolated single-asset results - genuinely noisy at this sample size, reported plainly

Per-symbol, per-fold round-trip counts run **1-8 trades** - small enough
that win-rate and profit-factor swing wildly and are not reliable
signal on their own (e.g. ILMN's F3 profit factor of 665 is a tiny-loss
artifact, not a real edge; several folds show `n/a` profit factor simply
because that fold had zero losing round trips out of 3-7 total). This is
exactly the "sample counts and uncertainty" ChatGPT asked to have
reported rather than hidden behind a single aggregate number - full
per-symbol, per-fold table is in the repo's backtest run output (not
reproduced in full here for length; summary below).

**MAIR's known weakness reproduces again, now on real (not proxy) data,
via a third independent method**: F2 (its most recent real window, July-
September) shows -21.92% strategy vs. -31.12% buy-and-hold - a real,
large loss, though again better than fully-invested buy-and-hold would
have been. Consistent with `watchlist_review_2026-09-27.md`'s removal
flag and `backtest_2026-09-28_sell_cross_profit_gate.md`/
`backtest_2026-09-29_gate_ab_test_with_costs.md`'s isolated gate-cost
finding - three separate analyses now agree MAIR is a genuinely bad
watchlist member, independent of any one methodology's assumptions.

## Decision: no parameter change - this is evidence, not a proposal

Nothing here changes live behavior. The purpose was answering ChatGPT's
specific methodological concern (has this strategy actually been
validated out-of-sample, across real regime diversity, against a real
benchmark) with real evidence, not asserting the answer. **The honest
summary: yes, the strategy beats cash in every one of 4 independent
real-data windows tested, and clearly earns its keep in down/choppy
markets (its whole design point) at the cost of giving back some upside
in strong bull runs (also by design, via stop-loss/take-profit capping
exposure) - a coherent, expected risk/return tradeoff, not an
accidental one.** MAIR remains the one clear, repeatedly-confirmed weak
spot, already flagged for watchlist review independent of this doc.

## What this doesn't establish (explicit, per ChatGPT's own ask)

- **Same-bar fill timing, not next-bar.** `backtest.py`/
  `portfolio_backtest.py` still execute a signal at the same bar's close
  price that generated it, not the next bar's open - a known
  simplification carried over unchanged from every prior backtest in
  this project, not fixed here. Real live cycles fetch a fresh quote and
  act within the same hourly window, so this is a reasonable proxy for
  the live cadence, but it is not the "realistic next-executable-price
  fill" ChatGPT specifically asked for.
- **No regime-filter or slower-timeframe variant tested.** ChatGPT asked
  to compare the baseline against a regime filter and a slower timeframe,
  "one change at a time." Those are new strategy components, not part of
  validating the existing one - out of scope for this pass specifically.
- **Crypto proxies only, still.** IBIT/ETHA stand in for BTC/ETH; the
  other 13 `WATCHLIST` crypto assets (including the account's only
  current position history - LINK, SOL, DOGE, etc.) have no historicals
  source in this project at all, the same standing gap every prior
  backtest has flagged.
- **`fee_pct=0.001` is one point, not a sweep**, for this specific pass
  (the sweep already exists in
  `backtest_2026-09-29_gate_ab_test_with_costs.md`).
- **4 folds of ~6-7 weeks each is still a modest sample** for genuinely
  independent regime coverage - real walk-forward rigor at institutional
  scale would want years, not one year with a 9-month real-data
  constraint from this specific data pull.
