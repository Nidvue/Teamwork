# PLAN - milestones and task graph

Owner: Project Manager. One row per task; `deps` must be `done` before it runs.
Priority: P0 code, P1 tests, P2 docs.

Related: [Project](Project.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md) · [pi packaging](Pi-Packaging.md)

## Status summary

The state of every row below is read from the tool, never from this file:
`teamwork.py board` for the per-role state and `teamwork.py task list <role>`
for one task. This file carries the exit condition, which does not move.

| milestone | exit condition | state |
|---|---|---|
| M0 Audit follow-up | `loop` STOP + `audit` 0 problems | done - T-0001..T-0007 |
| M1 Package the engine | `selftest` + installed wheel `--version` | done |
| M2 Make it attractive | README demo, strict docs site, 0 broken links | done |
| M3 Independent verification | every deliverable has a Reviewer verdict | done |
| M4 Publish | `v1.0.0` release with wheel, sdist, `SHA256SUMS`, SBOM | done - now at `v1.0.2` |
| M5 Post-1.0 hardening | typed module split, Windows-green matrix, dependency upkeep | done - T-0010..T-0016, closing T-0017 |
| M6 Evidence packets + repro gate | hashed evidence artifacts, repro-first bug gate, Reviewer verdicts | done - T-0020..T-0025 |
| M7 Reviewer fan-out + claims | `pulse` gives every deliverable to a different idle Reviewer lane | done |
| M8 Records hygiene | archive merge fields carry a proved revision, each milestone listed once | done |
| M9 Release truth | every published version is traceable to a tag or a measured exception, and every release claim is measurable | in progress (state read with `teamwork.py board`) |

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
| T-0028 | Repair archive merge fields, de-duplicate Plan, re-pin manifest | ceo | P1 | `Archive.md`, `Plan.md`, `AuditManifest.json` | review | 20 of 37 merge fields proved from `pr.merge` records or merge subjects |

## M9 - release truth (in progress)

Goal: the published state and the repository must agree, and every release claim
in the documentation must be measurable by a command.

M9 exists because they disagreed: the npm `latest` release shipped an engine
behind `main`, its CI run was red, no git tag covered the published versions,
the docs advertised an install channel that does not exist, and the release
record named a tag that never existed and a coverage threshold an order of
magnitude off. The milestone replaces those claims with a frozen contract, a
gate that reads the published facts, and records that admit only what is
measured.

Non-goals:

- publishing the package to a new distribution channel; the channel that does
  not resolve stays marked unavailable
- re-publishing a version that was already published
- rewriting published history; the npm-only 1.1.1 anomaly is recorded as an
  exception, not repaired
- changing the semantics of the nine rules; the contract is amended only by
  measurement (see [Decisions](Decisions.md) D-20261020-CEO-7)

### M9 deliverables

| id | task | role | area | artifact |
|---|---|---|---|---|
| T-0002 | freeze the release-consistency contract | architect | architecture | `docs/Team/Architecture.md` section 11 |
| T-0003 | correct the contract defects found while implementing section 11 | architect | architecture | `docs/Team/Architecture.md` section 11 |
| T-0004 | amend the frozen contract (rev, link policy, R2 decision record) | architect | architecture | `docs/Team/Architecture.md` section 11, [Decisions](Decisions.md) |
| T-0005 | rewrite the CI-scope description to match the delivered workflow | architect | ci | `docs/Team/Architecture.md` section 9 |
| T-0005 | the release-consistency checker, nine rules | developer | release | `scripts/check_release_consistency.py`, `release-exceptions.json` |
| T-0006 | unit tests, one per rule | developer | release | `tests/unit/test_release_consistency.py` |
| T-0007 | the local gate target | developer | makefile | `Makefile` |
| T-0009 | the R3 exception admission test | developer | release-consistency | `tests/unit/test_release_consistency.py` |
| T-0010 | the R8 warning-row exemption | developer | release | `scripts/check_release_consistency.py`, `tests/unit/test_release_consistency_r8.py` |
| T-0011 | the CI path-filter contract tests | developer | ci-contracts | `tests/unit/test_skill_contracts.py` |
| T-0012 | the GitHub API token in the checker | developer | release-consistency | `scripts/check_release_consistency.py` |
| T-0013 | the R9 denial-line exemptions | developer | release-consistency | `tests/unit/test_release_consistency.py` |
| T-0003 | wire the gate into CI | release-engineer | ci | `.github/workflows/ci.yml` |
| T-0004 | push the merged revision and certify CI | release-engineer | release | `.github/workflows/ci.yml`, `.github/workflows/release.yml` |
| T-0005 | repair the release record | release-engineer | release | `docs/Team/Release.md` |
| T-0007 | the full tag set and the online half in the release workflow | release-engineer | release | `.github/workflows/release.yml` |
| T-0008 | the scope classifier and a rename out of a shipping path | release-engineer | ci | `.github/workflows/ci.yml` |
| T-0059 | bump the version and record the npm-only anomaly | ceo | release | `src/teamwork/version.py`, `CHANGELOG.md` |
| T-0060 | tag the published version and publish its release | ceo | release | the git tag and its GitHub Release |
| T-0061 | repair the install and version claims | ceo | release | `README.md`, `docs/guide/install.md` |
| T-0062 | open the milestone: criteria, task graph, decisions | ceo | release | [Decisions](Decisions.md), the criteria records |
| T-0063 | sequence the required check | ceo | release | `.github/workflows/ci.yml`, the branch protection |
| T-0064 | the version claim in the architecture guide | ceo | docs | `docs/guide/architecture.md` |
| T-0002 | independent verification of the published-version traceability | reviewer | release | the acceptance-layer test record |
| T-0003 | acceptance proof that the release claims hold | tester | release | `tests/acceptance/test_release_claims.py` |
| T-0002 | record M9 on the plan and the board | project-manager | plan | this file, [Board](Board.md) |

Task ids are allocated per role queue, so the same id under two roles is two
tasks, not a duplicate; the role column is the qualifier. The state of every
row is read with `teamwork.py task list <role>`, and the merged revision of
every landed row is read with `teamwork.py pr list`.

### M9 dependencies

The order is fixed; each step consumes the frozen one before it.

```text
contract freeze -> checker -> unit tests -> CI wiring -> release
```

| step | consumes | why it cannot run earlier |
|---|---|---|
| contract freeze | - | the rules, the payload digest and the exception format must be written before code can be measured against them |
| checker | the frozen contract | an unimplementable contract is corrected by measurement, not defended |
| unit tests | the frozen contract and the checker | each test proves one rule and must fail before the implementation and pass after it |
| CI wiring | the checker | the gate must fail closed on the exit codes, so the checker is needed first |
| release | the gate, the tag and the repaired claims | nothing is published or pushed before the gate is green and the required check is sequenced |

### M9 acceptance criteria

The criteria are machine records (`teamwork.py criteria list`); each row below
states the verifiable claim and the command that produces its evidence.

| id | verifiable claim | evidence command | owner |
|---|---|---|---|
| AC-REL-1 | every version published to npm or to GitHub Releases is traceable to a git tag at a commit whose bundled payload matches, or is listed in `release-exceptions.json` with a measured reason | `python3 scripts/check_release_consistency.py --online` (R3), `git tag -l`, `cat release-exceptions.json` | ceo |
| AC-REL-2 | the checker implements R1-R9, exits 0 clean, 1 on drift and 2 on unreadable input, and every rule has a unit test that fails before the implementation and passes after it | `python3 scripts/check_release_consistency.py --offline` and its exit codes, `python3 -m pytest tests/unit/test_release_consistency.py tests/unit/test_release_consistency_digest.py tests/unit/test_release_consistency_r8.py -q` | developer |
| AC-REL-3 | the git tag for the published npm version points at the commit that version was published from, and its GitHub Release carries the wheel, the sdist, `SHA256SUMS` and both SBOMs | `git rev-list -n1 v1.1.2`, `gh release view v1.1.2 --json assets` | release-engineer |
| AC-REL-4 | `README.md`, `docs/guide/install.md` and `docs/Team/Release.md` print no install command that cannot work, no version older than `src/teamwork/version.py` and no tag that does not exist | `python3 scripts/check_release_consistency.py --online` (R6, R8, R9), `python3 -m pytest tests/acceptance/test_release_claims.py -q` | ceo |
| AC-REL-5 | the version on `main` is strictly greater than every published and tagged version, and `CHANGELOG.md` records the npm-only 1.1.1 anomaly with its reason | `grep __version__ src/teamwork/version.py`, `git tag -l`, `npm view @nidvue/teamwork versions`, `grep -n '^## ' CHANGELOG.md` | ceo |
| AC-REL-6 | CI runs the release-consistency gate, every workflow is green on the pushed revision, and the installed skill mirrors it | `gh run list --workflow=ci.yml --commit <pushed sha>`, `python3 scripts/teamwork.py refresh --check` | release-engineer |

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
