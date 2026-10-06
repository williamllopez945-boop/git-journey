import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.income_ex_dividend import (
    days_until_ex_dividend,
    in_avoid_window,
    in_favorable_window,
)


def test_days_until_ex_dividend_future():
    assert days_until_ex_dividend(date(2026, 10, 6), date(2026, 10, 7)) == 1
    assert days_until_ex_dividend(date(2026, 10, 6), date(2026, 10, 9)) == 3


def test_days_until_ex_dividend_today():
    assert days_until_ex_dividend(date(2026, 10, 7), date(2026, 10, 7)) == 0


def test_days_until_ex_dividend_past():
    assert days_until_ex_dividend(date(2026, 10, 9), date(2026, 10, 7)) == -2


def test_days_until_ex_dividend_accepts_iso_strings():
    assert days_until_ex_dividend("2026-10-06", "2026-10-07") == 1


def test_avoid_window_boundaries():
    assert in_avoid_window(0) is False   # today IS ex-date, not "before" it
    assert in_avoid_window(1) is True
    assert in_avoid_window(2) is True
    assert in_avoid_window(3) is False


def test_favorable_window_boundaries():
    assert in_favorable_window(1) is False   # still before ex-date
    assert in_favorable_window(0) is True    # ex-date itself
    assert in_favorable_window(-1) is True
    assert in_favorable_window(-2) is True
    assert in_favorable_window(-3) is False


def test_avoid_and_favorable_windows_do_not_overlap():
    for days_until in range(-5, 6):
        assert not (in_avoid_window(days_until) and in_favorable_window(days_until))
