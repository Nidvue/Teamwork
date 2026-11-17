# Test-layer gap matrix (T-0009)

Owner: Tester
Related: Board.md, [M26-test-audit.md](M26-test-audit.md), [Testing.md](../../../references/Testing.md), [the plan](../Plan.md)

## 1. What was measured

`teamwork.py tests plan` at `a978c6b2` reported 41 GAP rows: 39 `missing` plus 2
`failing` acceptance rows (TS-0117/TS-0118, Reviewer-owned). This matrix assigns
every row one owner and one decision. No area was renamed, no layer narrowed with
`--layers`, and no requirement was edited to make a row disappear.

## 2. Integration rows recorded now (owner: Tester)

13 of the 17 integration rows now have a passing record. Each command was run in
the T-0009 worktree; the full log is `Agents/Tester/Reports/T-0009-integration-runs.log`
and is bound as the record artifact.

| area | layer | record | command (`venv/bin/python -m pytest -q ...`) | result |
|---|---|---|---|---|
| agent-state-display | integration | TS-0124 | tests/integration/test_agent_state_round3.py | 5 passed in 3.60s |
| agent-state-row | integration | TS-0125 | tests/integration/test_agent_state_width_matrix.py | 5 passed in 1.64s |
| board | integration | TS-0126 | tests/integration/test_board_flow.py | 5 passed in 0.96s |
| ci-shard-matrix | integration | TS-0127 | tests/integration/test_ci_gate_surfaces.py | 6 passed in 0.17s |
| design | integration | TS-0128 | tests/integration/test_ui_refresh_flow.py | 5 passed in 0.83s |
| docs-audit | integration | TS-0129 | tests/integration/test_docs_pipeline_flow.py | 6 passed in 5.90s |
| docs-audit-citations | integration | TS-0130 | tests/integration/test_links_flow.py | 9 passed in 1.81s |
| pr-merge | integration | TS-0132 | tests/integration/test_merge_identity_flow.py | 3 passed in 0.09s |
| privacy-scan | integration | TS-0133 | tests/integration/test_makefile_flow.py | 9 passed in 3.58s |
| release-consistency | integration | TS-0137 | tests/integration/test_release_consistency_integration.py | 19 passed in 21.37s |
| release-gate | integration | TS-0138 | tests/integration/test_release_gate_flow.py | 12 passed in 2.56s |
| release-readiness | integration | TS-0139 | tests/integration/test_release_traceability_flow.py | 10 passed in 2.11s |
| status-widget | integration | TS-0140 | tests/integration/test_status_contract.py | 6 passed in 2.77s |

## 3. Integration rows that need a test, not a record (owner: Tester)

These four rows are a real coverage gap: no integration test asserts the area.
Recording them now would be a fabricated pass, so `pi-package` is queued as
**T-0010** and the other three as **T-0011** (tester queue), each with the
assertion it must make.

| area | layer | owner | decision | evidence it is missing |
|---|---|---|---|---|
| pi-package | integration | Tester | queued T-0010 - the integration test exists on `tester/t-0010` at `8e99ff0b`, not at this revision | `rg -l 'pi[-_]package' tests/integration/` -> one hit, `test_status_contract.py:28`, the build-script path only; `tests/unit/test_pi_package.py` is the unit layer |
| widget | integration | Tester | queued T-0011 - write the assertion | `pytest tests/integration/test_status_contract.py -k widget` -> 6 deselected |
| widget-header | integration | Tester | queued T-0011 - write the assertion | `pytest tests/integration/test_status_contract.py -k header` -> 6 deselected |
| security-audit | integration | Tester | queued T-0011 - write the assertion | `rg -l security-audit tests/` -> only unit files, no integration file |

## 4. Delegated: unit layer (owner: Developer, T-0085)

15 rows. The unit layer belongs to the Developer; the Tester does not write it.
Each needs `teamwork.py tests add --layer unit --area <a>` and a run at the head.

`agent-state-row`, `agent-state-width-matrix`, `board`, `ci-shard-matrix`,
`design`, `docs-audit`, `docs-audit-citations`, `pi-package`, `privacy-scan`,
`release-consistency`, `release-readiness`, `security-audit`, `ui-agent-state`,
`widget`, `widget-header`.

## 5. Delegated: acceptance layer (owner: Reviewer, T-0009 on the reviewer queue)

8 rows. Two of them are the failing rows the task hands to the Reviewer.

| area | layer | state | owner decision |
|---|---|---|---|
| board | acceptance | missing | Reviewer T-0009 |
| ci-shard-matrix | acceptance | missing | Reviewer T-0009 |
| docs-audit | acceptance | FAILING | Reviewer T-0009 - re-run first |
| docs-audit-citations | acceptance | FAILING | Reviewer T-0009 - re-run first |
| privacy-scan | acceptance | missing | Reviewer T-0009 |
| release-gate | acceptance | missing | Reviewer T-0009 |
| security-audit | acceptance | missing | Reviewer T-0009 |
| widget | acceptance | missing | Reviewer T-0009 |

## 6. Delegated: release layer (owner: Release Engineer, T-0005)

1 row: `changelog`/release. Command: `venv/bin/python scripts/check_release_consistency.py --offline`,
then `teamwork.py tests add --layer release --area changelog` and record the run.

## 7. Dead areas

None. Every one of the 41 area names still exists in the shipped tree and in a
requirement record, so no row is retired here and no requirement was deleted.

## 8. Proof

- `teamwork.py tests plan` -> 41 GAP rows at `a978c6b2`; after the 13 records the
  integration column of those areas reads passing (`TS-0124`..`TS-0130`, `TS-0132`, `TS-0133`, `TS-0137`..`TS-0140`).
- The 13 pytest commands in section 2 each exited 0 (log bound as the artifact).
- The remaining 28 rows name their new task id above, so none is unowned.
