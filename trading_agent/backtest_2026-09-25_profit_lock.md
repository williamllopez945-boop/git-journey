# Profit-lock stop — considered, not adopted (2026-09-25)

Owner asked whether tightening the stop-loss from -10% to +10% once a
position's unrealized gain hits 15% (so a reversal can't fully
round-trip a gain into a loss) would help. Backtested at the requested
15%/10% plus two neighboring pairs across 48 real series. Every variant
hurt more than it helped (mean -1.36% to -2.79%, worst case -15% to
-37%) — same root cause as the trailing-stop finding: clipping a
position before a strong trend fully plays out costs more than it
protects.

`PROFIT_LOCK_TRIGGER_PCT`/`PROFIT_LOCK_STOP_PCT` stay `None` (mechanism
built and tested, not shipped). Noting it here so it doesn't get
re-proposed without new evidence.
