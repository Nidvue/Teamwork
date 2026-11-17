# T-0085: unit-layer records for the 15 areas the plan required with no record

Owner: Developer. Task: T-0085. Revision: `612f6c19` (`git -C <worktree> rev-parse HEAD`).
Related: the board | the plan | the release - named here rather than linked: a one-way markdown edge fails `teamwork links`, and the precedent is docs/Team/reports/M26-code-audit.md.

## 1. Why this record exists

`teamwork.py tests plan` marked `unit?` (required, no record) on 15 areas, so
`loop` could not reach STOP. The unit suites for those areas already existed;
nothing was missing but the record of the run. This task runs each suite in the
task worktree (clean tree at `612f6c19`) and records the result, so the gap is
`unit+` or an honest `unit!` instead of `unit?`.

## 2. What was recorded

Every command was run from the clean worktree at `612f6c19`; `--artifact` binds
the log `.pi/Teamwork/Teams/Teamwork/Agents/Developer/Reports/T-0085-unit-runs-612f6c19.log`.

| Area | Command | Result | Record |
|---|---|---|---|
| agent-state-row | `pytest -q tests/unit/test_pi_status_render.py` | 24 passed | TS-0146 |
| agent-state-width-matrix | `pytest -q tests/unit/test_pi_status_render.py` | 24 passed | TS-0157 |
| ui-agent-state | `pytest -q tests/unit/test_pi_status_render.py tests/unit/test_lane_display.py` | 40 passed | TS-0147 |
| widget | `pytest -q tests/unit/test_pi_status_render.py` | 24 passed | TS-0158 |
| widget-header | `pytest -q tests/unit/test_pi_status_render.py` | 24 passed | TS-0159 |
| board | `pytest -q tests/unit/test_board_matches_tool.py tests/unit/test_board_feature_section.py` | 17 passed, 4 skipped | TS-0148 |
| ci-shard-matrix | `pytest -q tests/unit/test_ci_contracts.py` | 79 passed | TS-0149 |
| design | `pytest -q tests/unit/test_ui_readme.py` | 5 passed | TS-0150 |
| docs-audit | `pytest -q tests/unit/test_docs_contracts.py` | 2 failed, 18 passed | TS-0151 (fail) |
| docs-audit-citations | `pytest -q tests/unit/test_docs_contracts.py tests/unit/test_research_sources.py` | 2 failed, 23 passed | TS-0152 (fail) |
| pi-package | `pytest -q tests/unit/test_pi_package.py` | 9 passed | TS-0153 |
| privacy-scan | `pytest -q tests/unit/test_privacy_scan.py tests/unit/test_privacy_scan_load_failure.py` | 190 passed | TS-0154 |
| release-consistency | `pytest -q tests/unit/test_release_consistency.py` | 109 passed | TS-0155 |
| release-readiness | `pytest -q tests/unit/test_release_traceability.py` | 25 passed, 1 skipped | TS-0156 |
| security-audit | already passing at this revision | credited TS-0134 | not re-run |

## 3. The two reds, and why they are recorded red

`tests/unit/test_docs_contracts.py` fails two mutant cases at this revision, for a
cause outside this task's boundary:

```text
docs/Team/reports/M26-test-audit.md: [the writing standard](../../../AGENTS.md) does not resolve
FAILED test_mutant_a_link_inside_a_code_fence_is_not_reported
FAILED test_mutant_a_quoted_archive_evidence_link_is_not_reported
```

The link is authored in the Tester's M26 audit report, committed at this
revision; the checker resolves it against the copied `docs/` tree and reports it.
Reproduce on the main checkout: `venv/bin/python -m pytest -q tests/unit/test_docs_contracts.py`
-> `3 failed, 17 passed` (the third failure is the untracked
`docs/Team/Reviews/M26-docs-audit.md` in that checkout). Fixing it means editing a
report another role owns, so it is routed, not patched here.

## 4. Scope

No production code, no test file and no other role's document is touched: the
deliverable is the record set plus this report.
