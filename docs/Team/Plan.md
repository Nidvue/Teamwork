# PLAN - milestones and task graph

Owner: Project Manager. One row per task; `deps` must be `done` before it runs.
Priority: P0 code, P1 tests, P2 docs.

Related: [Project](Project.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md) · [pi packaging](Pi-Packaging.md)

## Status summary (2026-10-21, `main` as `git rev-parse --short main` reports it)

The revision named below is the tip this summary was measured at; it is read
from the tip, not pinned, and the next merge moves it. Every state in the
`state` column is read from the queue (`teamwork.py task list <role>`), the
archive (`teamwork.py archive`) and git (`git merge-base --is-ancestor <sha>
main`), never from a brief.

| milestone | exit condition | state |
|---|---|---|
| M0 Audit follow-up | `loop` STOP + `audit` 0 problems | done - T-0001..T-0007 |
| M1 Package the engine | `selftest` + installed wheel `--version` | done |
| M2 Make it attractive | README demo, strict docs site, 0 broken links | done |
| M3 Independent verification | every deliverable has a Reviewer verdict | done |
| M4 Publish | `v1.0.0` release with wheel, sdist, `SHA256SUMS`, SBOM | done - latest tag on the local `main` is `v1.1.0`; `v1.1.2` is tagged on the published side and is not on the local `main` yet (see [Board](Board.md)) |
| M5 Post-1.0 hardening | typed module split, Windows-green matrix, dependency upkeep | done - T-0010..T-0016, closing T-0017 |
| M6 Evidence packets + repro gate | hashed evidence artifacts, repro-first bug gate, Reviewer verdicts | done - T-0020..T-0025 |
| M7 Reviewer fan-out + claims | `pulse` hands each unclaimed deliverable to a different idle Reviewer lane | done - developer T-0001, merge `8f210bc` |
| M8 Records hygiene | archive merge fields proved or `pending`, Plan lists each milestone once, export names its head | done - ceo T-0028, merge `62ef5db` (P-0027, Reviewer-4); the Plan row below still said `review` and is corrected here |
| M9 Harness^2 adoption | AC-H1..AC-H8 verified on the merged revision | open - every M9 lane is merged and AC-H1..AC-H8 are verified; the exit condition's last clause (`pytest -q` clean on `main`) holds, so the milestone closes when the CEO records it |

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
`main` (`git merge-base --is-ancestor <sha> main` -> rc 0); an open PR is
`review`, a PR sent back for rework is `doing`, and a task the queue records
as `dropped` is listed in the drops table below with its reason.

| id | task | role | prio | deps | artifact | status | evidence |
|---|---|---|---|---|---|---|---|
| T-0001 | Research section 8: verdict table, adoption order, falsifiers, sources | product-manager | P1 | - | `docs/Team/Research.md` 8, `tests/unit/test_research_sources.py` | done | merge `3ce409a` (P-0005); 5 passed @ `eecc406` |
| T-0001 | Freeze the harness-surface and hooks CLI contract; record the decisions | architect | P1 | - | `docs/Team/Architecture.md` 11, `docs/Team/Decisions.md` | done | merge `811065b` (P-0003); the contract landed as Architecture 11.1-11.9 around one `hook_dir(root)` resolver |
| T-0001 | Engine: `harness list`, `harness lint`, `harness budget` + unit tests | developer | P0 | architect:T-0001 | `src/teamwork/harness.py`, `tests/unit/test_harness_surface.py` | done | merge `5dc7f6b` (P-0004); the eight-row registry landed in `aad25f3` |
| T-0002 | Engine: git hooks (in-loop enforcement) + unit tests | developer | P0 | architect:T-0001 | `src/teamwork/hooks.py`, `tests/unit/test_hooks.py` | done | merge `1c99bb1` (P-0007); 30 passed @ `0795f26` |
| T-0001 | Integration + acceptance tests for the harness surface and hooks | tester | P0 | developer:T-0001, developer:T-0002 | `tests/integration/test_harness_cli.py`, `tests/acceptance/test_harness_docs.py` | done | merge `4b3e6dd` (P-0011); the argv-builder defect the first round found was fixed in `5355b0b` |
| T-0001 | Docs: reviewer rubric, untrusted-material rule, SKILL.md and CHANGELOG | ceo | P1 | - | `roles/reviewer.md`, `references/Evidence.md`, `SKILL.md` | done | merge `e82075d` (P-0001), after 2 fail + 1 pass rounds |
| T-0002 | Docs pass for the new surface: cli guide, CHANGELOG, dead-skill trigger line | ceo | P1 | developer:T-0001, developer:T-0002 | `docs/guide/cli.md`, `CHANGELOG.md`, `SKILL.md` | done | merge `915f84f` (P-0008); `hooks` documented at `829bc45`, `harness` documented after the engine merged |

Every M9 row above is `done` and every merge named in the evidence column is an
ancestor of `main` (`git merge-base --is-ancestor <sha> main` -> rc 0 for
`3ce409a`, `811065b`, `5dc7f6b`, `1c99bb1`, `4b3e6dd`, `e82075d`, `915f84f`).
The one M9 task with no merge is the reviewer row, which the queue records as
`dropped`; it is in the drops table below, and the acceptance coverage it
wanted is in place under other ids (TS-0003 integration/harness, TS-0005
acceptance/harness). AC-H1..AC-H8 are verified on the merged revision
(`teamwork.py criteria list` -> 8/8) and `pytest -q` is clean on `main`, so the
milestone's exit condition is met; the milestone itself closes when the CEO
records that, not before.

Three tasks were dropped in this milestone. They are the M9 drops; the live
queues also carry CEO and Security Auditor drops from the privacy and audit
work, which is outside this milestone's scope and is listed in the table below.

| id | task | role | why dropped |
|---|---|---|---|
| T-0003 | Three measured defects on the harness/hooks branches (list shape, hook marker, root-commit hole) | developer | covered by the fixes it named: the eight-row list landed in developer T-0001 `aad25f3`, the marker literal and root-commit refusal in developer T-0002 `0795f26` |
| T-0002 | Architecture 11.2/11.6 drifted from the two branches in four measured ways | architect | superseded: reconciled inside architect T-0001's review rework `f476b82` as amendments A1-A3 and rulings R1-R6 (D-20261020-Architect-8, -9) |
| T-0001 | Run the acceptance record TS-0004 for area harness | reviewer | a queue-hygiene chore, not a deliverable: the mis-filed duplicate was resolved by renumbering - TS-0004 is the CEO's goal/milestone record, and the acceptance layer for area harness is TS-0005, owned and run by the Reviewer role, with TS-0003 (integration/harness) covering the process boundary. Its branch carried the D-0003 ruling, which moved to reviewer T-0002 and merged as `6a35198` (P-0026); the branch itself is superseded and is not merged |

Landed in the same window, outside this milestone's scope:

| id | task | role | status | evidence |
|---|---|---|---|---|
| T-0002 | Fix the hardcoded POSIX `PATH` in `tests/unit/test_skill_refresh.py` | tester | done | merge `fdc75d1` (P-0002) |
| T-0003 | Make the traceability record-resolution guard honest about an empty team tree | tester | done | merge `9a333fe` (P-0006); it is why product-manager T-0002 exists |
| T-0003 | RED gate: the privacy scan fails at HEAD on a forge squash merge | ceo | blocked | needs the user's authorization for a history rewrite; see [Board](Board.md) |
| T-0004 | AC-5's claimed green is false on `main` | ceo | dropped | superseded by ceo T-0005, which corrected the claim in the records; see [Board](Board.md) |
| T-0006 | The privacy red is local: the published history is clean | ceo | dropped | the answer it produced is recorded in [Risks](Risks.md) R-16 and in the T-0003 record |
| T-0007 | Fix the archive mask so it covers every rule the shipped gate reports | ceo | dropped | done on the developer lane as developer T-0007, merge `bd59121` (P-0014) |
| T-0005 | Records truth: AC-5 must not claim green | ceo | done | merge `05a4e4f` (P-0010) |
| T-0008 | Re-review P-0010 after the archive-mask fix | ceo | done | merge `9d96c95` (P-0016) |
| T-0009 | Export the audit manifest for the M9 milestone | ceo | done | merge `4078296` (P-0019) |
| T-0010 | Ledger export writes to the project root even inside a lane worktree | ceo | done | closed on the developer lane's reviewed work: merge `f3e8d31` (P-0018) |
| T-0011 | The published branch carries a committer guard the local main lacks | ceo | done | the measurement and the decision are committed in [Decisions](Decisions.md) as D-20261020-CEO-8 (merge `3dbd3ad`, P-0021); the queue records the task `done` with a passed review. The rewrite it gates is still the user's to authorize; see [Board](Board.md) |
| T-0004 | Design, declare and run the unit-layer test record for every area | developer | done | merge `b48015e` (P-0012) |
| T-0005 | Global memory entries must carry provenance, and a merge must never drop it | developer | done | merge `4552e07` (P-0013) |
| T-0006 | The privacy gate false-positives on a relative path | developer | done | merge `f9ce145` (P-0015) |
| T-0008 | Ledger export must act on the work tree the command runs in | developer | done | merge `f3e8d31` (P-0018) |
| T-0003 | Write the committed record of the privacy-audit answer | product-manager | done | merge `36f268d` (P-0017) |
| T-0001 | The audit report's conclusion is stale | security-auditor | dropped | superseded by security-auditor T-0002, which re-stated the report under the D-0003 ruling; merge `4d39f20` (P-0024) |
| T-0003 | The merged commit message of P-0024 carries a 40-hex tree id | security-auditor | dropped | the rule it produced is committed in [Decisions](Decisions.md) as D-20261021-CEO-1 (merge `57a71c8`, P-0027) |
| T-0002 | Re-state the Audit Report's disclosure claim | security-auditor | done | merge `4d39f20` (P-0024) |
| T-0009 | The dispute panel is computed at role level, so the neutral seat is locked out of a dispute between two instances of one role | developer | done | merge `4fdb2c4` (P-0025) |
| T-0002 | Carry the D-0003 tribunal ruling into the committed decision record | reviewer | done | merge `6a35198` (P-0026) |

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
