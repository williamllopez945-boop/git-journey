# SOXL day-trade proof of concept: architecture, data and validation plan

Status: **plan only, no code, no paper loop, no broker connection.** Written
2026-10-26 in response to the build request in `#voltrap-agents-work` (09:42 CDT) and
the owner's go-ahead the same day, with this scope set by the owner: **one share of
SOXL at a time, as a proof of concept.** Nothing here changes `config.py`, any live
routine, or any live strategy. Anything beyond backtest and paper work needs a
separate, explicit owner decision.

## 1. Scope and guardrails

- **Instrument and size:** SOXL (Direxion Daily Semiconductor Bull 3X ETF), long only,
  **at most 1 share open at a time.** At about $87 per share that is roughly 8.6% of the
  account, so a single share already exceeds the income sleeve's 6% per-position cap.
  This strategy therefore gets its own limits and must not draw on another sleeve's
  budget.
- **Mode:** backtest, then paper. The strategy code makes no brokerage calls and holds
  no credentials; as with every other strategy here, the agent (not the code) calls
  brokerage tools. Live order capability is out of scope and disabled by default.
- **Separate manual enablement:** any live use needs (1) an explicit owner decision,
  (2) a new, separately named switch in config that defaults to off and is not flipped
  by any routine, and (3) a kill-switch file/flag the module checks before every
  action. None of that is built in this phase.
- **Honest outcome rule:** if the strategy does not beat the baselines after costs and
  out-of-sample, the report says so and it is not presented as profitable.
- **Repo rules still apply:** isolated task branch and worktree, handoff note, full test
  suite at the reviewed head, no runtime state committed, review before merge.

## 2. Data source: what the brokerage history actually gives us

Probed on 2026-10-26 with the brokerage historicals tool (read-only):

| Interval | Probe | Result |
|---|---|---|
| Daily | 2021-10-26 to 2021-11-02 | Real bars. Daily history reaches the start of the cited backtest window. |
| 5-minute | 2026-04-28 and 2026-07-28 | Real bars with volume. |
| 5-minute | 2026-01-28 | **Interpolated flat bars, zero volume.** |
| 30-minute | 2024-10-28 | Interpolated flat bars. |
| Hourly and 5-minute | 2025-10-28 | Interpolated flat bars. |

Consequences:
1. **Daily:** the 5-year daily study (the Oct 26, 2021 to Oct 23, 2026 backtest in the
   request) can be reproduced from daily bars, split-adjusted by default; dividend
   adjustment ("all") is only offered for daily or coarser bars.
2. **Intraday:** genuine intraday history appears to start somewhere between
   2026-01-28 and 2026-04-28, so **at most about 6 to 9 months of real intraday bars.**
   Interpolated bars carry no information and must be filtered out. A multi-year
   day-trade backtest is not possible from this source.
3. **First data task:** find the exact first date with non-interpolated 5-minute and
   30-minute bars, count real bars per session, and record gaps.
4. **Implication for the claim:** with 6 to 9 months of intraday data, a day-trade
   result is a feasibility check and engineering proof of concept, not statistical
   proof. If the owner wants proof, a deeper intraday data source is needed. That is a
   decision for the owner (open question 1).

Data handling: the agent pulls bars with the brokerage tool and saves them as JSON
fixtures (data source, request parameters and retrieval date recorded alongside);
the strategy code reads files only. This keeps calculation pure and testable and
matches how `run_cycle.py` and `income_cycle.py` take their inputs.

## 3. Proposed architecture

A new, isolated area (standard-library Python, matching the repo; calculation separate
from persistence and tools):

| Piece | Responsibility | Notes |
|---|---|---|
| `soxl_data.py` | Load fixtures, drop interpolated bars, session grouping, validation | Pure; tests with small synthetic fixtures |
| `soxl_indicators.py` | RSI (both **Wilder** and the repo's existing **simple** RSI in `rsi_filter.py`), SMA, MACD, VWAP, ATR | The request says "14-day RSI" without a smoothing convention; both are tested and the choice is reported |
| `soxl_study.py` | Reproduces the cited daily forward-return study and its audit | See section 4 |
| `soxl_strategy.py` | Entry, exit, stop, no-trade rules as pure functions | See section 5 |
| `soxl_backtest.py` | Event-driven intraday simulator with costs; baselines; walk-forward | Reuses ideas from `backtest.py` and `portfolio_backtest.py` without modifying them |
| `soxl_paper.py` | Paper account state, hard limits, kill switch | Own gitignored state file; not built until the plan is approved |
| Tests | One file per module | Included in the full-suite run |

Isolation: own limits dict (not added to `config.py` until the owner approves any
config change), own state file, own routine if one is ever created, never writing
`state.json`, `position_state.json`, `scanner_state.json` or `cycle_log.json`.

## 4. Audit of the cited backtest (daily, 5-day horizon)

Reproduce from raw, split-adjusted daily bars, with every definition written down:

- **Window:** 2021-10-26 to 2026-10-23, and the count of observations (the request cites
  1,219).
- **Target definitions to test, since the request does not fix one:** close-to-close
  return at day 5 of at least +8.19%; and the maximum high within the 5 sessions of at
  least +8.19% above the entry close. "Finished down at least 8.19%" is close-to-close.
  Report which definition reproduces the cited 31.5% / 26.7%.
- **Indicators:** RSI(14) under both conventions; 20-day simple average; MACD(12,26,9).
- **Conditional cells:** RSI 30 to 35 (cited 67 observations, 55.2% / 22.4%); price below
  the 20-day average (cited 580 observations, 33.3% / 28.3%).
- **Overlap caveat, quantified:** consecutive observations share 4 of 5 days. Report the
  number of effectively independent observations, a non-overlapping subsample (every
  fifth day) and a block bootstrap confidence interval for each rate. The 55.2% cell
  is expected to have a wide interval.
- **Costs and path dependence:** report the effect of the bid/ask spread (SOXL was
  quoted $87.30 / $87.35 on 2026-10-26, about 0.06%) and note that a 3x daily-reset
  fund's multi-day return is not 3x the index's multi-day return.
- **Deliverable:** a table of cited versus reproduced values, and a plain statement of
  anything that cannot be reproduced.

## 5. Day-trade strategy design (candidates to test, not conclusions)

- **Entry candidates:** RSI 30 to 35 as one feature, combined with confirmations tested
  one at a time and together: trend (price versus a moving average), MACD state, VWAP
  position, relative volume, and volatility (ATR).
- **Exit and risk:** flat by the close every day (no overnight holds, which removes the
  multi-day decay and gap exposure of a 3x fund); a fixed percentage stop and target
  tested on a small grid; maximum 1 share; maximum 1 trade per day; a daily loss stop
  expressed in dollars. With 1 share, the worst case per trade is the stop distance on
  one share (for example a 3% stop is about $2.60).
- **No-trade rules:** first 5 to 10 minutes after the open, the last 10 minutes, days
  with the stock or the semiconductor index halted, days with a data gap, and any
  session where the instrument's quote is stale.
- **Parameter discipline:** the grid is kept small and fixed in advance; the number of
  parameter combinations tried is reported so the overfitting risk is visible.

## 6. Validation plan

- **Baselines:** hold cash; buy and hold SOXL over the same period; a random-entry,
  same-holding-time baseline (many seeds); the same strategy without the RSI
  condition; a plain trend baseline.
- **Costs:** half-spread on entry and exit from the observed bid/ask (or a stated
  constant), plus an explicit slippage assumption; no commission.
- **Out of sample:** on the daily study, an expanding-window walk-forward (train on
  past, test on the next block). On the intraday data, a single chronological split with
  a held-out final block, because there are only 6 to 9 months of real bars; no random
  shuffles and no use of future data in any indicator or threshold.
- **Look-ahead checks:** unit tests that every signal uses only bars up to and
  including the decision bar, and that entries fill on the next bar.
- **Report:** win rate, expectancy per trade in dollars and percent, trade count,
  maximum drawdown, longest losing streak, cost drag, and comparison to each baseline,
  with confidence intervals, in the repo's dated evidence style.
- **Success rule (set before looking at results):** the strategy must beat the best
  baseline after costs on the held-out data, with a confidence interval that does not
  include zero edge. Otherwise the result is "no demonstrated edge".

## 7. Constraints to verify before any live use

- **Day-trade rules for this account.** The agent's account is a "limited margin"
  brokerage account at about $1,016. Pattern-day-trader and settlement rules for that
  account type must be confirmed with the broker, not assumed. The plan's one trade per
  day cap exists partly to stay inside any limit.
- **3x leverage** and daily reset: large intraday swings (the 2026-04-28 and 2026-07-28
  open bars moved several percent within minutes).
- **One share is about 8.6% of the account;** losses on it count against the account's
  daily loss limit and circuit breaker, shared across strategies.
- **Permission checks:** any future routine that places orders would likely meet the same
  real-money permission check seen on the income and VOLTRAP routines; that is a reason
  to keep a paper-only loop first.

## 8. Milestones and gates

| Step | Output | Gate to continue |
|---|---|---|
| M0 | This plan | Owner approval of scope, data window and validation plan |
| M1 | Data audit, fixtures, first real-data date | Real intraday history confirmed (or a deeper source supplied) |
| M2 | Reproduction and audit of the daily backtest | Cited numbers reproduced or the gap explained |
| M3 | Intraday harness, baselines, costs | Look-ahead tests pass |
| M4 | Walk-forward and held-out results report | Beats the best baseline after costs out of sample, else stop and report no edge |
| M5 | Paper-loop design, limits, kill switch | Owner review before any paper loop is enabled |
| M6 | Live enablement specification (not built) | Separate, explicit owner decision |

## 9. Open questions and proposed answers

Status: **proposed by the implementing agent, not yet confirmed by the owner.**
Nothing below changes live behavior; the plan remains backtest and paper only.

1. **Data depth: proposed answer, accept 6 to 9 months of real intraday history
   for a feasibility check only.** The brokerage's intraday bars are real from
   about 2026-04; earlier bars are flat, zero-volume filler and must be excluded.
   A short window cannot support a go-live decision, so any result is labelled
   "feasibility, not evidence" and a deeper intraday source would be needed
   before M5.
2. **Target definition: proposed answer, keep both** the close-to-close and the
   intraday-high definitions in the audit. The audit is cheap, and the gap
   between them shows how much of the cited result depends on assuming a fill
   at the high.
3. **Day-trade rules: not answerable from here; owner must confirm with the
   broker.** The account is about $1,018, below the usual $25,000
   pattern-day-trader threshold, so same-day round trips may be limited or
   restricted. Until confirmed, the plan stays backtest and paper only and
   M5 (any live step) is blocked.
4. **Paper loop: proposed answer, a read-only routine writing paper state** in
   its own files, separate from the live runner and from every protected state
   file, with no order tools. Manual paper trading stays the fallback if the
   owner prefers.
