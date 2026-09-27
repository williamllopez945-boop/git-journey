# Relative-strength entry gate — considered, not adopted (2026-09-27)

Owner asked about ranking the watchlist by trailing relative strength and
gating new entries to the current leaders, from a "top 5 strategies"
research summary. Tested as an entry gate (rank assets by trailing
return, only let a fresh_buy_cross execute if the asset is in the top
fraction). A first pass on the 90-day hourly 12-series test bed looked
promising (+0.87pp worst-case, split-window) for one config (72h
lookback, keep top 75%).

Deeper multi-regime validation reversed it. Two real, multi-year/longer
crypto-ETF groups (bar-aligned, interpolated placeholder bars excluded):
IBIT+ETHA (2.15 years real daily) forced to pick the relatively stronger
of the two lost **-6.87% to -12.50%** worst-case across every lookback
tested (1/3/5 trading days) — clearly negative, larger in magnitude
than the original positive result. A shorter 4-way group
(GBTC+VSOL+BSOL+GSOL, ~7 months real daily) was only marginally positive
(+0.08% to +0.37%), nowhere near enough to offset that. The original
90-day hourly finding was a narrow, single-period artifact.

Not adopted — no config or code changes shipped. Noting it here so it
doesn't get re-proposed without new evidence.
