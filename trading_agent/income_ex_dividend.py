"""Ex-dividend timing gate for the income sleeve (see PLAYBOOK.md's
"Income sleeve" section).

On a fund's ex-dividend date, its share price mechanically steps down by
roughly the distribution amount - that value leaves the fund and goes to
whoever held shares as of the record date. Buying the day or two before
the ex-date just pre-pays for a distribution you immediately get back,
then eats the same markdown anyway - no real edge, a wash at best, worse
after costs. Buying on or shortly after the ex-date gets the genuinely
lower post-markdown price, while still being in position to collect
every future week's distribution from a weekly-paying fund.

Pure date arithmetic only - the live per-symbol ex_dividend_date comes
from get_equity_fundamentals, fetched by the calling cycle script, never
by this module.
"""

from datetime import date

AVOID_DAYS_BEFORE_EX_DIVIDEND = 2    # don't buy 1-2 days before ex-date
FAVORABLE_DAYS_AFTER_EX_DIVIDEND = 2  # do buy on, or up to 2 days after


def _as_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def days_until_ex_dividend(today, ex_dividend_date):
    """today, ex_dividend_date: date objects or ISO "YYYY-MM-DD" strings.

    Positive: the ex-date is upcoming (e.g. 1 means tomorrow).
    0: today IS the ex-date.
    Negative: the ex-date already passed (e.g. -1 means yesterday).
    """
    return (_as_date(ex_dividend_date) - _as_date(today)).days


def in_avoid_window(days_until):
    """True if 1 <= days_until <= AVOID_DAYS_BEFORE_EX_DIVIDEND - the
    pre-markdown window. Buying here pre-pays for a distribution you
    immediately get back while eating the same markdown anyway."""
    return 1 <= days_until <= AVOID_DAYS_BEFORE_EX_DIVIDEND


def in_favorable_window(days_until):
    """True if -FAVORABLE_DAYS_AFTER_EX_DIVIDEND <= days_until <= 0 - on
    or shortly after the ex-date, at the genuinely lower post-markdown
    price, still positioned for every future payout."""
    return -FAVORABLE_DAYS_AFTER_EX_DIVIDEND <= days_until <= 0
