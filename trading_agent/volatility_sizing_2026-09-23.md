# Volatility-aware position sizing — 2026-09-23

Built `volatility_sizing.py`: scales the position-size cap down (never
up) for assets more volatile than a benchmark (BTC), instead of every
asset getting the same flat `RISK_LIMITS["max_position_pct"]` (5%)
regardless of how volatile it is.

## Scope, stated upfront

This sizes an individual position by its own volatility relative to
BTC. It does **not** model correlation across several simultaneously-held
positions (e.g. multiple meme coins that tend to move together) — a
proper treatment of that needs a true multi-asset portfolio backtester
that tracks concurrent holdings, which is a materially larger project
than the single-asset `backtest.py` built so far this session. Rather
than overreach into that, this validates the volatility *measurement*
against real market data instead, checking that it correctly
differentiates risk across assets.

## Design

- `realized_volatility(prices)`: sample stdev of period-over-period %
  returns. Same units as `crossover_pct` (a percentage, not a fraction).
- `scaled_max_position_pct(asset_vol, benchmark_vol, base_cap)`: returns
  `base_cap * min(1.0, benchmark_vol / asset_vol)` — an asset at or below
  the benchmark's volatility keeps the full cap; a more volatile asset
  gets scaled down proportionally. Deliberately never scales *above* the
  base cap for a calmer-than-benchmark asset — increasing capital
  deployed to "make up for" low volatility would raise aggregate
  portfolio risk, not just rebalance it.
- Wired into `RiskManager.position_size` as an optional
  `max_position_pct` override parameter (backward compatible — existing
  calls without it behave exactly as before).

## Validation against real data

**Important:** volatility must be compared on the same bar interval —
comparing hourly-measured volatility against daily-measured volatility
exaggerates the daily series' relative risk, since daily returns are
naturally larger swings than hourly ones. Two same-cadence groups below.

**Hourly bars (matches the live system's actual cadence):**

| Asset | Volatility (%/bar) | Scaled cap | % of base |
|---|---|---|---|
| IBIT (BTC, benchmark) | 1.037% | 5.000% | 100.0% |
| ETHA (ETH) | 1.317% | 3.937% | 78.7% |

ETH measured ~27% more volatile than BTC on real hourly data, and scaled
to ~79% of the flat cap — a sensible, real differentiation, not an
arbitrary guess.

**Daily bars (GBTC/Solana ETFs, GBTC-2021 as benchmark):**

| Asset | Volatility (%/bar) | Scaled cap | % of base |
|---|---|---|---|
| GBTC 2021 (choppy-bull, benchmark) | 5.366% | 5.000% | 100.0% |
| GBTC 2022 (crash) | 4.788% | 5.000% | 100.0% |
| VSOL | 3.143% | 5.000% | 100.0% |
| BSOL | 3.340% | 5.000% | 100.0% |
| GSOL | 5.509% | 4.870% | 97.4% |

Most stayed near the cap since GBTC-2021 happened to be the most
volatile period in this particular group; GSOL, the one asset more
volatile than the benchmark, was correctly scaled down.

## Live usage

Only available on the `price_history.py` polling path — it needs an
accumulated raw price series (at least 3 bars) to compute a stdev from.
The faster scanner path (`scanner_signals.py`) only has point-in-time SMA
values from the RobinHood scanner, not a series, so scanner-detected
signals always size at the flat cap. See `PLAYBOOK.md` step 5d.
