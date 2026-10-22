"""Candidate screening and strike selection for VOLTRAP, the options
wheel strategy (see PLAYBOOK.md's "VOLTRAP" section for the full
procedure). Mirrors watchlist_review.py's role: pure functions that
cut the repeated ranking/filtering work out of the live cycle, without
wrapping the actual chain/quote tool calls themselves (those stay live
per cycle, since the tradeable universe and its budget both move week
to week).

Three independent pieces:
- rank_by_voltrap_fit: given one cycle's options-focused scan results
  (scan_id built via create_scan, preset HIGH_OPTIONS_VOLUME_IV plus
  custom IV/liquidity/price filters - see PLAYBOOK.md), filters out
  anything the current budget can't secure 100 shares of and anything
  too illiquid, then ranks the rest by implied volatility as a coarse
  premium-yield proxy. This is a first-pass filter only - the real
  premium/collateral numbers come from review_option_order on the
  specific contract chosen afterward, never from this ranking alone.
- pick_strike_by_delta / pick_strike_by_otm_pct: given one underlying's
  option instruments for a single expiration, each already paired with
  a quote, choose the strike inside a target band. Delta is preferred
  when the quote payload carries it; the OTM-percentage form is the
  documented fallback if it doesn't (verify at first live use).
- voltrap_budget_after_income_reserve: VOLTRAP, the income sleeve, and
  the crypto/stock bot are three independent strategies that each size
  their own budget as a fraction of total portfolio value - but all
  three draw on the SAME real cash. Nothing before 2026-10-09 enforced
  that, because VOLTRAP had no real cash to reserve yet. Now that
  VOLTRAP_RISK_LIMITS["max_voltrap_pct"] is 1.00 (owner request), a
  pct-of-portfolio ceiling alone would let VOLTRAP's weekly entry
  reserve cash the income sleeve needs for its own buys (owner request,
  2026-10-09: "Ensure dividend stocks buys are available too. Voltrap
  will trade with what's left"). See PLAYBOOK.md and CHANGELOG.md.
"""


def rank_by_voltrap_fit(scan_rows, max_collateral_per_contract, min_avg_options_volume=None, min_open_interest=None):
    """scan_rows: {"ticker": ..., "columns": {...}} dicts from the VOLTRAP
    candidate scan, columns keyed by the scanner's own display names
    ("Last", "Implied volatility", "Average options volume",
    "Open interest").

    Filters out:
    - any row whose 100-share collateral (100 * Last) exceeds
      max_collateral_per_contract (can't secure even one contract on it
      within budget)
    - any row below min_avg_options_volume / min_open_interest, when
      given (illiquid - real slippage risk on the actual fill)
    - any row missing Last or Implied volatility (still warming up, or
      the column wasn't populated this cycle)

    Returns the survivors sorted by Implied volatility descending (a
    coarse "richer premium" proxy) with an extra "collateral_per_contract"
    key attached. Empty in, empty out - callers treat an empty result as
    "no candidate fits this cycle's budget/liquidity bar", not an error.
    """
    ranked = []
    for row in scan_rows:
        ticker = row.get("ticker") or row.get("columns", {}).get("Symbol")
        if not ticker:
            continue
        cols = row.get("columns", {})
        try:
            last = float(cols["Last"])
            iv = float(cols["Implied volatility"])
        except (KeyError, TypeError, ValueError):
            continue

        collateral = 100 * last
        if collateral > max_collateral_per_contract:
            continue

        if min_avg_options_volume is not None:
            try:
                avg_options_volume = float(cols.get("Average options volume", 0))
            except (TypeError, ValueError):
                avg_options_volume = 0
            if avg_options_volume < min_avg_options_volume:
                continue

        if min_open_interest is not None:
            try:
                open_interest = float(cols.get("Open interest", 0))
            except (TypeError, ValueError):
                open_interest = 0
            if open_interest < min_open_interest:
                continue

        ranked.append({**row, "collateral_per_contract": collateral})

    ranked.sort(key=lambda r: float(r["columns"]["Implied volatility"]), reverse=True)
    return ranked


def pick_strike_by_delta(instruments, target_delta_min, target_delta_max, option_type):
    """instruments: list of {"strike": float, "delta": float, ...} for one
    underlying/expiration (delta already pulled from get_option_quotes).
    option_type: "put" or "call" - deltas are expected in that side's
    natural sign convention (puts negative, calls positive); this
    function compares absolute value against the band either way.

    Returns the instrument whose |delta| falls within
    [target_delta_min, target_delta_max], closest to the midpoint of the
    band if more than one qualifies. None if none do - the caller's
    signal to skip this underlying this cycle rather than force a trade
    outside the target risk band.
    """
    midpoint = (target_delta_min + target_delta_max) / 2
    candidates = [i for i in instruments if target_delta_min <= abs(i["delta"]) <= target_delta_max]
    if not candidates:
        return None
    return min(candidates, key=lambda i: abs(abs(i["delta"]) - midpoint))


def pick_strike_by_otm_pct(instruments, current_price, target_otm_pct_min, target_otm_pct_max, option_type):
    """Fallback for pick_strike_by_delta when the quote payload doesn't
    carry delta. instruments: list of {"strike": float, ...}.

    For a put, "out of the money" means strike below current_price; for
    a call, strike above current_price. target_otm_pct_* are fractions
    (0.10 = 10% OTM), matching the rest of this project's convention.
    Returns the instrument whose OTM distance falls within the target
    band, closest to its midpoint. None if none qualify.
    """
    midpoint = (target_otm_pct_min + target_otm_pct_max) / 2
    candidates = []
    for inst in instruments:
        strike = inst["strike"]
        if option_type == "put":
            if strike >= current_price:
                continue
            otm_pct = (current_price - strike) / current_price
        else:
            if strike <= current_price:
                continue
            otm_pct = (strike - current_price) / current_price
        if target_otm_pct_min <= otm_pct <= target_otm_pct_max:
            candidates.append((otm_pct, inst))
    if not candidates:
        return None
    return min(candidates, key=lambda pair: abs(pair[0] - midpoint))[1]


def voltrap_budget_after_income_reserve(
    portfolio_value,
    buying_power,
    max_voltrap_pct,
    income_max_aggregate_pct,
    current_voltrap_collateral_used,
):
    """New cash VOLTRAP may still reserve as collateral this cycle,
    after leaving room for the income sleeve's own budget.

    portfolio_value: real total account value (get_portfolio).
    buying_power: real spendable cash right now (get_portfolio) - the
        actual constraint on reserving new collateral, unlike
        portfolio_value which includes whatever is already deployed
        elsewhere (crypto/stock positions, income-sleeve shares,
        VOLTRAP's own existing collateral).
    max_voltrap_pct: VOLTRAP_RISK_LIMITS["max_voltrap_pct"] - VOLTRAP's
        own nominal ceiling as a fraction of portfolio_value.
    income_max_aggregate_pct: INCOME_RISK_LIMITS["max_aggregate_position_pct"]
        - the income sleeve's own ceiling. Reserved against buying_power
        in full, whether or not the sleeve currently holds anything, so
        a dividend-stock buy this week or next always has real cash
        available rather than competing with VOLTRAP for it.
    current_voltrap_collateral_used: cash VOLTRAP already has reserved
        in open csp_open/covered_call_open contracts (sum from
        VoltrapStateStore across VOLTRAP_WATCHLIST), so a nominal
        ceiling isn't exceeded cycle over cycle as positions accumulate.

    Returns the smaller of (VOLTRAP's remaining nominal headroom) and
    (real cash left after reserving the income sleeve's full ceiling) -
    never negative.
    """
    nominal_ceiling = portfolio_value * max_voltrap_pct
    remaining_nominal = max(0.0, nominal_ceiling - current_voltrap_collateral_used)
    income_reserved = portfolio_value * income_max_aggregate_pct
    cash_after_income_reserve = max(0.0, buying_power - income_reserved)
    return min(remaining_nominal, cash_after_income_reserve)
