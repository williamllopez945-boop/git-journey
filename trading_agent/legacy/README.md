# legacy/

Modules that no live path calls. Kept, with their tests, so re-enabling one is a
wiring change rather than a rebuild.

| Module | Disabled | Why |
|---|---|---|
| `income_ex_dividend.py` | 2026-10-16 (owner request) | Ex-dividend timing gate for income-sleeve entries. |
| `income_candidates.py` | 2026-10-16 (owner request) | `filter_by_liquidity` spread screen; no longer called from `income_cycle.py`. |

Import path: `trading_agent.legacy.<module>`. The tests stay in `trading_agent/tests/`.
See `PLAYBOOK.md` "Income sleeve" and `CHANGELOG.md` (2026-10-16) for the history.
