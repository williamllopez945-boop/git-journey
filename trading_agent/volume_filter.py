"""Volume entry confirmation filter: blocks a fresh buy entry unless the
bar's trading volume clears a multiple of its own recent average - the
standard technical-analysis heuristic that a breakout on above-average
volume is more likely a genuine, sustained move than a low-volume drift
that reverses.

Scope, same as the whipsaw cooldown, concurrent-positions cap, and RSI
filter: only ever blocks a NEW entry (a "buy" signal into a previously-
flat asset). Never blocks a sell/death-cross or a protective exit.
"""

DEFAULT_VOLUME_PERIOD = 14
DEFAULT_VOLUME_MIN_RATIO = 1.0


def average_volume(volumes, period):
    """Mean volume of the `period` bars immediately before the current one
    (excludes the current bar itself), or None if there isn't enough
    history yet (needs period+1 bars)."""
    if len(volumes) < period + 1:
        return None
    return sum(volumes[-(period + 1):-1]) / period


def passes_volume_filter(volumes, period=DEFAULT_VOLUME_PERIOD, min_ratio=DEFAULT_VOLUME_MIN_RATIO):
    """Whether a fresh buy entry should proceed: True when there isn't
    enough history yet to compute an average (don't block warm-up), or
    when the current bar's volume (the last element of `volumes`) is at
    least min_ratio times the preceding period's average volume."""
    avg = average_volume(volumes, period)
    if avg is None or avg <= 0:
        return True
    current = volumes[-1]
    return current >= avg * min_ratio
