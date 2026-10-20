# PLAN - milestones and task graph

Owner: Project Manager. One row per task; `deps` must be `done` before it runs.
Priority: P0 code, P1 tests, P2 docs.

Related: [Project](Project.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md) · [pi packaging](Pi-Packaging.md)

## Status summary (2026-10-20, `main` @ `74b5522`)

| milestone | exit condition | state |
|---|---|---|
| M0 Audit follow-up | `loop` STOP + `audit` 0 problems | done - T-0001..T-0007 |
| M1 Package the engine | `selftest` + installed wheel `--version` | done |
| M2 Make it attractive | README demo, strict docs site, 0 broken links | done |
| M3 Independent verification | every deliverable has a Reviewer verdict | done |
| M4 Publish | `v1.0.0` release with wheel, sdist, `SHA256SUMS`, SBOM | done - latest tag `v1.1.0` (`CHANGELOG` 1.1.1 and 1.1.2 written, untagged) |
| M5 Post-1.0 hardening | typed module split, Windows-green matrix, dependency upkeep | done - T-0010..T-0016, closing T-0017 |
| M6 Evidence packets + repro gate | hashed evidence artifacts, repro-first bug gate, Reviewer verdicts | done - T-0020..T-0025 |
| M7 Reviewer fan-out + claims | `pulse` hands each unclaimed deliverable to a different idle Reviewer lane | done - developer T-0001, merge `8f210bc` |
| M8 Records hygiene | archive merge fields proved or `pending`, Plan lists each milestone once, export names its head | done - ceo T-0028, merge `62ef5db` (P-0027, Reviewer-4); the Plan row below still said `review` and is corrected here |
| M9 Harness^2 adoption | AC-H1..AC-H8 verified on the merged revision | open - 3 lanes unmerged, `pytest -q` red on AC-5 |

## M5 - post-1.0 hardening (closed)

Exit: `pytest -q` green locally and in CI on every OS of the matrix, no open red
run, and the governance records match the merged revision.

| id | task | role | prio | deps | artifact | status | evidence |
|---|---|---|---|---|---|---|---|
| T-0010 | Export the audit manifest with a workspace `TeamId` | ceo | P2 | - | `docs/Team/AuditManifest.json` | done | commit `384df6a` |
| T-0011 | Split `engine.py` into typed modules | ceo | P1 | - | `src/teamwork/*.py` | done | commit `c8fb469` |
| T-0012 | Skip the POSIX umask test on Windows | ceo | P1 | T-0011 | `tests/unit/test_integrity_fixes.py` | done | commit `f2e3b5a`; CI `39173857076` windows jobs green |
| T-0013 | Fix import order in the Windows skip test | ceo | P1 | T-0012 | `tests/unit/test_integrity_fixes.py` | done | commit `b7fe03b` |
| T-0014 | Land the three Dependabot action bumps | ceo | P0 | - | `.github/workflows/release.yml` | done | commit `9b56f1b`; PR #17 17/17 checks; supersedes #11-#13 |
| T-0015 | Refresh stale governance docs to the merged revision | ceo | P1 | - | this file, `Board.md`, `Risks.md`, `Release.md` | done | commit `1d49c21`; passed on round 3 after two evidence-backed fails |
| T-0016 | `ensure_gitignore` orphan headers and glob-covered entries | ceo | P1 | - | `src/teamwork/engine.py`, `tests/unit/test_gitignore_bootstrap.py` | done | commit `4cd8afc`; 5 regression tests, 3 of which fail on the pre-fix engine |
| T-0017 | Close M5: board done + audit manifest export | ceo | P1 | T-0014..T-0016 | this file, `Board.md`, `AuditManifest.json` | done | merge `ff419fa` |

No M5 task is open; the role queue (`teamwork.py task list ceo`) is the only
authoritative source for a task's exact state.

## M6 - evidence packets + repro gate (closed)

Exit: evidence carries a hashed artifact, a defect proves its failing run before
the fix, and both passed independent review. Source: [Research](Research.md) 6
(A2 + A3).

| id | task | role | prio | artifact | status | evidence |
|---|---|---|---|---|---|---|
| T-0020 | Evidence packets + repro-first gate | ceo | P1 | `src/teamwork/{engine,records}.py`, two test modules | done | `8694073`..`9d59976`; `Archive.md` |
| T-0021 | Review records baseline + replay | ceo | P2 | `engine.py`, `docs/guide/cli.md` | done | `2297adc` |
| T-0022 | The repro proof belongs to the defect task | ceo | P3 | `engine.py`, `records.py`, docs | done | `3934690`; 1 fail + 2 review rounds |
| T-0024 | Close-out audit flow as a team skill | ceo | P2 | `.agents/skills/ceo-audit-close/SKILL.md` | done | `b662faf` |
| T-0025 | Fix-forward: allow `.agents` at the root | ceo | P0 | `tests/unit/test_hygiene.py` | done | `d72f44b`; repro `b662faf` -> `a4ead34` |
| T-0023 | Bind the adoption decision + closing manifest | ceo | P3 | `Decisions.md`, `AuditManifest.json` | done | merge `ae80950`; reviewed after 1 fail + 1 pass |

## M7 - reviewer fan-out + claims (closed)

Exit: `pulse` gives each unclaimed deliverable to a different idle Reviewer lane,
who holds it as a record; review is parallel, not serialised by the dispatcher.

| id | task | role | prio | artifact | status | evidence |
|---|---|---|---|---|---|---|
| T-0001 | Fan review out across Reviewer lanes | developer | P0 | `engine.py`, `records.py`, `tests/unit/test_review_fanout.py`, docs | done | merge `8f210bc`; 10 new unit tests; repro `479742d` -> `76d5f76` |

## M8 - records hygiene (closed)

Exit: archive merge fields carry a proved revision or say `pending`, the Plan
lists each milestone once, and the export names the head it was taken from.

| id | task | role | prio | artifact | status | evidence |
|---|---|---|---|---|---|---|
| T-0028 | Repair archive merge fields, de-duplicate Plan, re-pin manifest | ceo | P1 | `Archive.md`, `Plan.md`, `AuditManifest.json` | done | merge `62ef5db` (P-0027, Reviewer-4); 20 of 37 merge fields proved then, the rest say `pending` and later entries fill their own field per PR |

## M9 - Harness^2 adoption (open)

Exit: AC-H1..AC-H8 in `Criteria.md` verified on the merged revision - `harness`
and `hooks` registered and documented, the ordered review rubric and the
untrusted-material rule stated where agents read them, and `pytest -q` clean on
`main`. Source: [Research](Research.md) 8, whose adoption order is H10+H5+H2,
then H1+H3+H8, then H4, then the doctrine rows H6/H7/H9.

The intake brief numbers this milestone M8. The M8 above is the records-hygiene
milestone and its own exit condition requires each milestone to be listed once,
so the Harness^2 adoption is M9. A row is `done` only when its merge is on
`main`; an open PR is `review`, a PR sent back for rework is `doing`.

| id | task | role | prio | deps | artifact | status | evidence |
|---|---|---|---|---|---|---|---|
| T-0001 | Research section 8: verdict table, adoption order, falsifiers, sources | product-manager | P1 | - | `docs/Team/Research.md` 8, `tests/unit/test_research_sources.py` | done | merge `73be637` (P-0005); 5 passed @ `38e6890` |
| T-0001 | Freeze the harness-surface and hooks CLI contract; record the decisions | architect | P1 | - | `docs/Team/Architecture.md` 11, `docs/Team/Decisions.md` | doing | P-0003 changes-requested after 2 rework rounds; head `f476b82` unmerged |
| T-0001 | Engine: `harness list`, `harness lint`, `harness budget` + unit tests | developer | P0 | architect:T-0001 | `src/teamwork/harness.py`, `tests/unit/test_harness_surface.py` | doing | P-0004 changes-requested after 2 rounds (@`a26f5db`, @`5eabdc9`); `harness` absent from `main` |
| T-0002 | Engine: git hooks (in-loop enforcement) + unit tests | developer | P0 | architect:T-0001 | `src/teamwork/hooks.py`, `tests/unit/test_hooks.py` | done | merge `49cd42e` (P-0007); 30 passed @ `2fbd126` |
| T-0001 | Integration + acceptance tests for the harness surface and hooks | tester | P0 | developer:T-0001, developer:T-0002 | `tests/integration/test_harness_cli.py`, `tests/acceptance/test_harness_docs.py` | blocked | branch `21bfcd3` unmerged: 29 failed on `main` (groups and docs absent), 26 passed / 3 failed on the probe merge |
| T-0001 | Docs: reviewer rubric, untrusted-material rule, SKILL.md and CHANGELOG | ceo | P1 | - | `roles/reviewer.md`, `references/Evidence.md`, `SKILL.md` | done | merge `2f44f00` (P-0001), after 2 fail + 1 pass rounds |
| T-0002 | Docs pass for the new surface: cli guide, CHANGELOG, dead-skill trigger line | ceo | P1 | developer:T-0001, developer:T-0002 | `docs/guide/cli.md`, `CHANGELOG.md`, `SKILL.md` | review | P-0008 open at `20a99fd`: `hooks` documented, `harness` deliberately not |
| T-0001 | Run the acceptance record TS-0004 for area harness | reviewer | P2 | tester:T-0001 | acceptance record TS-0004 | todo | filed with owner `tester` by mistake; only the reviewer role can run or remove it |

Two tasks were dropped in this milestone; they are the only `- status: dropped`
rows in the six live queues (`grep -c '^- status: dropped'
.pi/Teamwork/Teams/Teamwork/Roles/*/TaskQueue.md`).

| id | task | role | why dropped |
|---|---|---|---|
| T-0003 | Three measured defects on the harness/hooks branches (list shape, hook marker, root-commit hole) | developer | covered by the fixes it named: the eight-row list landed in developer T-0001 `5eabdc9`, the marker literal and root-commit refusal in developer T-0002 `2fbd126` |
| T-0002 | Architecture 11.2/11.6 drifted from the two branches in four measured ways | architect | superseded: reconciled inside architect T-0001's review rework `f476b82` as amendments A1-A3 and rulings R1-R6 (D-20261020-Architect-8, -9) |

Landed in the same window, outside this milestone's scope:

| id | task | role | status | evidence |
|---|---|---|---|---|
| T-0002 | Fix the hardcoded POSIX `PATH` in `tests/unit/test_skill_refresh.py` | tester | done | merge `090910a` (P-0002) |
| T-0003 | Make the traceability record-resolution guard honest about an empty team tree | tester | done | merge `cc86e6d` (P-0006); it is why product-manager T-0002 exists |
| T-0003 | RED gate: the privacy scan fails at HEAD on a forge squash merge | ceo | blocked | needs a ruling on the three options in the task record |
| T-0004 | AC-5's claimed green is false on `main` | ceo | todo | the one failure left in `pytest -q`; see [Board](Board.md) |

## Closed milestones (evidence on file)

| id | task | role | result | evidence |
|---|---|---|---|---|
| T-0001 | Full-project audit: parser, ledger, paths, locks, privacy, CI | ceo | done | `make ci` -> all gates passed; 336 passed, 1 skipped |
| T-0002 | Scope the audit-manifest anchor to the workspace id | ceo | done | `pytest tests/unit/test_ledger.py` -> 17 passed; `audit` -> 0 |
| T-0003 | Repo-local role identity, `--strict-authors`, exit-code docs | ceo | done | commit `1e646a9` |
| T-0004 | Accurate exit-code table; identity guard tests | ceo | done | commit `043d483` |
| T-0005 | Fix `dispute sign` undeclared `--force` | ceo | done | commit `61eecc9` |
| T-0006 | Correct the exit-code example; tribunal sign coverage | ceo | done | commit `29dc42f` |
| T-0007 | Correct the T-0005 archive evidence | ceo | done | commit `b05d04a` |
| T-0008 | Residual audit items: umask, UTF-16 BOM, nested repo, coverage, stale board | ceo | done | commit `e7a7d4d` |
| T-0009 | Fix the `pr merge` commit message acting role | ceo | done | commit `9e1ab8f` |

## Task-graph integrity

The task graph is checked against `.pi/Teamwork/Teams/Teamwork/Roles/*/TaskQueue.md`.
A task census moves every time any task changes status, so this section states
the invariants that were verified rather than a snapshot count.

Verified at the plan-layer check (2026-10-19):

| invariant | result |
|---|---|
| dangling dependencies | 0 |
| dependency cycles | 0 |
| one queue holding the same task id twice | 0 |
| tasks missing a priority | 0 |
| queue directories that are not a role | 0 |

Each task block is `## T-xxxx` followed by `- priority:`, `- status:` and
`- deps:` lines. A dependency is written `role:T-xxxx` and resolves against that
role's queue; the role name is compared with separators and case removed, so
`security-auditor`, `SecurityAuditor` and `securityauditor` all resolve to
`Roles/SecurityAuditor/TaskQueue.md`.

Task ids are allocated per role queue, so every role legitimately owns a
`T-0001`; that is not a duplicate. What is a defect is one queue carrying the
same id twice, or a queue directory whose name is not a role in the tree.

Re-measure the census (snapshot only, not evidence):

```sh
grep -h '^- status:' .pi/Teamwork/Teams/Teamwork/Roles/*/TaskQueue.md | sort | uniq -c
```

Re-check the dependencies (they are structural, so the result does not move with
the task count):

```sh
grep -h '^- deps: .' .pi/Teamwork/Teams/Teamwork/Roles/*/TaskQueue.md
```

Each `role:T-xxxx` above must name an existing queue directory and an existing
`## T-xxxx` block in it; a name that resolves nowhere is a dangling dependency.

The invariants are executable: `tests/unit/test_task_graph_integrity.py` parses
the shared queues with role-qualified node keys and fails on a dangling dep, a
cycle, a duplicate open id, a task with no priority, or this section acquiring a
census again.

```sh
PYTHONPATH=src python -m pytest tests/unit/test_task_graph_integrity.py -q
```

## Parallel rules

- Interfaces were frozen in [Architecture](Architecture.md) before any lane
  started; one writer per file (see the ownership table there).
- Tests are written from the frozen contract, in parallel with implementation.
- Docs never block code or tests.
- Only the CEO pushes, tags, releases or writes to GitHub.
