# Income sleeve: does an "institutional money entry" confirmation beat the 20-day dip alone? (2026-10-13)

Owner request: "Check hourly during trading times. Buy when oversold
and check trend analysis of where institutional money will enter."
Follow-up answers (2026-10-13): drop the RSI-oversold idea
(`backtest_2026-10-09_macd_rsi_income_sleeve_rejected.md` already found
RSI-alone close to a wash), focus on the institutional-flow idea
instead. Answered with a real backtest per COLLABORATION.md's rule
("Any strategy parameter change needs real historical backtesting
first... Read the rejected trailing-stop, profit-lock, RSI, and
liquidity-displacement studies before proposing to enable those ideas
again"), not opinion.

**No real order-flow data exists here.** Robinhood's API has no
dark-pool/block-trade/order-flow feed - any "institutional money" proxy
has to be built from ordinary OHLCV bars. Two candidate proxies were
tried.

## First attempt: volume-weighted support level (rejected before backtesting)

Initial design: compute a trailing 20-day volume-weighted average price
(VWAP) and require today's close to be at or below it (within 2%)
before confirming a `dip_buy` signal - the idea being that heavy $
volume recently transacted near a price level marks it as "where big
money has been active."

Checked this against real data for all 8 original income-sleeve symbols
(YMAX, YMAG, ULTY, CHPY, GPTY, AMDW, GOOW, NVDW, same roster as the
2026-10-09 RSI/MACD study) **before** running a full backtest: counted
every bar where `income_signals.classify_dip` already said `dip_buy`,
and checked how often the VWAP-proximity condition would have blocked
it.

**Result: 0 blocks out of 790 real `dip_buy` bars across all 8
symbols.** This is not a coincidence - `classify_dip` fires when
today's close is in the bottom 10% of its own trailing 20-day range, and
a volume-weighted average over that same window is a blend of prices
across the whole range. Being near the window's low makes being below
the window's volume-weighted average close to a mathematical certainty
unless almost all volume happened to transact exactly at the low. This
design was a no-op wrapped around the existing signal - dropped without
being wired into the backtest harness, since it had nothing to
contribute.

## Second attempt: volume-surge confirmation (the one actually backtested)

Replaced it with a gate that is NOT redundant with the dip signal:
`income_institutional_flow.volume_surge_confirmed` - today's volume
must be at least 1.5x the trailing 20-day average volume (today
excluded). Reasoning: a price dropping into the bottom of its range on
unusually heavy volume looks more like a real capitulation/accumulation
event than a quiet drift down on ordinary volume. Confirmed this
actually discriminates before backtesting: across the same 8 symbols,
it blocks roughly 75-88% of raw `dip_buy` bars (not 0%, not 100%) -
genuinely orthogonal information to the range-position signal.

### Data

Same source and filtering as the 2026-10-09 study:
`get_equity_historicals(symbols=[8 names], interval="day",
bounds="regular", start_time=2024-01-01)`, `interpolated != true` only
(real trading days, each symbol's own real inception onward). Real bar
counts: YMAX 687, YMAG 678, ULTY 657, CHPY 383, GPTY 432, AMDW 307,
GOOW 307, NVDW 414 (counts differ slightly from the 2026-10-09 doc -
two more real trading days have since occurred).

### Method

`income_backtest.income_backtest(closes, volumes=volumes)` (production
`income_signals.classify_dip` + `income_exit.check_income_exit`
unchanged, now with the optional volume-surge gate added this session -
see `income_backtest.py`/`income_institutional_flow.py`) vs. the
existing `income_backtest(closes)` baseline (no `volumes` argument - the
gate is fully opt-in and defaults off). Starting cash $100/symbol,
frictionless, same convention as every other income-sleeve backtest.
Each symbol's real history split in half (H1/H2) and scored
worst-half-first, the project's standing ranking rule - full-period
return alone can hide a half that performed much worse. **Same
price-only caveat as every income-sleeve backtest in this project**: no
distribution cash flow is modeled.

### Results

| Symbol | baseline entries, full ret% / maxdd% / worst-half% | gated entries, full ret% / maxdd% / worst-half% |
|---|---|---|
| YMAX | 6, -56.29 / 61.38 / -43.95 | 6, -60.53 / 62.25 / -44.46 |
| YMAG | 4, -22.64 / 34.10 / -23.89 | 3, -22.37 / 32.50 / -19.62 |
| ULTY | 11, -80.35 / 80.50 / -59.10 | 8, -66.84 / 67.09 / -43.32 |
| CHPY | 1, +16.37 / 18.60 / +10.13 | 1, +19.40 / 18.88 / -7.36 |
| GPTY | 2, -6.68 / 25.60 / -4.75 | 1, +10.08 / 15.69 / -16.55 |
| AMDW | 2, +73.58 / 24.96 / -2.00 | 1, +67.27 / 28.99 / +0.82 |
| GOOW | 1, +6.18 / 17.06 / -13.77 | 3, -23.40 / 29.98 / -10.18 |
| NVDW | 2, +2.08 / 23.89 / -5.86 | 1, +12.35 / 23.89 / -16.82 |

### Observations

- **ULTY - the sleeve's most actively traded name and its worst
  baseline performer - clearly improves.** Entries drop from 11 to 8,
  full-period return improves from -80.35% to -66.84%, max drawdown
  from 80.50% to 67.09%, and the worst half's return improves from
  -59.10% to -43.32%. This is the one case where the gate helps on
  every axis, not just the headline number.
- **YMAG also improves modestly and consistently** (fewer entries,
  better full return, better drawdown, better worst-half).
- **The other six symbols are mixed, and worse worst-case-first on
  balance.** CHPY and NVDW both show a better full-period return but a
  meaningfully worse worst-half (CHPY: +10.13% -> -7.36%; NVDW: -5.86%
  -> -16.82%). GPTY's full return flips positive but its worst-half gets
  substantially worse (-4.75% -> -16.55%). GOOW gets worse on every
  axis except a slightly better worst-half. AMDW is close to a wash
  (full return very slightly worse, worst-half very slightly better).
  Fewer entries did not translate into "safer" worst-case outcomes for
  most of the roster - several times the opposite, because removing
  the loss from more trades also removed the gain from some winning
  ones, and the half that got worse often lost its best remaining trade.
- **Same structural read as the RSI finding**: this is not a clean,
  uniform improvement - it is a mixed result that happens to land
  clearly positive for the two names with the deepest/most active
  trading history, and mixed-to-negative for the shorter-history,
  thinner-volume names where a handful of trades swing the result
  heavily either way.

### Answer to "check trend analysis of where institutional money will enter"

On this data, a defensible, discriminating proxy for that idea
(volume-surge confirmation) is **not a clean win across the sleeve** by
the project's own worst-case-first standard, even though it is a real
signal (unlike the VWAP-distance attempt, which was a no-op). It
clearly helps the two names that have actually traded enough to judge,
and is a wash-to-negative on the rest, similar in character to the
2026-10-09 RSI finding - a defensible idea that doesn't clear the bar
for an unconditional go-live recommendation.

### Decision

**No code change to the live cycle.** `income_cycle.py` is unchanged;
`classify_dip` remains the sole entry signal in production.
`INCOME_WATCHLIST`, `INCOME_RISK_LIMITS`, `INCOME_AUTO_EXECUTE`
untouched, per COLLABORATION.md. The new module
(`income_institutional_flow.py`) and the `income_backtest.py` opt-in
`volumes=` parameter are additive-only, fully tested
(`tests/test_income_institutional_flow.py`, full suite still green),
and not wired into any live path.

**Decision point for the owner**: the two defensible options this
result supports are (a) do not adopt the gate sleeve-wide given the
mixed worst-case picture, or (b) adopt it only for ULTY/YMAG
specifically (the two names it clearly helps), leaving the rest on the
plain dip signal - a per-symbol gate the current `income_cycle.py`
doesn't support yet and would need a small, explicit config addition if
chosen. Not decided here; no further code change made pending that
choice.

**On the hourly-checking part of the original request**: this signal
is built entirely from daily bars (daily close + daily volume), so
checking it more often than once a day would not surface new
information - the same conclusion flagged as an open question before
this backtest. If the owner still wants genuinely hourly decisions, that
would require redesigning the signal around intraday bars, a materially
different and not-yet-attempted piece of work, separate from this gate.
