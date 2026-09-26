# Trailing stop — considered, not adopted (2026-09-24)

Owner asked whether a trailing stop on the post-take-profit remainder
(tracks the peak price since take-profit, exits on a pullback from it)
would help. Backtested across 12 real series (90-day hourly + GBTC's
full history in 6 regimes) at every percentage from 3%–15%. Every
variant tested hurt returns — mean delta negative at every value, worst
case -70 percentage points in the strongest bull regime. Letting the
30% remainder ride loose (not tight) is what lets it capture big
continued moves; a trailing stop fights that.

`TRAILING_STOP_PCT` stays `None` (mechanism built and tested, not
shipped). Noting it here so it doesn't get re-proposed without new
evidence.
