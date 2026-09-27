# Handoff: <unique task id>

Copy this file to `docs/handoffs/<unique-task-id>.md`.
One owner writes this task note; other tasks use other filenames.
Keep secrets, account details, raw live responses, and credentials out.

## Objective and scope

- Objective:
- Allowed files/subsystems:
- Out of scope:
- Dependencies on other tasks / agreed interfaces:

## Ownership and location

- Status: active | paused | ready-for-review | changes-requested | complete
- Assigned implementing agent:
- Assigned reviewing agent:
- Current implementation owner:
- Next agent and role (review does not transfer implementation ownership):
- Ownership transfer, if any (from, to, date, owner authorization):
- Absolute workspace path:
- Task branch:
- Remote and default branch (no embedded credentials):
- Original base commit (full SHA):
- Latest implementation commit (full SHA; excludes this note's later commit):
- Latest handoff commit: resolve with
  `git log -1 --format=%H -- docs/handoffs/<unique-task-id>.md`.
- Working tree at handoff (clean, or exact uncommitted files and why):
- Other active workspaces / files reserved to other tasks:

## Completed changes

- What changed, why, and affected files:
- Plan tasks: done / in progress / pending:
- Decisions or deviations from the original plan:

## Tests and results

- Tested implementation revision:
- Environment: OS, Python, pytest, dependencies/local setup:
- Exact commands:
- Results and counts: passed | failed | not run (reason):
- Evidence location or concise relevant output (sanitize before committing):
- Any baseline failure and how it was distinguished from a regression:
- Historical backtest evidence, if strategy behavior changed:

## Outstanding issues and risks

- Unfinished work:
- Known limitations:
- Questions requiring an owner decision:
- Missing environment prerequisites (names only, never values of secrets):

## Next steps

1. Receiver: verify folder, branch, Git status, base, latest commit and actual diff.
2. Inspect changed code and test evidence; re-run relevant checks and full suite.
3. Report any drift between this note and the repository before continuing.
4. Reviewer: report findings first; do not silently fix them.
5. Next task-specific action:

## Receiver acknowledgment

Write only after a clear transfer allows you to own this note. Otherwise put
review findings in `<task-id>.review-<agent>.md` on your review branch.

- Received by / date:
- Actual inspected implementation SHA:
- Aligned with handoff, or differences found:
- Independently verified checks:
- Findings/report location:
- Next implementation owner and agreed action:
