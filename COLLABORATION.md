# Working with Codex and Claude Code

A branch is a named line of saved changes. A commit is a saved checkpoint.
A worktree is another folder containing its own checked-out branch; worktrees
share Git history, but have separate working files and staging areas.
A clone has its own history store as well as its own working files.

**Default: one agent implements a task, then the other reviews its saved
commits. One working folder has at most one active agent.** Separate chat
windows are not separate workspaces. Codex and Claude Code do not automatically
share conversations, plans, approvals, or tool results. The commits and the
task's written handoff carry that information.

## Read first and preserve existing work

At the start of every task, inspect the actual checkout:

```text
git rev-parse --show-toplevel
git status --short --branch
git branch --show-current
git remote -v
git symbolic-ref refs/remotes/origin/HEAD
git worktree list
git log -5 --oneline
```

This project's remote is `https://github.com/williamllopez945-boop/git-journey.git`
and its default branch is `main`. Verify rather than assuming those remain true.
Do not paste remote URLs containing credentials into a report.

Read these documents, in order, before touching trading behavior:

1. `trading_agent/README.md` and `trading_agent/PLAYBOOK.md`.
2. `trading_agent/config.py`.
3. `trading_agent/CHANGELOG.md`.
4. The relevant dated `backtest_*.md`, `watchlist_*.md`, and
   `volatility_sizing_*.md` evidence.
5. For research changes, `research_agent/README.md`, `PLAYBOOK.md`, and
   `config.py`.

Preserve existing instructions, edits, staged changes, and untracked files.
If work is already present, identify its owner and scope before editing it;
use a new worktree when that avoids interference. Do not discard changes,
automatically stash someone else's work, force-push, rewrite shared commits,
or use `reset --hard` / `clean -fd` to obtain a clean workspace.

These collaboration rules supplement the operating runbooks. Reading a
runbook is not authorization to execute its trading, notification, scheduling,
commit/push, or account-management steps during development.

## Project conventions and boundaries

- This is a real-money system. The production config has live trading enabled.
  Development and review require no brokerage access. Do not connect or run
  the live trading/research automations just to test code.
- The Python modules are small, focused, mostly standard-library logic.
  Keep calculation functions separate from persistence and external tools;
  match the surrounding style and add meaningful tests for new logic.
- `run_cycle.py` is an analysis helper, not a complete order executor. It can
  write risk/scanner state even with `--no-log`. Never smoke-test it against
  real runtime files; use the isolated fixtures in its tests.
- Never modify `RISK_LIMITS`, `DRY_RUN`, `WATCHLIST`, `STOCK_WATCHLIST`,
  `VOLTRAP_WATCHLIST`, `VOLTRAP_RISK_LIMITS`, or `VOLTRAP_AUTO_EXECUTE`
  incidentally. These require explicit owner approval for that change.
- Any strategy parameter change needs real historical backtesting first with
  `backtest.py` / `portfolio_backtest.py`, multiple windows and worst-case
  comparisons. Report negative results. Do not invent crypto history:
  the existing studies use equity/ETF proxies such as IBIT and ETHA.
  Read the rejected trailing-stop, profit-lock, RSI, and liquidity-displacement
  studies before proposing to enable those ideas again.
- For a real behavior change, update the relevant README, CHANGELOG, and
  referenced PLAYBOOK sections alongside code, following their dated style.
  Flag conflicts between current code and old prose; do not resolve them by
  silently changing live parameters.
- Research is advisory, with coverage defined by its imported watchlists.
  It does not place orders or change trading gates. VOLTRAP has separate
  configuration and its own go-live conditions.
- `state.json`, `cycle_log.json`, and `voltrap_state.json` are tracked in
  Git as of 2026-09-29 (owner decision, `.gitignore` updated on `main`) -
  unlike the files below, they may be committed and pushed. This was a
  deliberate reversal to let an agent record an already-executed trade
  when a live auto-mode permission block prevented any other path; treat
  it as the current policy, not a one-off exception. Never edit, copy from
  production, or commit runtime state for the files that remain untracked:
  `price_history.json`, `scanner_state.json`, `position_state.json`, and
  `research_agent/research_log.json`. Temporary test fixtures are distinct
  from production state. Keep development folders separate from a live runner.
- Keep secrets, `.env` files, credentials, private keys, tokens, and local
  environments out of Git and handoffs. Do not display or automatically copy
  credentials. If live access is ever explicitly required, the owner configures
  it separately in the intended environment; it is not part of this workflow.
  An ignore rule does not untrack a file already committed.
- Dated `daily_logs/*.md` and `research_notes/*.md` are intentional project
  records. Do not fabricate new live records during a development task.

## Ownership and the default handoff

1. Agree on one objective, an implementing agent, a reviewing agent, and the
   files/subsystem in scope. Use a task branch such as `codex/feature-name`
   or `claude/feature-name`; do not implement on `main`.
2. Copy [the template](docs/handoffs/TEMPLATE.md) to
   `docs/handoffs/<unique-task-id>.md`. Only that task's current owner writes
   it. Do not create a shared `current-status.md` for parallel tasks.
3. Implement, inspect the diff, run the relevant tests plus the full suite,
   and save focused commits. Stage named files, not an indiscriminate
   `git add .`. Review `git diff --cached` before committing.
4. Record the exact implementation commit, original base commit, tests and
   results, outstanding work, environment, and next agent in the task note.
   Commit the note separately if needed. Its own commit can be found with
   `git log -1 --format=%H -- docs/handoffs/<unique-task-id>.md`; a file cannot
   contain the hash of the commit that first saves that same file.
5. Set the note to `ready-for-review`, stop the implementing agent, and give
   the reviewer the folder, branch, note path, and implementation SHA.
   A reviewer is not automatically the new implementation owner.
6. The receiver verifies the actual branch, status, commits, diff, affected
   code, and test results before continuing. A handoff is a claim to check,
   not proof. Re-run relevant checks and the full suite at the reviewed
   revision; report anything that could not be verified.
7. **Review findings first**, with file/line, impact, and severity. If there
   are no findings, say so and give verification limits. Do not silently fix
   the implementation. The reviewer may write a separate
   `docs/handoffs/<task-id>.review-<agent>.md` report on its own branch.
8. For corrections, the owner explicitly assigns the task back to the original
   implementer, or transfers implementation ownership after the previous
   writer stops. Alternatively authorize a fix on a separate task branch in
   a separate workspace. Record the transfer; a review request alone is not
   permission to make corrective edits.

To alternate in one folder: stop Codex, open that exact folder in Claude Code
and supply the review prompt; after the review, stop Claude Code before
resuming Codex there. Reverse the names for a Claude implementation reviewed
by Codex. Neither tool remembers the other's chat, so always pass the note.

Using the prepared separate folders is usually easier: Claude reviews the
saved revision in its own folder while Codex's task is paused. To review a
later task, first ensure the Claude folder is clean and idle, then create a
new review branch there at the supplied implementation commit:

```text
git switch -c claude/review-feature IMPLEMENTATION_SHA
```

Replace `IMPLEMENTATION_SHA` with the real hash. For Codex reviewing Claude,
use `codex/review-feature`. Do not reuse a branch name that already exists.
Worktrees share local commits immediately; no push is needed. Separate clones
need an explicitly authorized fetch/transfer before a local commit is visible.

## Optional simultaneous implementation

Use different worktrees or clones, different task branches, and different
task notes. Assign non-overlapping tasks, for example one agent changes
research digest formatting while the other improves a pure trading helper.
Name the allowed files and interface assumptions in each note.

Shared files such as config, shared instructions, or a common test helper get
one designated owner. Coordinate an overlap before editing; Git isolation
prevents filesystem collisions but does not prevent incompatible designs or
merge conflicts. Do not update another task's note, switch its branch, remove
its worktree, or edit files through its path.

From an idle control clone, these create two new task folders without changing
the control folder's branch or files (replace the example task names):

```text
git fetch origin
git worktree add --no-track -b codex/research-digest ../git-journey-codex-research-digest origin/main
git worktree add --no-track -b claude/trading-helper ../git-journey-claude-trading-helper origin/main
git worktree list
```

Use the approved shared setup commit as the starting ref instead of
`origin/main` until this collaboration setup has been reviewed and merged.
Do not start from an old default branch that lacks the instructions.
If a task needs another unmerged task, declare the dependency and use its
agreed commit as the base. Only the controlling owner manages worktrees.
Worktree folders must remain alongside their shared control clone; deleting
the control clone breaks their Git links. A worktree's `.git` is a pointer,
so copying that folder alone is not a backup or a new clone.

## Dependencies and checks

No application build, packaging, lint, or CI command was configured when this
setup was added. The existing production modules use the Python standard
library; the test dependency is pinned in `requirements-dev.txt`.
Python 3.12 is the version verified for this setup.

Each worktree needs its **own** ignored `.venv`. Git does not carry it, ignored
configuration, runtime files, MCP login, or agent conversation state to another
worktree. Git configuration and hooks may be shared through the control clone;
do not change repository-wide hooks/settings as an incidental task.

Windows PowerShell, from each worktree root (the `py` launcher requires a
normal Python installation; substitute an installed Python executable if needed):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest trading_agent/tests/ research_agent/tests/
git diff --check
git status --short --branch
```

macOS/Linux, from each worktree root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest trading_agent/tests/ research_agent/tests/
git diff --check
git status --short --branch
```

The underlying required suite is
`python3 -m pytest trading_agent/tests/ research_agent/tests/`
(use the corresponding environment's Python on Windows). For a targeted check,
substitute a test file such as `trading_agent/tests/test_scanner_signals.py`;
still run both full test directories before declaring a change done.
Tests are not real historical backtests or verification of a live account.

Run checks in development worktrees with no production runtime state.
This setup closes existing tests' temporary file handles for Windows and
gives the invalid-CLI test explicit temporary state paths. Older revisions
lack those fixes: run them only in a disposable source copy, not a live checkout.
Record the command, revision, Python/pytest versions, platform, pass/fail counts,
and relevant failures in the task note. Never call an unrun check "passed."

## Review and integration

Merging means combining saved branch histories. It does not guarantee their
combined behavior is correct. A push uploads commits to GitHub; a local commit
does not. Deployment and live trading are separate actions.

No push, default-branch merge, deployment, or live operation is part of setup.
For future tasks, obtain the owner's authorization for publication/integration.
Do not force-push. Keep commits focused and retain reviewable history.

Before proposing integration, check each task's saved diff and test evidence.
When authorized to combine tasks, use a fresh integration worktree and branch
so `main` and both agents' folders remain unchanged. Example commands for a
later, authorized integration (not performed by setup):

```text
git fetch origin
git worktree add --no-track -b integration/research-and-helper ../git-journey-integration origin/main
cd ../git-journey-integration
git merge --no-ff codex/research-digest
git merge --no-ff claude/trading-helper
```

Run these sequentially and stop at any conflict; do not blindly continue the
second merge. Inspect both intended changes, resolve each conflict deliberately,
stage only the resolved files, and finish that merge. If the intended result is
unclear, leave the integration branch paused and ask the owner. Do not select
"ours" or "theirs" for every file as a shortcut.

Create the integration worktree's own environment and run the full suite on the
**combined** result, even if both tasks passed alone. Review the final diff
against `origin/main`, record checks, then present the result for the owner's
approved PR/merge process. Never bypass a failing check just because it is old.
Do not deploy or restart a live runner as a side effect of merging.

## Starter prompts

**Implementer** (replace bracketed fields):

> Read AGENTS.md or CLAUDE.md and COLLABORATION.md. Implement [objective] in
> [absolute workspace], on [codex/task-name or claude/task-name]. You are the
> sole implementation owner; [other agent] will review. Scope: [allowed files].
> Inspect Git status, base, and existing work first. Use
> docs/handoffs/[task-id].md, save focused commits, and record the exact revision
> and test evidence. Follow the production boundaries. Stop at ready-for-review.
> Do not push, merge into main, deploy, or run live trading.

**Reviewer** (replace bracketed fields):

> Read AGENTS.md or CLAUDE.md, COLLABORATION.md, and
> docs/handoffs/[task-id].md. Review [implementation SHA] against [base SHA] in
> [absolute workspace/review branch]. The implementer is paused. Verify the
> actual Git diff and relevant code, compare the handoff to reality, and run
> the relevant checks plus the full suite. Report findings first with file/line,
> impact, and severity; otherwise state no findings and verification limits.
> Do not make corrective edits without a clear ownership transfer or a separately
> authorized fix task/workspace. Do not push, merge, deploy, or use live tools.
