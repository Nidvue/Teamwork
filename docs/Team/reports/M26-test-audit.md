# M26 test audit: vacuous tests proved by mutation, coverage, hermeticity, flake

Owner: Tester. Task: T-0008 (M26 audit; audit only, no fix).
Related: [the board](../Board.md) | [the plan](../Plan.md) | [M26 code audit](M26-code-audit.md) | [the writing standard](../../../AGENTS.md)

Audited revision: `d6ab6d23` (`git log --oneline -1` at the audit head), on a
dedicated worktree `Runtime/Worktrees/Tester/T-0008`. No source file and no test
file is changed by this task; every mutant below was applied to that worktree,
its targets run, and the file restored (`git status --porcelain` clean except the
audit scratch directory).

## 1. Conclusion

The suite is strong where the team already spent effort: **both `_preflight_undo`
mutants are killed** (the closed-lane gate is really tested), and **the ledger
chain and `fold_finished_seats` (the seat fold at reconcile) are killed**. That
`fold_finished_seats` verdict says nothing about `records.merge_tasks`, the
duplicate-task fold, which no test executes at all (F3). The defects are elsewhere:

1. **The review gate's mechanical check is reached but not asserted.** Two mutants
   of `engine.review_mechanical` survive the unit suite while a hit-marker proves
   the function is executed by it. The revision-matching arm and the
   no-revision arm are dead code to the suite. Findings 1-2.
2. **`records.merge_tasks` is never executed by any test at all.** Not in unit
   (2,647 passed), not in integration+acceptance (459 passed). The duplicate-task
   fold - the mechanism that keeps one title from becoming two board rows - has
   zero coverage. Finding 3.
3. **`lanes.acquire_slot`'s renewal arm is never executed.** The cap arm is
   killed; the "this lane already holds a lease, renew it" arm is not reached by
   any test. Finding 4.
4. **Three integration/acceptance tests fail on a pristine worktree**, so they are
   not hermetic: they depend on ambient state of the live checkout. F7.

Mutation score of this audit: **5 killed / 6 survived** over 11 hand-built
mutants - M1, M2, M3, M4, M5 and M7 survived; M6, `ledger_verify`,
`fold_finished_seats` and both `_preflight_undo` mutants were killed. The M19
audit's 8/14 is superseded by these 11, which target the paths this task names.
F6 and F9 were withdrawn on review (2.2) and are not in that count.

## 2. Method

| What | How |
|---|---|
| Static vacuity scan | AST walk of every `test_*` function in `tests/`: constant-truth assert, self-compare assert, no-assert bodies. 2,683 test functions |
| Mutation | one edit per mutant, exact-text, asserted unique before the write; targets run with `-x -q`; file restored from the original string, `git status` verified |
| Reachability | the same edit replaced by a hit-marker write (`/tmp/m26_M*`), full `tests/unit` then full `tests/integration tests/acceptance`; a marker file proves a test **executes** the line, its absence proves **no test reaches it** |
| Hazards / flake | regex scan of `tests/**/*.py` for `fcntl`, `signal`, `symlink`, hardcoded `/tmp` / `/home`, `umask`, `locale`, `\r\n`, `time.sleep`, `subprocess.*` without timeout, network, live `.pi` tree |
| Matrix | `teamwork.py tests plan` gap list |

Scratch: `.pi-audit/scan.py`, `.pi-audit/mutate.py` in the worktree (untracked, removed at close).

### 2.1 Base-line reds (pre-existing, not caused by this task)

| Command | Result |
|---|---|
| `pytest -q tests/unit` (no mutant, markers only) | `1 failed, 2647 passed, 7 skipped in 272.98s` |
| `pytest -q tests/integration tests/acceptance` (no mutant) | `3 failed, 459 passed, 3 skipped in 109.78s` |

The 4 reds: `test_traceability_matrix.py::test_every_deterministic_state_matches_a_real_run`,
`test_makefile_flow.py::test_lint_is_green_on_this_checkout`,
`test_memory_flow_certification.py::test_a_lane_run_leaves_one_short_entry_a_sibling_instance_sees`,
`test_acceptance_ci_contracts.py::test_clean_tree_accepts_with_exit_0`.
`test_hygiene.py::test_repository_root_contains_only_expected_entries` was in this
list at the audit head only because the audit's own scratch `.pi-audit/` sat
untracked in the repository root; on the clean worktree it is green
(`1 passed, 10 deselected in 0.02s`). See 2.2.

### 2.2 Withdrawn on review at `d6ab6d23` (refuted by the cited code)

| Id | Claim that was wrong | Refuting command -> result |
|---|---|---|
| F6 | "reds on any lane's untracked scratch directory" | the enumeration skips every `git check-ignore` match (`tests/unit/test_hygiene.py:134-139`) and a lane's scratch lives under the gitignored `.pi/`; on the clean worktree `pytest -q tests/unit/test_hygiene.py -k repository_root` -> `1 passed, 10 deselected in 0.02s` |
| F9 | "a fixed sleep before reading the rendered lane list" | `tests/integration/test_lane_display_live.py:83-87` is `deadline = time.time() + 30` / `while time.time() < deadline:` / `break` when every agent is live / `time.sleep(0.5)` as the poll step - the poll-with-deadline the finding recommends is already the code |

## 3. Findings, ranked

### F1 - P0 - `review_mechanical` does not assert that the preflight revision matches
`src/teamwork/engine.py:10853` (`if failed == 0 and _same_revision(sha, revision):`;
`:10855` is the `REVIEW_MECHANICAL_NO` return of that arm, not the mutant target).

- Mutant M4: `and _same_revision(sha, revision)` deleted -> `pytest -q tests/unit/test_review_credit.py tests/unit/test_review_detects.py`
  -> **`29 passed`**. SURVIVED.
- Reachability: marker inside the `for match in _RE_PREFLIGHT_EVIDENCE.finditer(...)` body ->
  `/tmp/m26_M4` **exists** after `pytest -q tests/unit`. The tests call the function, they
  just never build the "a green preflight for a *different* SHA" case.
- Failure it misses: an author self-checks at rev A, the lane is pushed at rev B, the
  reviewer reads "green preflight" and stops. The check silently becomes "any green
  preflight ever recorded on this task".
- Smallest test that closes it: one unit case - task `self_note` carrying
  `preflight @aaaaaaaaaaaa -> 0 failed`, call `review_mechanical(task, "bbbbbbbbbbbbbb")`,
  assert `REVIEW_MECHANICAL_UNKNOWN`.

### F2 - P0 - `review_mechanical`'s no-revision arm is dead code to the suite
`src/teamwork/engine.py:10846` (`if not (revision or "").strip():`).

- Mutant M5: the arm replaced by `if False:` -> same two files -> **`29 passed`**. SURVIVED.
- Marker `/tmp/m26_M5` exists -> the function is reached; the empty-revision case is not.
- Failure it misses: a review packet with no revision returns `UNKNOWN` ("the author did
  not run the mechanical gate") instead of `NA` - the reviewer is told the author skipped a
  gate that cannot apply. A misleading verdict text on a real review path.
- Smallest test: `assert review_mechanical({}, "")[0] == REVIEW_MECHANICAL_NA`.

### F3 - P0 - `records.merge_tasks` has no test at all
`src/teamwork/records.py:1053-1079` (dedupe fold and status fold).

- Mutant M1: `if key in index and key:` -> `if False:` -> `tests/unit/test_pulse_authority.py`
  **`18 passed`**; muter M2: status-fold `if` -> `if False:` -> **`18 passed`**.
- Reachability: marker on the `if key in index` line, full `tests/unit` -> **no
  `/tmp/m26_M1`**; marker again, full `tests/integration tests/acceptance` -> **no
  `/tmp/m26b_M1`, no `/tmp/m26b_M2`**. No test in the repository executes this function.
- Failure it misses: the reconcile that folds duplicate tasks by title, keeps the higher
  priority, fills empty fields and advances `todo` -> `doing`/`done`. Breaking it
  silently duplicates every task row on a two-way reconcile and loses the priority of
  the older copy. This is the duplicate detection the board depends on (the same class
  of duplicate T-0008-as-docs rows exist in the board).
- Smallest test: `merge_tasks([], [task("a", "P0")])` twice with one changed field ->
  assert `len(dst) == 1` and the priority/status survived. No engine, no git.

### F4 - P1 - `lanes.acquire_slot` renewal arm has no test
`src/teamwork/lanes.py:762` (`if name in used:` - a lane that already holds a lease
renews it instead of failing at the cap).

- Mutant M7: `if name in used:` -> `if False:` -> `tests/unit/test_lanes.py`
  **`50 passed in 36.11s`**. SURVIVED.
- Reachability: marker -> absent in `tests/unit` **and** absent in
  `tests/integration tests/acceptance`. The arm is never executed.
- By contrast the cap arm **is** tested: M6 (`if len(used) >= cap:` -> `if False:`)
  -> `1 failed, 11 passed`. KILLED.
- Failure it misses: a lane renewing its own lease is counted twice against the cap, or
  (with the arm dead) its `slot renew` starts returning `False` and the lane stalls at the
  provider cap while it already holds the slot - the exact "never block a lane" rule.
- Smallest test: acquire twice for one agent on a cap-1 provider, assert both calls are
  `(True, 1)` and one file remains.

### F5 - P1 - `required_layers_for`'s declared-area arms are unasserted
`src/teamwork/engine.py:2225` (`return core or staffed or list(DEFAULT_REQUIRED_LAYERS)`).

- Mutant M3: that line -> `return list(DEFAULT_REQUIRED_LAYERS)` -> 70 tests over
  `test_test_records.py`, `test_tasks.py`, `test_features.py` **`70 passed`**. SURVIVED.
- Failure it misses: an area whose plan declares a *subset* (or `ALL_LAYERS_SENTINEL`) gets
  the full core set anyway, so `tests plan` reports gaps that the declaration closed and
  `loop` blocks STOP on a gap nobody owes. (K-0036 already records the cost of this class.)
- Smallest test: a tmp team whose testplan declares `board: unit` -> assert
  `required_layers_for(root, "board") == ["unit"]`.

### F6 - WITHDRAWN - `test_repository_root_contains_only_expected_entries` is correctly scoped
Refuted on review; not counted, no fix proposed. The enumeration already skips every
entry `git check-ignore` matches (`tests/unit/test_hygiene.py:134-139`), and a lane's
scratch lives under the gitignored `.pi/`, so it does not red this test. The red I
recorded was my own `.pi-audit/` directory, created by this audit at the repository root
and not gitignored. On the clean worktree:

```
pytest -q tests/unit/test_hygiene.py -k repository_root -> 1 passed, 10 deselected in 0.02s
```

### F7 - P2 - Three integration/acceptance tests are not hermetic
`tests/integration/test_makefile_flow.py`, `test_memory_flow_certification.py`,
`tests/acceptance/test_acceptance_ci_contracts.py` (see 2.1).

- Proof: they fail on a pristine worktree at `d6ab6d23` with **no** mutant applied
  (`3 failed, 459 passed`) and are named as "the pre-existing acceptance/traceability
  pair" in earlier lane evidence, so they are red across revisions, not flaky.
- Failure it misses: the local signal does not match CI's. A lane cannot distinguish its
  own regression from ambient redness, which is exactly the LOCAL+CI symmetry the charter
  requires.
- Smallest test: each of the three reads its subject through `git show HEAD:<path>` (a
  revision), not the working tree.

### F8 - P2 - Cror-platform: unguarded `os.symlink` in tests that the Windows matrix runs
`tests/integration/test_portability_flow.py:433,462`; `tests/unit/test_release_consistency.py:1482,1501,1518,1539,1558,1573`
- 8 of the 20 `os.symlink` sites in `tests/*.py` (`grep -rn --include='*.py' -o 'os\.symlink'
tests/ | wc -l` -> `20`; 16 are in `test_release_consistency.py`, 2 in
`test_portability_flow.py`). The guard this report first claimed for the other 12 does
not exist: `grep -n 'pytestmark'` finds no module-level skip in either file, so the same
WinError 1314 applies to all 20.

- Hazards on `windows-latest`: symlink creation needs Developer Mode / elevation, so the
  test raises `OSError` (WinError 1314) instead of asserting. `/etc/hostname` as a symlink
  target (`:1573`) does not exist there at all.
- Status: **UNVERIFIED for CI** - no windows job log was read in this audit; the file:line
  evidence is static. Ranked P2 because the windows leg is already the slow/red leg (R-33).

### F9 - WITHDRAWN - the live-display read is a deadline poll, not a fixed sleep
Refuted on review; not counted, no fix proposed. `tests/integration/test_lane_display_live.py:83-87`
is `deadline = time.time() + 30`, `while time.time() < deadline:`, `break` once every
agent is live, `time.sleep(0.5)` as the poll step - the poll-with-deadline this finding
recommended is already the code. The second half is a measured cost, not a flake:
`tests/unit/test_lanes.py` runs real launcher subprocesses, which is why it takes 36.11s
for 50 tests under M7.

### F10 - P2 - 6 "self-compare" asserts are determinism checks, not tautologies - reported, not counted
`tests/integration/test_ci_gate_surfaces.py:105-106`, `tests/unit/test_lane_worktree_per_task.py:38`,
`tests/unit/test_ledger.py:29`, `tests/unit/test_memory_index.py:159`,
`tests/unit/test_pi_status_render.py:300` - each asserts `f(x) == f(x)`.

- These are **two-call** determinism checks and are legitimate (the charter requires the
  second-call case). They cannot fail for a referentially transparent function, so they
  prove less than they read; `test_digest_is_deterministic` sits next to
  `test_digest_frozen_known_value`, which is the assert that actually bites. Not dropped as
  a finding, listed so the next audit does not re-find it: **no `assert True`, no constant
  assert, no self-compare tautology** exists in the suite (0 of 2,683 test functions).

### F11 - P2 - 37 test functions carry no `assert` of their own
`tests/acceptance/test_entrypoints.py` (5), `tests/unit/test_evidence_packets.py` (5),
`tests/unit/test_messages.py` (2), `tests/unit/test_memory_wiki.py` (3), and 22 more
(AST scan). Most delegate to a helper that asserts (`expect_exit`, `raises`) or are
deliberate no-raise cases - the M19 audit found the same three and cleared them.
`tests/unit/test_evidence_packets.py:157,278,282,292,303` are the cluster worth a read
next round: five "refuses"/"no-op" cases in a row are where a deleted assert hides.

## 4. Hazards measured (not rankable as findings without a windows log)

| Class | Sites | Note |
|---|---|---|
| `os.symlink` | 20 | 8 cited in F8; no module-level skip in either file |
| `subprocess.run/call/Popen` | 235 | timeout coverage not measured per site; the ones read in `tests/acceptance/*` pass `timeout=` |
| `time.sleep` | 20 | poll steps with a deadline, or inside generated child scripts (F9 withdrawn) |
| hardcoded `/tmp` or `/home` | 22 | all are *assertions about* such paths (`test_privacy_scan.py`, `test_hygiene.py`), not I/O into them - correct |
| `fcntl`, `signal`, `locale`, `umask` | 0, 0, 0, 2 | umask is saved and restored (`test_integrity_fixes.py:540-546`) |
| live `.pi` tree or real git history | 29 + 11 | F6/F7 are the two that bite |
| network | 16 | all in `tests/integration/probes/` (opt-in probes, not collected by default) |

## 5. Test matrix the team is missing

`teamwork.py tests plan` -> **22 coverage gaps**. The gap is a **record** gap, not a
coverage gap, wherever a test file for the area exists - and the plan cannot tell the
two apart, which is itself the reportable fact.

| Area / layer | Test file exists? | Gap is |
|---|---|---|
| board / unit, integration | yes - 7 `tests/*/test_board_*.py` (`ls tests/*/*board*`) | record only |
| release-consistency / unit, integration | yes - 5 files (`test_release_consistency*.py`) | record only |
| pi-package / unit, integration | yes - `test_pi_package.py`, `test_acceptance_memory_pi_package.py` | record only |
| pr-merge / integration | yes - `test_pr_merge_base_advance.py` | record only |
| agent-state-display, agent-state-row, agent-state-width-matrix, ui-agent-state / unit, integration | yes - `test_agent_state_round3.py`, `test_agent_state_width_matrix.py` | record only |
| widget, status-widget / unit, integration | yes - `test_pi_status_render.py`, `test_lane_display.py` | record only |
| changelog / release, design / unit+integration, docs-audit / unit+integration, ci-shard-matrix / unit+integration | **no file by that name** (`ls tests/*/*<area>*.py` empty for both `-` and `_` spellings) | genuinely uncovered, or covered under another area name |

Actionable for the next lane: the 13 record-only gaps are closed by `tests run --layer
<l> --area <a>` against the command that already exists - no new test needed; the four
remaining areas need a test before a record.

## 6. What this audit did not do

- No fix, no test edit, no source edit (audit only, per the task).
- No CI run was read: F8 is static and marked `UNVERIFIED` for `windows-latest`.
- Coverage was not re-run (the M19 audit's per-function analysis stands); reachability
  here is proved by hit-markers, which is stronger for "does any test execute this line".
