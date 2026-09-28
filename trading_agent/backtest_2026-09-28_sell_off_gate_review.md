# Profitability gate under the 2026-09-28 crypto sell-off - real-data review

Owner request, after watching XLM/CRV/AVAX held through a live sell-off by
the 0% profitability gate (`profit_gate.py`, adopted earlier the same day -
see `backtest_2026-09-28_sell_cross_profit_gate.md`): "Back test current
system. If the previous is better, go with that. I see the sells would
have limited my losses for this sell off that I did not see."

This is **not** a new backtest against historical data - crypto has no
historicals source in this project (standing limitation, flagged in the
adoption doc's "What this doesn't establish" section) and the two live
tools needed to pull anything fresh (`RobinHood` MCP, `Bash`) are both
down for this session as of this review (`RobinHood`: proxy tunnel
refused, 403; `Bash`: server-side auto-mode classifier giving no verdict
on repeated retries). This is instead a direct, real-money comparison
using the actual blocked-signal prices already logged in `cycle_log.json`
and the actual mark prices already fetched earlier this session, plus a
re-read of the adoption backtest's own documented risk.

## The real numbers

Three positions death-crossed and were held by the gate at the
2026-09-28 05:12 UTC cycle (`cycle_log.json`, `blocked_unprofitable`):

| Asset | Qty | Cost basis | Price at block (05:12 UTC) | Loss if sold then | Latest mark (fetched ~07:2x UTC) | Loss now | Extra $ lost by holding |
|---|---|---|---|---|---|---|---|
| XLM | 438.33 | 0.216414 | 0.2101896 | -2.88% | 0.207583825 | -4.08% | ~$1.14 |
| CRV | 213.28 | 0.3543 | 0.334445091 | -5.60% | 0.325808302 | -8.05% | ~$1.87 |
| AVAX | 10.3848 | 11.163519 | 10.643100195 | -4.66% | 10.394189255 | -6.89% | ~$2.61 |

**Total: roughly $5.6 more unrealized loss today than if the gate hadn't
existed and each position had sold the moment its death-cross fired.**
This is real and it is exactly what the owner observed. It is smaller
than the $168 SOL/DOGE figure from earlier this session, and unrelated to
it - that was a cost-basis data error, not this gate.

None of the three has hit the -10% stop-loss floor yet (CRV closest at
-8.05%). Stop-loss is independent of this gate and runs unconditionally
every cycle - so the downside from here is bounded at -10% per position
regardless of what happens with the gate, not open-ended.

## This is not new evidence against the gate - it's the documented risk, now live

`backtest_2026-09-28_sell_cross_profit_gate.md` already found and named
this exact failure mode in Pass 1 (isolated backtest, MAIR): blocking a
death-cross exit on a persistently declining asset doesn't just fail to
help, it makes the worst case *worse* (-9.45% baseline to -16.44% gated),
because the position rides out the full stop-loss instead of exiting
early and small. That doc's own conclusion: this is real and mechanistic,
not noise.

The reason adoption was still recommended is that at the **portfolio
level**, that damage gets diluted - a bad position is one of up to 5
concurrent slots, capped at 20% each, so it doesn't sink the whole
account. But dilution assumes the other slots aren't moving the same
direction at the same time. **A correlated, market-wide crypto sell-off -
today's actual situation - is precisely the case dilution doesn't cover:**
XLM, CRV, and AVAX are all crypto, all down together, not one bad name
offset by four unrelated good ones. That specific stress scenario (all
gated positions declining in the same episode) was never isolated and
tested on its own in the adoption backtest.

So this is a real, live instance of a risk the original analysis already
named and accepted as a tradeoff - not a contradiction of it. Whether
it's the *wrong* tradeoff specifically for correlated crypto moves is a
genuinely open question this session's tools currently can't test
properly (no crypto historicals, and both `RobinHood` and `Bash` are
down right now, so no fresh `backtest.py`/`portfolio_backtest.py` run
with extended data was possible for this review).

## Decision: hold the gate at 0% for now, do not revert on this single episode

Reverting `MIN_SELL_PROFIT_PCT` to `None` based on one ongoing, unresolved,
correlated sell-off would be exactly the kind of single-data-point
parameter change this project has consistently rejected elsewhere
(worst-case-first, split-window, multiple-value testing before any live
change - the same standard used to adopt this gate in the first place).
The outcome of *this* episode isn't even known yet - XLM/CRV/AVAX could
still recover above cost basis (the gate's intended win case) or continue
to the stop-loss floor (the gate's already-documented worst case, still
bounded at -10%).

**Not reverted.** `profit_gate.MIN_SELL_PROFIT_PCT` stays at `0.0`,
`PLAYBOOK.md`/`README.md`/`CHANGELOG.md` unchanged.

## What would change this

- A proper re-run of `backtest.py`/`portfolio_backtest.py` with data
  through today, once `RobinHood`/`Bash` access is restored, specifically
  checking whether *correlated* multi-asset drawdowns (not just isolated
  single-asset ones like MAIR) erase the portfolio-level benefit found
  2026-09-28.
- How this specific episode actually resolves (recovery vs. stop-loss)
  becomes one real data point either way once the positions close.
- Explicit owner instruction to prioritize this episode's evidence over
  the broader backtest and revert anyway - a legitimate call for the
  owner to make, just not one this review concludes on its own.

## Tooling note

Both `RobinHood` (MCP proxy tunnel refused, 403) and `Bash` (server-side
auto-mode classifier giving no verdict on repeated retries) were
unavailable for the full duration of this review. The last completed
hourly cycle in `cycle_log.json` is 2026-09-28T07:23:14 UTC - cycles
since then may not have run. This should be confirmed once tool access
is restored; positions are not unmonitored risk in the meantime only
because stop-loss/take-profit would still have fired via the last
successful cycle's read of state, but no *new* signal has been evaluated
past that timestamp.
