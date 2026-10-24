# Proposed thin routine prompts (DRAFTS; only the income prompt is applied)

Status: **drafts for owner review.** Applied so far: the income sleeve prompt
(2026-10-24) and a one-paragraph fix to the stored hourly prompt (record the fill
in a separate `--record-only` call, 2026-10-24). The full hourly draft, the
daily-review draft and the rest below are NOT applied. Applying a prompt is a Phase 3 action that needs explicit owner
approval, one routine at a time, with the previous prompt saved first (for
rollback, via `get_trigger`, into a scratch file kept out of Git because prompts
contain account details).

Why: the stored prompts are long copies of PLAYBOOK. They drift. Two have
already failed that way: the income prompt passed a `--fundamentals-file` flag
removed on 2026-10-16, and the VOLTRAP monitor still says "recommend-only"
while `config.py` has `VOLTRAP_AUTO_EXECUTE = True`. Each draft below keeps
only (a) a pointer to the PLAYBOOK section that is the source of truth, (b) the
operational overrides and hard rules that must never be missed, and (c) the
reporting contract. Anything else is read live from the repo.

Common footer for every routine: *If a tool or script call is denied by a
permission check, report it in the notification and stop; do not work around
it.*

## Hourly trading cycle (also needs a schedule change in Phase 3)

> Hourly trading cycle for the agent in /home/user/git-journey/trading_agent.
> First read `STATUS.md`, then run `PLAYBOOK.md` "Steps, per cycle", "Scanner-based
> cycle - stocks", "Per-position exit rules", "Hard rules" and "Cycle logging",
> using the live values in `config.py` and `exit_criteria.py`.
>
> Overrides that apply every run:
> - All crypto is cut (owner, 2026-10-08). Check crypto only if a crypto position
>   is open (AERO protective-exit check via `get_crypto_quotes`), else skip it.
> - Arm and check the daily circuit breaker first. Protective exits (stop-loss,
>   take-profit) always run, even during a halt; gate-floor exits and all new
>   entries do not.
> - Stock steps only run 9:30-16:00 ET Monday to Friday; outside that, exit quietly.
> - Use `run_cycle.py --asset-class stock` for the analysis. Record an executed trade
>   in a SEPARATE call: `run_cycle.py --asset-class stock --record-only --portfolio-file
>   <portfolio.json> --record-trade-*` flags, with no scan, historicals, quotes or
>   positions files. Never re-run the analysis command with the fill flags (it
>   reclassifies identical inputs and advances `scanner_state.json` twice), and never
>   call `record_trade` inline. See PLAYBOOK "Per-cycle helper".
> - Orders are marketable limit orders only, never market orders.
> - Never edit `config.py` (`RISK_LIMITS`, `DRY_RUN`, `WATCHLIST`,
>   `STOCK_WATCHLIST`, `VOLTRAP_*`, `INCOME_*`).
>
> Report: one PushNotification (<200 chars) and a Slack post to the channel in
> PLAYBOOK "Slack notifications" only when something is notable (executed trade,
> protective exit, recommendation awaiting approval, or a blocked signal worth
> noting). Stay quiet on a plain hold.

## Income sleeve cycle

**APPLIED 2026-10-24** (owner approval). The stored version is slightly fuller than the draft below: it also names the account, restates that exits run even during a circuit-breaker halt, keeps the exact record-only command and drops the draft's shorthand. The draft text is kept for reference.

> Income sleeve cycle in /home/user/git-journey/trading_agent. Follow `PLAYBOOK.md`
> "Income sleeve" (especially "Per-cycle script"). Read `INCOME_WATCHLIST`,
> `INCOME_RISK_LIMITS` and the exit constants live; do not restate them.
>
> - Fetch quotes, daily historicals (~90 days, split in two calls and merged),
>   positions and portfolio into scratchpad files, then run
>   `python3 trading_agent/income_cycle.py` with only the four `--*-file` flags
>   (`--help` shows the current set). It takes no `--fundamentals-file`.
> - Act on every exit it reports. Place every `ENTER` as a marketable limit order,
>   whole shares only; if the floored quantity is 0, place nothing and report the
>   signal as unexecutable (no market-order fallback).
> - After any fill, record the real fill price in a separate `--record-only` call.
> - Verify the run left today's state files in `trading_agent/`; if not, say so.
>
> Report: one PushNotification for an entry, an exit, an unexecutable signal, a
> position within 5 points of its stop-loss, or any failure. Quiet only on a
> plain hold with all state files written. Never modify `INCOME_*` constants.

## VOLTRAP daily monitor (conditional)

> VOLTRAP daily monitor. Follow `PLAYBOOK.md` "VOLTRAP", sections "State machine"
> and "Weekly + daily cycles". `VOLTRAP_AUTO_EXECUTE` is read from `config.py`
> (currently True); this monitor itself never places orders.
>
> - If the real option positions are empty and `voltrap_state.json` shows no
>   `csp_open`/`covered_call_open` symbol, exit quietly with no notification.
> - Otherwise check each open contract for deep ITM / early-assignment risk and
>   drive the expiration-day state transitions described in the PLAYBOOK.
> - Rolling is out of scope: flag it to the owner, do not attempt it.
>
> Hard rules: read-only on orders and positions; only `VoltrapStateStore`
> bookkeeping may be updated. Notify only if something actionable happened.

## Daily after-action review

> Daily after-action review. Follow `PLAYBOOK.md` "Cycle logging" and the
> `daily_review.py` helpers: `summarize_day`, then `format_markdown_report` with
> the **active** watchlists only (crypto is cut, so pass `STOCK_WATCHLIST`, not
> `WATCHLIST + STOCK_WATCHLIST`). Cross-check equity orders and day realized P/L
> against the local logs; skip the crypto orders cross-check while crypto is cut.
> Add 2-4 sentences of observations (name patterns, not single data points).
> Write `daily_logs/<today UTC>.md`, commit only that file on the branch named in
> the repo's routine guidance, push it, then send the push headline and the Slack
> excerpt every day (this routine is a daily habit; quiet days still report).
> Never edit config or place, preview, or cancel an order.

## Weekly watchlist review

> Weekly watchlist review. Follow `PLAYBOOK.md` "Weekly watchlist review" for
> `STOCK_WATCHLIST` and `VOLTRAP_WATCHLIST` only; crypto is paused (one line
> noting that). Write the dated recommendation file (even for "no change"),
> commit and push it, and send one notification. Never edit `config.py`; a swap
> happens only after explicit owner approval. Confirm the current branch before
> committing and stop if it is not the expected one.

## Known defect in the live hourly prompt (found in PR #8 review; FIXED 2026-10-24)

**Fixed 2026-10-24** with a narrow one-paragraph edit to the stored hourly prompt (owner approval). The original text read:

The stored hourly prompt said to pass `--record-trade-*` "on the SAME
run_cycle.py command" (a 2026-09-29 note). PLAYBOOK was corrected on 2026-10-05:
recording must be a separate `--record-only` call. No stock trade has executed
since, so nothing has gone wrong yet, but the first real fill could trigger the
double-classification bug. The paragraph now requires the separate `--record-only` call, so the thin
hourly prompt is no longer urgent.

## Not redrafted

The research agent scan prompt and the paper dry-run prompt are left as is
(the dry-run is proposed for pausing in Phase 3). The Ledger refresh prompt is a
fixed mechanical template tied to the dashboard's schema, so thinning it risks
breaking the snapshot shape; it is proposed only for a lower cadence.
