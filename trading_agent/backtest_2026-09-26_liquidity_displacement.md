# Liquidity sweep/displacement entry gate — considered, not adopted (2026-09-26)

Owner asked about the ICT "liquidity displacement" concept (a candle
that sweeps below a swing low then reverses hard) as an extra entry
gate. Operationalized it into a testable rule and backtested it across
12 real series and several parameterizations. Every version hurt more
than it helped — it either rejected almost every entry (a displacement
candle and the SMA crossover confirmation operate on mismatched
timeframes) or cut real winners with no compensating benefit (mean
delta -3.6% to -6.1%, worst case -36%).

No config or code changes shipped. Noting it here so it doesn't get
re-proposed without new evidence.
