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
| M4 Publish | `v1.0.0` release with wheel, sdist, `SHA256SUMS`, SBOM | done - the release line has since advanced; newest tag is read with `git tag -l --sort=-v:refname \| head -1` |
| M5 Post-1.0 hardening | typed module split, Windows-green matrix, dependency upkeep | done - T-0010..T-0016, closing T-0017 |
| M6 Evidence packets + repro gate | hashed evidence artifacts, repro-first bug gate, Reviewer verdicts | done - T-0020..T-0025 |
| M7 Reviewer fan-out + claims | `pulse` gives every deliverable to a different idle Reviewer lane | done |
| M8 Records hygiene | archive merge fields carry a proved revision, each milestone listed once | done |
| M9 Release truth | every published version is traceable to a tag or a measured exception, and every release claim is measurable | done - AC-REL-1..AC-REL-6 measured green, including CI on the pushed revision |
| M9p Harness^2 adoption | `harness` and `hooks` registered and documented, AC-H1..AC-H8 verified on the merged revision | closed on the published line; its records are kept below under M9p because the reconciled history carries two milestones that were both named M9 |
| M10 Release truth on every OS | the CI matrix is green on all three operating systems, not only ubuntu and macOS | done - T-0022..T-0024; CI run 39690418108 on the pushed revision, 19/19 jobs |
| M11 Solid review pass | suite green on a stock Windows host, docs re-measured, tree censused and cleaned, `loop` STOP + `audit` 0 problems | in progress - see the M11 section below |
| M12 Release parity: GitHub, npm, Pages | AC-22 and AC-23 verified by a role other than the author on the merged revision, and the two release defects named at intake (release-engineer T-0011, T-0012) closed | in progress - see the M12 section below; the live state of every row is read with `teamwork.py board` |

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
| T-0028 | Repair archive merge fields, de-duplicate Plan, re-pin manifest | ceo | P1 | `Archive.md`, `Plan.md`, `AuditManifest.json` | done | merge `62ef5db`; 20 of 37 merge fields proved from `pr.merge` records or merge subjects |

## M9 - release truth (closed)

Goal: the published state and the repository must agree, and every release claim
in the documentation must be measurable by a command.

M9 existed because they disagreed: the npm `latest` release shipped an engine
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
| T-0014 | keep `scripts/` off `sys.path` after the skill-sync import | developer | - | `tests/unit/test_skill_sync.py` |
| T-0015 | unit-layer records for the six uncovered areas | developer | - | the unit test records |
| T-0016 | R3 ignores a published non-X.Y.Z npm version | developer | - | `scripts/check_release_consistency.py` |
| T-0017 | the install docs pin a superseded wheel URL | developer | - | `docs/guide/install.md` |
| T-0018 | the traceability unit test re-declared the version shape | developer | - | `tests/unit/test_release_traceability.py` |
| T-0019 | the tag pin `refresh --branch vX.Y.Z` cannot resolve | developer | - | `src/teamwork/engine.py`, `docs/guide/install.md` |
| T-0020 | R6 cannot see a stale version in a `--branch`/`--tag` pin | developer | - | `scripts/check_release_consistency.py` |
| T-0003 | wire the gate into CI | release-engineer | ci | `.github/workflows/ci.yml` |
| T-0004 | push the merged revision and certify CI | release-engineer | release | `.github/workflows/ci.yml`, `.github/workflows/release.yml` |
| T-0005 | repair the release record | release-engineer | release | `docs/Team/Release.md` |
| T-0006 | audit every commit identity on a rewritten-history push | release-engineer | - | `.github/workflows/` |
| T-0010 | the identity gate must not audit all history on a rewritten-history push | release-engineer | - | `src/teamwork/engine.py`, `tests/unit/test_commit_identity.py` |
| T-0007 | the full tag set and the online half in the release workflow | release-engineer | release | `.github/workflows/release.yml` |
| T-0008 | the scope classifier and a rename out of a shipping path | release-engineer | ci | `.github/workflows/ci.yml` |
| T-0009 | the release prose must state what the tree contains | release-engineer | - | `docs/Team/Release.md` |
| T-0059 | bump the version and record the npm-only anomaly | ceo | release | `src/teamwork/version.py`, `CHANGELOG.md` |
| T-0060 | tag the published version and publish its release | ceo | release | the git tag and its GitHub Release |
| T-0061 | repair the install and version claims | ceo | release | `README.md`, `docs/guide/install.md` |
| T-0062 | open the milestone: criteria, task graph, decisions | ceo | release | [Decisions](Decisions.md), the criteria records |
| T-0063 | sequence the required check | ceo | release | `.github/workflows/ci.yml`, the branch protection |
| T-0064 | the version claim in the architecture guide | ceo | docs | `docs/guide/architecture.md` |
| T-0065 | reconcile the published line with the local release-traceability line | ceo | - | the merged line, `docs/Team/Archive.md` |
| T-0066 | `links` measured the main checkout from inside a worktree | ceo | links | `src/teamwork/engine.py` |
| T-0067 | `audit` asked which field the proof was written in | ceo | - | `src/teamwork/engine.py`, `tests/unit/test_audit_evidence_sources.py` |
| T-0070 | `audit` link health used the main checkout too | ceo | links | `src/teamwork/engine.py`, `tests/unit/test_integrity_fixes.py` |
| T-0002 | independent verification of the published-version traceability | reviewer | release | the acceptance-layer test record |
| T-0004 | acceptance-layer records for the links area | reviewer | - | `tests/acceptance/test_acceptance_links.py` |
| T-0003 | acceptance-layer records for the five uncovered areas | reviewer | - | the acceptance test records |
| T-0005 | fix the env-secret rule that reports a function call as a credential | security-auditor | privacy | `scripts/privacy_scan.py`, `tests/unit/test_privacy_scan.py` |
| T-0003 | acceptance proof that the release claims hold | tester | release | the acceptance proof, held on the unmerged P-0087 branch |
| T-0004 | integration-layer records for the six uncovered areas | tester | - | the integration test records |
| T-0005 | integration-layer records for the links area | tester | - | `tests/integration/test_links_flow.py` |
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
| AC-REL-4 | `README.md`, `docs/guide/install.md` and `docs/Team/Release.md` print no install command that cannot work, no version older than `src/teamwork/version.py` and no tag that does not exist | `python3 scripts/check_release_consistency.py --offline` (R6, R9), `python3 scripts/check_release_consistency.py --online` (R8), `python3 -m pytest -q tests/unit/test_release_consistency.py tests/unit/test_release_consistency_r8.py` | ceo |
| AC-REL-5 | the version on `main` is strictly greater than every published and tagged version, and `CHANGELOG.md` records the npm-only 1.1.1 anomaly with its reason | `grep __version__ src/teamwork/version.py`, `git tag -l`, `npm view @nidvue/teamwork versions`, `grep -n '^## ' CHANGELOG.md` | ceo |
| AC-REL-6 | CI runs the release-consistency gate, every workflow is green on the pushed revision, and the installed skill mirrors it | `gh run list --workflow=ci.yml --commit <pushed sha>`, `python3 scripts/teamwork.py refresh --check` | release-engineer |

## Harness^2 adoption (M9 on the published line, closed)

Exit: AC-H1..AC-H8 in `Criteria.md` verified on the merged revision - `harness`
and `hooks` registered and documented, the ordered review rubric and the
untrusted-material rule stated where agents read them, and `pytest -q` clean on
`main`. Source: [Research](Research.md) 8, whose adoption order is H10+H5+H2,
then H1+H3+H8, then H4, then the doctrine rows H6/H7/H9.

The intake brief numbers this milestone M8. The M8 above is the records-hygiene
milestone and its own exit condition requires each milestone to be listed once,
so the Harness^2 adoption was M9 on the published line. The reconciled history
carries both milestones, so it is recorded here as **M9p** to keep the two apart
([D-20261021-CEO-4](Decisions.md)). A row is `done` only when its merge is on
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

Every M9p row above is `done` and every merge named in the evidence column is an
ancestor of `main` (`git merge-base --is-ancestor <sha> main` -> rc 0 for
`3ce409a`, `811065b`, `5dc7f6b`, `1c99bb1`, `4b3e6dd`, `e82075d`, `915f84f`).
The one M9p task with no merge is the reviewer row, which the queue records as
`dropped`; it is in the drops table below, and the acceptance coverage it
wanted is in place under other ids (TS-0003 integration/harness, TS-0005
acceptance/harness). AC-H1..AC-H8 are verified on the merged revision
(`teamwork.py criteria list` -> 8/8) and `pytest -q` is clean on `main`, so the
milestone's exit condition is met and it reads `closed` above. The rows stay
because the merges they name are the proof that the reconciled line carries the
harness surface at all - `src/teamwork/harness.py` and `hooks.py` are on `main`
only through this line.

Three tasks were dropped in this milestone. They are the M9p drops; the live
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

## M11 - solid review and tree truth (live)

Exit: every tracked file carries a verdict and the search that produced it, no
file is left unreferenced or duplicated without a written justification, the
board and the M11 table below are rendered from the role queues rather than from
a hand-written snapshot, and the M11 acceptance criteria are verified on the
merged revision (`teamwork.py criteria list`). Source: the CEO's M11 intake
(ceo T-0001).

### M11 deliverables

Rendered from `Roles/*/TaskQueue.md`. The queue is the authority for a state, so
read any row again with `teamwork.py task list <role>`.

| role | id | task | prio | area | state | claimed by | pr | merged |
|---|---|---|---|---|---|---|---|---|
| ceo | T-0001 | Own M11: intake, criteria, goal-layer tests, arbitration, close-out (manifest + final report) | P0 | intake | doing | CEO | - | - |
| ceo | T-0007 | Record the M11 solid-review engagement intake (objective, criteria, milestone, decision) | P0 | - | review | CEO | P-0002 | - |
| ceo | T-0002 | Register the two include: matrix lanes as required checks (py3.10, py3.12 run but do not block) | P1 | - | todo | - | - | - |
| ceo | T-0003 | Protect the v* tag pattern (no ruleset, no tag protection rule today) | P1 | - | todo | - | - | - |
| ceo | T-0004 | Clear the R8 drift at docs/Team/Decisions.md:1284 - it blocks the online release gate, so no tag can be released | P1 | - | todo | - | - | - |
| ceo | T-0005 | Decide required_linear_history on main (off; policy says no merge commits on the default branch) | P2 | - | todo | - | - | - |
| ceo | T-0006 | Make CodeQL a merge gate, and either enforce SHA pinning on actions or record why not | P2 | - | todo | - | - | - |
| ceo | T-0008 | Remove the two stale tier-init instance dirs .pi/Teamwork/Teams/Teamwork/Agents/Developer and Agents/Tester | P2 | - | todo | - | - | - |
| architect | T-0001 | Code and logic review of src/teamwork and scripts: find real defects, dead code, inconsistent invariants; file each finding as a task and record contract changes in Architecture.md | P0 | - | doing | Architect | - | - |
| developer | T-0001 | Fix resources.self_invocation(): the returned command is unusable on Windows when a path has a space or backslash | P0 | - | review | Developer-1 | P-0001 | - |
| developer | T-0002 | Guard every symlink-dependent test so the suite is green on a host without symlink privilege | P0 | - | doing | Developer-1 | - | - |
| developer | T-0003 | Make every test that needs an external tool honest: skip with a stated reason when the tool is absent | P0 | test-portability | review | Developer-2 | P-0004 | - |
| developer | T-0004 | Remove the personal absolute path from commit a4c726f (message + resources.py docstrings) before it can merge | P0 | - | todo | - | - | - |
| developer | T-0005 | Reword the developer-1 T-0001 commit message: it carries the operator home path and turns the privacy gate red | P0 | - | todo | - | - | - |
| developer | T-0006 | Re-point the board gate at the live milestone: tests/unit/test_board_matches_tool.py cannot see the M11 queues | P1 | - | todo | - | - | - |
| tester | T-0001 | Certify the suite locally on this host and in CI on the pushed revision; own integration-layer records for portability and ci-release | P0 | - | doing | Tester-1 | - | - |
| reviewer | T-0001 | Serve the review queue and own the acceptance layer for the M11 deliverables | P0 | - | todo | - | - | - |
| reviewer | T-0002 | Second review seat: fan out the review queue, merge on pass, and cover the acceptance layer independently | P0 | - | todo | - | - | - |
| product-manager | T-0001 | Rebuild the traceability matrix for AC-19..AC-21 and re-key the machine criteria store (gap G-1) | P1 | - | doing | ProductManager | - | - |
| project-manager | T-0001 | Tree census: classify every tracked file as live, superseded, duplicate or unreferenced; delete or justify each hit | P0 | plan | review | ProjectManager | - | - |
| release-engineer | T-0001 | Workflow and release-gate integrity: workflows match the tree, hooks install, branch protection matches policy | P0 | ci | review | ReleaseEngineer | P-0003 | - |
| release-engineer | T-0002 | Pin the lint job's ruff to the project pin instead of installing the newest release | P1 | - | todo | - | - | - |
| release-engineer | T-0003 | ci.yml skips the privacy job (and every code job) on a prose-only push to main | P2 | - | todo | - | - | - |
| release-engineer | T-0004 | privacy-allow.txt: correct the exemption-mechanism sentence and record that the file is self-exempting | P3 | - | todo | - | - | - |
| security-auditor | T-0001 | Security and privacy posture audit: tree, history, workflows, hooks, scanning alerts | P0 | - | doing | SecurityAuditor | - | - |
| technical-writer | T-0001 | Docs truth pass: remove every stale or self-contradicting state claim in docs/Team, README, CHANGELOG and docs/guide | P0 | - | doing | TechnicalWriter | - | - |

### M11 tree census - project-manager T-0001

214 tracked files, each classified by a measurement rather than by inspection.
The evidence cell quotes the search that produced the verdict, so every row can
be re-run:

| measurement | command | result |
|---|---|---|
| tracked files | `git ls-files \| wc -l` | 214 |
| references to a path, then to its basename | `git grep -l -F -- <path>` / `git grep -l -F -- <name>` | the evidence cell of every row below |
| test modules pytest collects | `python -m pytest --collect-only -q` | 1256 tests in 83 modules |
| byte-identical duplicates | `git ls-files -z \| xargs -0 md5sum \| sort \| uniq -d -w32` | 0 |
| build and bundle consumers | `pyproject.toml`, `bundle.BUNDLE_FILES`/`BUNDLE_TREES`, `build_pi_package.py`, `verify_release.py` | the `roles/`, `references/`, `templates/`, `SKILL.md` and `AGENTS.md` rows |
| deletions the census proved | `git status --short` after the pass | 0 |

Counts: **206 live, 2 superseded in part and kept as records, 0 duplicate, 6
unreferenced in-tree and kept with a written reason, 0 deleted.**

#### Census

`live` means something in the tree reads the file: code, a test, a build
manifest, a bundle list, the site nav or a document that links it. `evidence`
names that consumer; a bare count is the number of files naming the path.

| path | verdict | evidence | action |
|---|---|---|---|
| `.agents/skills/ceo-audit-close/SKILL.md` | live | project skill: `grep -l ceo-audit-close` -> 9 file(s); `grep -l .agents/skills/ceo-audit-close/SKILL.md` -> 4 (Archive.md, Plan.md, test_harness_cli.py, +1) | kept |
| `.agents/skills/product-manager-records/SKILL.md` | live | project skill: `grep -l product-manager-records` -> 2 file(s); `grep -l .agents/skills/product-manager-records/SKILL.md` -> 1 (Archive.md) | kept |
| `.editorconfig` | live | `pyproject.toml` sdist list; editor convention; `grep -l .editorconfig` -> 4 (Architecture.md, Archive.md, pyproject.toml, +1) | kept |
| `.gitattributes` | live | `grep -l .gitattributes` -> 17 (AGENTS.md, Architecture.md, Archive.md, +14) | kept |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | unreferenced in-tree | GitHub reads `.github/ISSUE_TEMPLATE/*.yml` by path; in-tree hits 0 | kept, justified - the repo's issue form; no in-tree gate replaces it |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | unreferenced in-tree | GitHub reads `.github/ISSUE_TEMPLATE/*.yml` by path; in-tree hits 0 | kept, justified - same reason as the bug form |
| `.github/PULL_REQUEST_TEMPLATE.md` | unreferenced in-tree | GitHub reads `.github/PULL_REQUEST_TEMPLATE.md` by path; in-tree hits 0 | kept, justified - the contributor's checklist; deleting removes a control |
| `.github/dependabot.yml` | live | forge dependency updates; `test_code_scanning.py` pins its shape; `grep -l .github/dependabot.yml` -> 1 (test_code_scanning.py) | kept |
| `.github/privacy-allow.txt` | live | `Makefile` and both workflows pass it to the privacy scan; `grep -l .github/privacy-allow.txt` -> 17 (ci.yml, docs.yml, Makefile, +14) | kept |
| `.github/workflows/ci.yml` | live | `grep -l .github/workflows/ci.yml` -> 15 (Architecture.md, Archive.md, Decisions.md, +12) | kept |
| `.github/workflows/docs.yml` | live | `grep -l .github/workflows/docs.yml` -> 7 (ci.yml, Architecture.md, Archive.md, +4) | kept |
| `.github/workflows/release.yml` | live | `grep -l .github/workflows/release.yml` -> 12 (ci.yml, Architecture.md, Archive.md, +9) | kept |
| `.gitignore` | live | `grep -l .gitignore` -> 14 (CHANGELOG.md, SKILL.md, Archive.md, +11) | kept |
| `AGENTS.md` | live | the managed team block; `bundle.BUNDLE_FILES`; `grep -l AGENTS.md` -> 49 (SKILL.md, SKILL.md, docs.yml, +46) | kept |
| `CHANGELOG.md` | live | the release history every release rule reads; `grep -l CHANGELOG.md` -> 28 (ci.yml, docs.yml, release.yml, +25) | kept |
| `CITATION.cff` | live | citation metadata; in the sdist file list; `grep -l CITATION.cff` -> 14 (docs.yml, CHANGELOG.md, Architecture.md, +11) | kept |
| `CODE_OF_CONDUCT.md` | live | `docs.yml` paths; linked from README/CONTRIBUTING; `grep -l CODE_OF_CONDUCT.md` -> 12 (docs.yml, CHANGELOG.md, CONTRIBUTING.md, +9) | kept |
| `CONTRIBUTING.md` | live | `docs.yml` paths; linked from README/SECURITY; `grep -l CONTRIBUTING.md` -> 17 (docs.yml, CHANGELOG.md, CODE_OF_CONDUCT.md, +14) | kept |
| `LICENSE` | live | `pyproject.toml` license file; `NOTICE` references it; `grep -l LICENSE` -> 20 (ci.yml, docs.yml, NOTICE, +17) | kept |
| `Makefile` | live | the documented one-shot gate (`make ci`); `grep -l Makefile` -> 17 (.editorconfig, AGENTS.md, Architecture.md, +14) | kept |
| `NOTICE` | live | `build_pi_package.py` ships it in the npm package; `grep -l NOTICE` -> 10 (CHANGELOG.md, README.md, Architecture.md, +7) | kept |
| `README.md` | live | `pyproject.toml` readme; site and forge entry page; `grep -l README.md` -> 41 (ci.yml, docs.yml, CHANGELOG.md, +38) | kept |
| `SECURITY.md` | live | `docs.yml` paths; linked from README/CONTRIBUTING; `grep -l SECURITY.md` -> 16 (docs.yml, CHANGELOG.md, CODE_OF_CONDUCT.md, +13) | kept |
| `SKILL.md` | live | `bundle.BUNDLE_FILES`; the protocol every role reads; `grep -l SKILL.md` -> 57 (AGENTS.md, CHANGELOG.md, README.md, +54) | kept |
| `assets/banner.svg` | live | README hero `<img src=...>` (README.md:2); `grep -l assets/banner.svg` -> 2 (README.md, Design.md) | kept |
| `assets/demo.svg` | live | README demo `<img src=...>` (README.md:19); `grep -l assets/demo.svg` -> 7 (README.md, Archive.md, Design.md, +4) | kept |
| `assets/logo.svg` | live | Design IMG-3; pinned by `test_skill_contracts.py:248`; `grep -l assets/logo.svg` -> 3 (Archive.md, Design.md, test_skill_contracts.py) | kept |
| `assets/social-preview.png` | live | Design IMG-1; `.gitattributes:82` opt-out; forge social preview; `grep -l assets/social-preview.png` -> 6 (.gitattributes, Archive.md, Decisions.md, +3) | kept |
| `docs/CNAME` | unreferenced in-tree | in-tree hits 0; content `teamwork.nidvue.com` == `CHANGELOG.md:427` | kept, justified - a published site claim, not a dead file |
| `docs/Team/Architecture.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Architecture.md` -> 30 (PULL_REQUEST_TEMPLATE.md, dependabot.yml, ci.yml, +27) | kept |
| `docs/Team/Archive.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Archive.md` -> 33 (SKILL.md, privacy-allow.txt, AGENTS.md, +30) | kept |
| `docs/Team/AuditManifest.json` | live | generated by `ledger export` (`config.F_MANIFEST`); `grep -l docs/Team/AuditManifest.json` -> 12 (SKILL.md, SKILL.md, Archive.md, +9) | kept |
| `docs/Team/AuditManifest.md` | live | generated by `ledger export` (`config.F_AUDITREPORT`); `grep -l docs/Team/AuditManifest.md` -> 3 (Archive.md, test_acceptance_docs.py, test_docs_contracts.py) | kept |
| `docs/Team/AuditReport.md` | superseded in part (record) | header `Superseded in part - read this first`; 8 files name it (Architecture, Risks, decisions) | kept, justified - dated audit measurement and evidence record |
| `docs/Team/Board.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Board.md` -> 7 (SKILL.md, Architecture.md, Archive.md, +4) | kept |
| `docs/Team/Costs.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Costs.md` -> 2 (Architecture.md, test_portability.py) | kept |
| `docs/Team/Decisions.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Decisions.md` -> 21 (SKILL.md, PULL_REQUEST_TEMPLATE.md, privacy-allow.txt, +18) | kept |
| `docs/Team/Design.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Design.md` -> 8 (README.md, SKILL.md, Architecture.md, +5) | kept |
| `docs/Team/M9Acceptance.md` | superseded in part (record) | header `Historical measurement - superseded on AC-REL-6`; linked from `Project.md:6`, `Decisions.md:1268` | kept, justified - evidence record; D-20261022-CEO-5 keeps its body |
| `docs/Team/Pi-Packaging.md` | live | linked from Plan/Board/Architecture/Release; `test_docs_contracts.py:323` names it; `grep -l docs/Team/Pi-Packaging.md` -> 3 (Architecture.md, Archive.md, test_docs_contracts.py) | kept |
| `docs/Team/Plan.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Plan.md` -> 8 (SKILL.md, Architecture.md, Archive.md, +5) | kept |
| `docs/Team/Project.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Project.md` -> 15 (ci.yml, docs.yml, release.yml, +12) | kept |
| `docs/Team/Release.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Release.md` -> 14 (ci.yml, CHANGELOG.md, Architecture.md, +11) | kept |
| `docs/Team/Research.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Research.md` -> 6 (CHANGELOG.md, Architecture.md, Archive.md, +3) | kept |
| `docs/Team/Risks.md` | live | `config.DOCS` team document, one owner and one path; `grep -l docs/Team/Risks.md` -> 6 (SKILL.md, Architecture.md, Archive.md, +3) | kept |
| `docs/assets/nidvue-apple-touch-icon.png` | unreferenced in-tree | only `docs/Team/Archive.md` names it; NOTICE covers `docs/assets/nidvue-*` | kept, justified - NOTICE claim; deletion touches a trademark record |
| `docs/assets/nidvue-favicon.ico` | unreferenced in-tree | only `docs/Team/Archive.md` names it; NOTICE covers `docs/assets/nidvue-*` | kept, justified - same reason as the touch icon |
| `docs/assets/nidvue-favicon.svg` | live | `mkdocs.yml:31` favicon; `grep -l nidvue-favicon.svg` -> 2 (mkdocs.yml, test_skill_contracts.py) | kept |
| `docs/assets/nidvue-icon.svg` | live | `mkdocs.yml:30` logo; README.md:3; `grep -l docs/assets/nidvue-icon.svg` -> 2 (README.md, test_skill_contracts.py) | kept |
| `docs/guide/architecture.md` | live | `mkdocs.yml` nav; `grep -l docs/guide/architecture.md` -> 6 (Architecture.md, Archive.md, Pi-Packaging.md, +3) | kept |
| `docs/guide/ci.md` | live | `mkdocs.yml` nav; `grep -l docs/guide/ci.md` -> 1 (CONTRIBUTING.md) | kept |
| `docs/guide/cli.md` | live | `mkdocs.yml` nav; `grep -l docs/guide/cli.md` -> 8 (CHANGELOG.md, Archive.md, Decisions.md, +5) | kept |
| `docs/guide/install.md` | live | `mkdocs.yml` nav; `grep -l docs/guide/install.md` -> 13 (CHANGELOG.md, README.md, Architecture.md, +10) | kept |
| `docs/guide/quickstart.md` | live | `mkdocs.yml` nav; `grep -l docs/guide/quickstart.md` -> 5 (README.md, Archive.md, Pi-Packaging.md, +2) | kept |
| `docs/index.md` | live | `mkdocs.yml` nav; `grep -l docs/index.md` -> 10 (Architecture.md, Archive.md, Decisions.md, +7) | kept |
| `docs/requirements.txt` | live | installed by `ci.yml`, `docs.yml`, `mkdocs.yml`; `grep -l docs/requirements.txt` -> 5 (ci.yml, docs.yml, CONTRIBUTING.md, +2) | kept |
| `mkdocs.yml` | live | the site build every docs job runs; `grep -l mkdocs.yml` -> 12 (docs.yml, CHANGELOG.md, Architecture.md, +9) | kept |
| `pyproject.toml` | live | the build, the `teamwork` console script and the tool config; `grep -l pyproject.toml` -> 36 (ci.yml, release.yml, AGENTS.md, +33) | kept |
| `references/Adapters.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Adapters.md` -> 11 (privacy-allow.txt, CHANGELOG.md, README.md, +8) | kept |
| `references/Audit.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Audit.md` -> 2 (SKILL.md, Archive.md) | kept |
| `references/Concurrency.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Concurrency.md` -> 7 (README.md, SKILL.md, Archive.md, +4) | kept |
| `references/Dissent.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Dissent.md` -> 3 (CHANGELOG.md, SKILL.md, Archive.md) | kept |
| `references/Docs.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Docs.md` -> 3 (SKILL.md, Research.md, technical-writer.md) | kept |
| `references/Engineering.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Engineering.md` -> 11 (AGENTS.md, README.md, SKILL.md, +8) | kept |
| `references/Evidence.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Evidence.md` -> 10 (CHANGELOG.md, SKILL.md, Archive.md, +7) | kept |
| `references/Remotes.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Remotes.md` -> 5 (CHANGELOG.md, SKILL.md, Archive.md, +2) | kept |
| `references/Roles.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Roles.md` -> 9 (SKILL.md, Archive.md, Decisions.md, +6) | kept |
| `references/State.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/State.md` -> 1 (SKILL.md) | kept |
| `references/Testing.md` | live | `bundle.BUNDLE_TREES`; linked from `SKILL.md`; `grep -l references/Testing.md` -> 3 (SKILL.md, Archive.md, Project.md) | kept |
| `release-exceptions.json` | live | read by `check_release_consistency.py` R3 (AC-REL-1); `grep -l release-exceptions.json` -> 17 (CHANGELOG.md, Architecture.md, Archive.md, +14) | kept |
| `roles/architect.md` | live | `ROLES_DIR / 'architect.md'` (`engine.py:3893`); `grep -l roles/architect.md` -> 2 (SKILL.md, Archive.md) | kept |
| `roles/ceo.md` | live | `ROLES_DIR / 'ceo.md'` (`engine.py:3893`); `grep -l roles/ceo.md` -> 4 (SKILL.md, Archive.md, Decisions.md, +1) | kept |
| `roles/cfo.md` | live | `ROLES_DIR / 'cfo.md'` (`engine.py:3893`); `grep -l roles/cfo.md` -> 2 (SKILL.md, Archive.md) | kept |
| `roles/coo.md` | live | `ROLES_DIR / 'coo.md'` (`engine.py:3893`); `grep -l roles/coo.md` -> 2 (SKILL.md, Archive.md) | kept |
| `roles/cto.md` | live | `ROLES_DIR / 'cto.md'` (`engine.py:3893`); `grep -l roles/cto.md` -> 2 (SKILL.md, Archive.md) | kept |
| `roles/data-engineer.md` | live | `ROLES_DIR / 'data-engineer.md'` (`engine.py:3893`); `grep -l roles/data-engineer.md` -> 1 (SKILL.md) | kept |
| `roles/designer.md` | live | `ROLES_DIR / 'designer.md'` (`engine.py:3893`); `grep -l roles/designer.md` -> 9 (SKILL.md, Decisions.md, Design.md, +6) | kept |
| `roles/developer.md` | live | `ROLES_DIR / 'developer.md'` (`engine.py:3893`); `grep -l roles/developer.md` -> 5 (SKILL.md, Archive.md, Decisions.md, +2) | kept |
| `roles/product-manager.md` | live | `ROLES_DIR / 'product-manager.md'` (`engine.py:3893`); `grep -l roles/product-manager.md` -> 2 (SKILL.md, Archive.md) | kept |
| `roles/project-manager.md` | live | `ROLES_DIR / 'project-manager.md'` (`engine.py:3893`); `grep -l roles/project-manager.md` -> 1 (SKILL.md) | kept |
| `roles/release-engineer.md` | live | `ROLES_DIR / 'release-engineer.md'` (`engine.py:3893`); `grep -l roles/release-engineer.md` -> 4 (SKILL.md, Archive.md, Decisions.md, +1) | kept |
| `roles/reviewer.md` | live | `ROLES_DIR / 'reviewer.md'` (`engine.py:3893`); `grep -l roles/reviewer.md` -> 7 (CHANGELOG.md, SKILL.md, Archive.md, +4) | kept |
| `roles/security-auditor.md` | live | `ROLES_DIR / 'security-auditor.md'` (`engine.py:3893`); `grep -l roles/security-auditor.md` -> 2 (SKILL.md, Archive.md) | kept |
| `roles/technical-writer.md` | live | `ROLES_DIR / 'technical-writer.md'` (`engine.py:3893`); `grep -l roles/technical-writer.md` -> 2 (SKILL.md, Decisions.md) | kept |
| `roles/tester.md` | live | `ROLES_DIR / 'tester.md'` (`engine.py:3893`); `grep -l roles/tester.md` -> 3 (SKILL.md, Decisions.md, Project.md) | kept |
| `scripts/build_pi_package.py` | live | `grep -l scripts/build_pi_package.py` -> 9 (Makefile, Architecture.md, Archive.md, +6) | kept |
| `scripts/check_release_consistency.py` | live | `grep -l scripts/check_release_consistency.py` -> 19 (ci.yml, release.yml, CHANGELOG.md, +16) | kept |
| `scripts/privacy_scan.py` | live | `grep -l scripts/privacy_scan.py` -> 29 (PULL_REQUEST_TEMPLATE.md, privacy-allow.txt, ci.yml, +26) | kept |
| `scripts/sync_skill.py` | live | `grep -l scripts/sync_skill.py` -> 8 (Makefile, Architecture.md, Archive.md, +5) | kept |
| `scripts/teamwork.py` | live | `grep -l scripts/teamwork.py` -> 46 (ci.yml, docs.yml, CHANGELOG.md, +43) | kept |
| `scripts/verify_release.py` | live | `grep -l scripts/verify_release.py` -> 20 (ci.yml, release.yml, CONTRIBUTING.md, +17) | kept |
| `src/teamwork/__init__.py` | live | package entry point (`pyproject.toml` / `python -m teamwork`) | kept |
| `src/teamwork/__main__.py` | live | package entry point (`pyproject.toml` / `python -m teamwork`) | kept |
| `src/teamwork/bundle.py` | live | imported by 4 module(s): build_pi_package.py, sync_skill.py, engine.py, +1 | kept |
| `src/teamwork/cli.py` | live | imported by 4 module(s): teamwork.py, __main__.py, test_context_economy.py, +1 | kept |
| `src/teamwork/config.py` | live | imported by 15 module(s): engine.py, harness.py, hooks.py, +12 | kept |
| `src/teamwork/engine.py` | live | imported by 42 module(s): cli.py, harness.py, conftest.py, +39 | kept |
| `src/teamwork/gitutil.py` | live | imported by 3 module(s): engine.py, harness.py, hooks.py | kept |
| `src/teamwork/harness.py` | live | imported by 1 module(s): engine.py | kept |
| `src/teamwork/hooks.py` | live | imported by 2 module(s): engine.py, test_cli_contract.py | kept |
| `src/teamwork/imaging.py` | live | imported by 1 module(s): engine.py | kept |
| `src/teamwork/io.py` | live | imported by 11 module(s): engine.py, gitutil.py, harness.py, +8 | kept |
| `src/teamwork/layout.py` | live | imported by 4 module(s): engine.py, harness.py, hooks.py, +1 | kept |
| `src/teamwork/names.py` | live | imported by 8 module(s): engine.py, gitutil.py, harness.py, +5 | kept |
| `src/teamwork/portable.py` | live | imported by 3 module(s): engine.py, io.py, test_portable.py | kept |
| `src/teamwork/records.py` | live | imported by 4 module(s): engine.py, harness.py, test_audit_evidence_sources.py, +1 | kept |
| `src/teamwork/resources.py` | live | imported by 3 module(s): config.py, engine.py, test_resources.py | kept |
| `src/teamwork/version.py` | live | imported by 3 module(s): __init__.py, engine.py, test_cli_dispatch.py | kept |
| `templates/AGENTS.md` | live | `bundle.BUNDLE_FILES`; `verify_release.py:44`; `engine.py:9235`; `grep -l templates/AGENTS.md` -> 14 (Architecture.md, Archive.md, Decisions.md, +11) | kept |
| `templates/Docs/Architecture.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Archive.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Board.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Costs.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Decisions.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Design.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Plan.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Project.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Release.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Research.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/Docs/Risks.md` | live | `init` copies it from `TEMPLATES_DIR/'Docs'` (`engine.py:3848`) | kept |
| `templates/TeamMap.md` | live | `config.DIR_TEAM_MAP_TPL`, read by `init` (`engine.py:3848`); `grep -l templates/TeamMap.md` -> 4 (Architecture.md, Archive.md, Decisions.md, +1) | kept |
| `templates/pi-package/prompts/teamwork-pulse.md` | live | `build_pi_package.py:130` ships `prompts/`; `grep -l teamwork-pulse.md` -> 1 (Pi-Packaging.md) | kept |
| `templates/pi-package/prompts/teamwork-review.md` | live | `build_pi_package.py:130` ships `prompts/`; `grep -l teamwork-review.md` -> 1 (Pi-Packaging.md) | kept |
| `templates/pi-package/skills/teamwork-pi/SKILL.md` | live | `build_pi_package.py:127` copies it into the npm package; `grep -l templates/pi-package/skills/teamwork-pi/SKILL.md` -> 1 (Archive.md) | kept |
| `tests/__init__.py` | live | imported by 6 module(s): check_release_consistency.py, privacy_scan.py, cli_harness.py, +3 | kept |
| `tests/acceptance/cli_harness.py` | live | imported by 9 module(s): gate_fixtures.py, test_acceptance_docs.py, test_acceptance_links.py, +6 | kept |
| `tests/acceptance/conftest.py` | live | imported by 1 module(s): __init__.py | kept |
| `tests/acceptance/gate_fixtures.py` | live | imported by 5 module(s): test_acceptance_ci_contracts.py, test_acceptance_docs.py, test_acceptance_links.py, +2 | kept |
| `tests/acceptance/test_acceptance_ci_contracts.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/acceptance/test_acceptance_docs.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/acceptance/test_acceptance_links.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/acceptance/test_acceptance_makefile.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/acceptance/test_acceptance_release_consistency.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/acceptance/test_acceptance_release_workflow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/acceptance/test_cross_platform.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/acceptance/test_entrypoints.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/acceptance/test_full_loop.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/acceptance/test_harness_docs.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/conftest.py` | live | imported by 2 module(s): __init__.py, conftest.py | kept |
| `tests/gitenv.py` | live | imported by 5 module(s): test_harness_docs.py, test_harness_cli.py, test_git_env.py, +2 | kept |
| `tests/integration/test_ci_scope_classifier.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_command_surface.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_context_economy_contract.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_docs_pipeline_flow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_evidence_flow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_harness_cli.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_links_flow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_makefile_flow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_release_consistency_integration.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_release_gate_flow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_release_traceability_flow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_release_workflow_flow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_task_graph_flow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/integration/test_workspace_flow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_archive_mask_identity_rules.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_archive_merge_revisions.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_audit_evidence_sources.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_board_matches_tool.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_ci_contracts.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_cli_contract.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_cli_dispatch.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_code_scanning.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_commit_identity.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_context_economy.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_criteria.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_decision_ids.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_dispute_panel_instances.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_docs_contracts.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_evidence_packets.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_git_env.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_gitignore_bootstrap.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_global_memory_provenance.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_harness_surface.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_hooks.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_hygiene.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_imaging.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_integrity_fixes.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_io.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_ledger.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_ledger_export_worktree.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_lfs_threshold_scope.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_makefile_contracts.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_memory.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_names.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_parallel_capacity.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_pi_package.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_portability.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_portable.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_pr_merge_base_advance.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_pr_task_collision.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_privacy_scan.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_provider_caps.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_refresh_source.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_release_consistency.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_release_consistency_digest.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_release_consistency_r8.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_release_traceability.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_release_workflow.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_reporting_hierarchy.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_research_sources.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_resources.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_review_fanout.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_review_merges_on_pass.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_roster_tiers.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_skill_contracts.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_skill_refresh.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_skill_sync.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_sys_path_hygiene.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_task_graph_integrity.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_tasks.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_test_records.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_traceability_matrix.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/test_worktree_reclaim.py` | live | pytest collects it (1256 tests collected) | kept |
| `tests/unit/workflow_yaml.py` | live | imported by 3 module(s): test_ci_contracts.py, test_makefile_contracts.py, test_release_workflow.py | kept |

#### Deletions

None. The pass proved no tracked file is dead, so it deleted nothing: a file
that only a forge reads by path (`.github/` templates, `docs/CNAME`), a file a
trademark claim names (`docs/assets/nidvue-*`), and a dated measurement a
decision keeps (`M9Acceptance.md`, `AuditReport.md`) are all still in use by
something outside a grep. Deleting one of them on suspicion is the failure mode
this census exists to prevent, and each of the six unreferenced rows below states
the reader that keeps it alive.

#### Kept, justified - the eight non-live rows

| path | why it stays |
|---|---|
| `.github/ISSUE_TEMPLATE/bug_report.yml` | GitHub reads it by path; it is the repo's own bug form, and no in-tree gate replaces it |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | same reason as the bug form |
| `.github/PULL_REQUEST_TEMPLATE.md` | the contributor's checklist; deleting it removes a control, not a file |
| `docs/CNAME` | the custom-domain claim `CHANGELOG.md:427` makes, in the file the Pages deploy needs |
| `docs/assets/nidvue-apple-touch-icon.png` | `NOTICE` names `docs/assets/nidvue-*` as the bundled trademark set |
| `docs/assets/nidvue-favicon.ico` | same trademark set as the touch icon |
| `docs/Team/M9Acceptance.md` | a dated measurement kept as the record of what M9 measured; `D-20261022-CEO-5` keeps a historical document's body, and `Project.md` and `Decisions.md` link it |
| `docs/Team/AuditReport.md` | the audit's dated measurement; the security lane re-stated it under the D-0003 ruling instead of deleting it |

#### Duplicate check

Zero duplicates, measured two ways: no two tracked files share a digest
(`md5sum | uniq -d` -> 0), and the pairs that look like copies are not:

| pair | why both are real |
|---|---|
| `templates/Docs/*.md` vs `docs/Team/*.md` | the template and the instance: `init` copies the first to make the second, and the second carries this team's content |
| `tests/unit/test_portable.py` vs `tests/unit/test_portability.py` | the OS seam's unit tests vs the portability contract (source-level rules, bundle resolution) - 6 tests vs 26, no shared assertion |
| `SKILL.md` vs `templates/pi-package/skills/teamwork-pi/SKILL.md` | the host-agnostic protocol vs the pi-specific layer that maps its six host operations |
| `README.md` vs `docs/guide/install.md` | the entry page vs the install reference the site links; the version pin they share is read by rule R6 of the release checker |

#### Findings handed to their owners

1. **The board gate cannot see M11** (filed as developer T-0006).
   `tests/unit/test_board_matches_tool.py` compares the board with the queues
   through a per-role `FLOOR` table written for M9, and it looks the floor up with
   the folded role name (`norm_role`) while the table is keyed by the hyphenated
   one, so every hyphenated role silently gets floor 0. Measured: in a linked
   worktree the file skips (`4 passed, 2 skipped`) because a worktree has no team
   tree; in the main checkout at `7db810a` it fails (`2 failed, 4 passed`). After
   the re-initialisation for M11 the queues restart at T-0001, so no floor above 1
   can match. Re-run through the gate's own functions against the board below:
   `mismatches()` and `flight_mismatches()` report only tasks the floor excludes
   (`... on the board, but no such task in the milestone`), and not one
   `board says (state, pr, merged), queue says (...)` disagreement - the rows and
   the queues agree on every task the gate does look at.
2. **Two stale instance directories** (filed as ceo T-0008). `Agents/Developer`
   and `Agents/Tester` are not empty - each holds the generated `StartHere.md`,
   `Inbox.md` and `WorkLog.md` - but no task is claimed by `Developer` or
   `Tester`, and the tool counts them as lanes: `teamwork.py agents` ->
   `developer instances=3 [Developer, Developer-1, Developer-2]` and
   `tester instances=2 [Tester, Tester-1]`, while only `Developer-1`,
   `Developer-2` and `Tester-1` hold work. Removing local team state is the
   CEO's call, not a hygiene deletion from this lane.

## M12 - Release parity (live)

Intake, objective, non-goals and the two acceptance criteria are in
[Project](Project.md) M12; this section carries the exit condition and the rows
that deliver it, and pins no state that `teamwork.py` can report. The board renders
the same records for both open milestones: [Board](Board.md).

Exit condition: AC-22 (npm parity) and AC-23 (Pages on release) verified by a role
other than the author on the merged revision, and the two release defects named at
intake closed - release-engineer T-0011 and release-engineer T-0012. Their state
is read with `teamwork.py task list release-engineer` and never from this file.

### M12 engagement tasks

Rendered from `Roles/*/TaskQueue.md` at the revision that carries this section, so
it is what the queues said then and not a claim about now; read any cell again with
`teamwork.py task list <role>` and `teamwork.py pr list`. The selection is
mechanical and re-measurable - it is every task record created in this engagement:
`grep -h '^- created: 2026-10-28' .pi/Teamwork/Teams/Teamwork/Roles/*/TaskQueue.md`.
Housekeeping records filed in the same engagement are included rather than filtered
out, because a table that picked the rows it liked would be a second, hand-kept
view of the queues - the defect the board gate exists to prevent.

| role | id | task | prio | area | state | claimed by | pr | merged |
|---|---|---|---|---|---|---|---|---|
| architect | T-0003 | Architecture.md no longer describes what docs.yml does: it omits the v* tag trigger | P1 | - | todo | - | - | - |
| ceo | T-0011 | Allow v* tags to deploy the github-pages environment so a release can refresh the site | P0 | - | todo | - | - | - |
| ceo | T-0012 | Record the M12 intake, AC-22/AC-23 and the governance decision; own their acceptance | P0 | intake | done | CEO | P-0033 | bd7467d |
| ceo | T-0013 | Add the AC-22/AC-23 rows to the traceability matrix: main's suite is red without them | P0 | docs | done | CEO | P-0034 | 1793013 |
| developer | T-0018 | scripts/build_pi_package.py documents --out only in its module docstring, not in --help, so no workflow may pass it and release.yml builds the bundle with the default out dir instead | P2 | - | todo | - | - | - |
| developer | T-0019 | Record the release area's unit layer from the release tests that exist | P1 | - | done | Developer-1 | P-0036 | 65392da |
| project-manager | T-0004 | Add M12 (release parity: GitHub, npm, Pages) to Plan.md and refresh the board | P1 | plan | dropped | - | - | - |
| project-manager | T-0005 | Release blocker: docs/Team/Board.md is stale against the live queues so the full suite is red at ee75c4a (3 failed in test_board_matches_tool.py) - re-render Board.md only | P0 | plan | review | project-manager | P-0039 | - |
| release-engineer | T-0011 | release.yml uploads SHA256SUMS twice (dist/* and the explicit entry): the duplicate-name race made the v1.3.0 publish job fail with 'Not Found - releases/assets#update-a-release-asset' and need a re-run | P0 | release | done | release-engineer | P-0030 | 7908d44 |
| release-engineer | T-0012 | Push the branch and its tag together (git push --atomic): pushing main first made the main CI release-consistency gate run without the new tag and fail R6 until the job was re-run | P1 | - | todo | - | - | - |
| release-engineer | T-0013 | Publish @nidvue/teamwork to npm from every v* tag, and make the release asset set unique (supersedes T-0011) | P0 | release | done | release-engineer | P-0031 | d3f9b7a |
| release-engineer | T-0014 | Pages rebuilds and deploys from the released revision on a v* tag | P0 | release | done | release-engineer | P-0032 | c41ecfe |
| release-engineer | T-0015 | Backfill the already-tagged release to npm once the operator configures the publisher credential | P1 | - | blocked | - | - | - |
| reviewer | T-0004 | Land the D-0004 tribunal ruling in Decisions.md on main (commit 4645118) | P0 | - | done | Reviewer-2 | P-0038 | e038181 |
| technical-writer | T-0005 | Site and README: npm as a first-class install channel plus a releases page | P0 | docs | done | technical-writer | P-0035 | 1d94e18 |
| tester | T-0003 | Record the release area's integration layer on the merged revision | P1 | - | done | tester-1 | P-0037 | 3627c7d |
| tester | T-0004 | Delete the merged branch tester-1/t-0003-record-the-release-area-s-integration-la: your Runtime worktree still has it checked out, so the merge at 3627c7d could not retire it | P2 | - | todo | - | - | - |

Both proofs the exit condition asks for come from a tag run of the merged
pipeline, and no commit can supply that measurement: `grep -c 'npm publish'
.github/workflows/release.yml` and the `on:` block of `.github/workflows/docs.yml`
show the pipeline is in place, and the first `v*` tag after this merge is what
measures it. Both criteria are recorded red at intake as gaps G-11 and G-12 in
[Project](Project.md), where each carries the command that re-measures it; the row
that closes AC-22's evidence is release-engineer T-0015, blocked on the operator's
npm credential, and AC-23 also waits on the `github-pages` environment policy
(ceo T-0011).

## M13 - Code integrity, CI truth and reviewer throughput (live)

Intake: the user asked for a systematic review of the code that fixes what it
finds, the CI errors fixed, and the reviewer lane made faster because it had
become the bottleneck. Scope, non-goals and the machine criteria AC-R1..AC-R7 are
in [Project](Project.md); this section names the lanes and where their evidence
lands.

| lane | what it owns | evidence |
|---|---|---|
| Reviewer-1 audit | `engine.py` task/queue/review/pulse/loop paths, ranked findings with a reproduction each | `Agents/Reviewer-1/Reports/M13-engine-audit.md` |
| Reviewer-2 audit | support modules, `scripts/`, workflows, Makefile | `Agents/Reviewer-2/Reports/M13-support-audit.md` |
| Tester audit | vacuous/flaky tests, cross-platform hazards, CI scope paths | `Agents/Tester/Reports/M13-test-audit.md` |
| Security audit | `privacy_scan.py` rule coverage and the release trust boundary | `Agents/SecurityAuditor/Reports/M13-security-audit.md` |
| Fix lanes | one branch and PR per task, each with its own test; the Reviewer that verified it merges it | `teamwork.py task list developer`, [Archive](Archive.md) |
| Architect | the R2-on-a-feature-branch decision and the committer-guard fallback scope | [Decisions](Decisions.md), [Architecture](Architecture.md) section 11.2.2 |

Measured before the throughput change, from this team's own ledger on 2026-10-29:
a review claim lived 20 minutes while claim-to-verdict was p50 42.4 / p90 125.2
minutes, so a standard or deep claim could be taken over mid-review; and
`review --queue` listed ten unfinished tasks where one was submitted. T-0017 made
R2 green after the `v1.4.2` tag; T-0015 fixed the committer guard that audited the
whole ancestry on a pull request; T-0016 made the queue measure submitted work and
the lease follow the review profile.

Findings that are real but not fixed in this engagement carry a task with the
audit row as evidence and the reason they wait; they are not dropped silently.

## M14 - Tree truth: claims, assets, hygiene, and the gate on this host (live)

Intake: the operator asked to continue the project and get the rest of the job
done. The M11-M13 judgements that the tree was true, the assets sound and the
code clean were carried by prose; this engagement re-measures them as four
machine criteria (`criteria list`, AC-1..AC-4) and repairs what disagrees.

Non-goals: a new engine feature, a roster change, a published tag, npm
publication (blocked on the operator credential - G-11), and any history rewrite.

Exit condition: AC-1..AC-4 verified by a role other than the owner on the merged
revision, `teamwork.py tests plan` with no gap for a staffed role, `loop` STOP.

| lane | task | what it owned | merged |
|---|---|---|---|
| Technical Writer | T-0001 | every public claim in README, root policies, mkdocs config, `docs/**` except internal records | `ff9a708` |
| Technical Writer | T-0002 | the six surfaces that described the old team-wide `clean` | `543c665` |
| Technical Writer | T-0003 | the licence contradiction in `CITATION.cff` and the quickstart ordering | `a1929ba` |
| Technical Writer-2 | T-0004 | the roster-tier table a doc change invalidated | `aeed914` |
| Designer | T-0001 | every asset in `assets/`, `docs/assets/` and the README mermaid diagram | `7783953` |
| Designer | T-0002 | the geometry cells its own rewrite moved out of the docs contract | `aeb5d62` |
| Designer | T-0003 | the connectors below the 3:1 bar | `1f648fd` |
| Developer-1 | T-0001 | dead files and comments in `src/` and `scripts/` | `304d757` |
| Developer-2 | T-0002 | `scripts/build_pi_package.py` shelling out to `du -sh` | `381bb5c` |
| Developer-2 | T-0004 | R8 reading any word after `pip install` as a distribution claim | `252e9d4` |
| Developer-2 | T-0005 | `clean --all` being team-wide, so one lane emptied every peer's `Scratch/` | `6111b1a` |
| Developer-3 | T-0003 | an unlaunchable gate escaping, and POSIX-only proof cells crashing the matrix guard | `cf26e96` |
| Developer-3 | T-0006 | the board renderer's missing role spellings | `5895411` |
| Developer-4 | T-0007 | a fresh project could not render the board `init` had just written | [FILL] |
| Architect | T-0001 | the `system` layer: no POSIX-only launch, every failure guarded or red | `0cac9bd` |
| Tester | T-0001 | the gate certification, both `integration` layers, and the red it refused to waive | `8b5db3f` |
| CEO | T-0001, T-0002 | the merge contract three public surfaces still claimed | `d36e731`, `cd561a5` |

### M14.1 - The gate was not runnable on this host

Baseline before any lane started, on `333c08a`, win32, python 3.15.2:
`pytest -q` -> **10 failed, 1540 passed, 46 skipped** (14m01s). The repository
`.venv` is a WSL virtualenv (`bin/`, no `Scripts/`) and no `pytest`/`ruff` exists
on the PATH, so the findings were read from a fresh `venv/` (gitignored, already
covered by `.gitignore`). Nine of the ten survived the editable install the
documented `make dev` step performs; the tenth (`test_sys_path_hygiene`) *was*
that missing step, not a defect. The nine: four board rows against the
re-initialised queues (the closing render), three `du` failures, one `sh`
failure, one POSIX proof cell. Nothing was waived; each of the three real
classes became a task above.

The decision is `D-20261030-CEO`; the host fact is in global memory under
`build`. `mypy` is **UNVERIFIED** on this host (not installed in either
interpreter).

### M14.2 - What the reviews cost and caught

Seven deliverables were failed and re-reviewed as deltas, and two criteria were
refused by their independent verifier. Every fail named a defect that the author
could have found locally - one of them in the author's own evidence line:

| fail | finding | closed by |
|---|---|---|
| designer T-0001 | no PR, so the branch could never merge | `pr open`, content unchanged |
| technical-writer T-0001 | a new sentence claimed nothing else pins the allowlist; a test pins its exact five entries | corrected sentence + the pinning test in the same change |
| developer-2 T-0005 | the scope fix left an unfiltered `*.tmp` sweep that still deleted a peer's file, and 4 of 5 tests failed on argparse rather than on behaviour | every unlink routed through the scope; tests rewritten to assert effects |
| developer-3 T-0003 | a new timeout branch with no test anywhere | one test that fails when the branch is deleted |
| technical-writer-2 T-0004 | the commit's "measured" figure was one byte off at the revision it pinned | message corrected, tree unchanged |
| tester T-0001 | a certification with no branch: `--no-merge` would have left a `pending` archive line on a clean tree | a real commit closing the positive `--team-wide` coverage gap |
| ceo T-0002 | the new sentence claimed a post-merge history the merge does not produce | `--no-ff` named, `main` keeps both commits |

Two verifiers refused to verify and were right to:

| criterion | what the verifier found | closed by |
|---|---|---|
| AC-1 | `CITATION.cff` said `AGPL-3.0-only` while `NOTICE`, `pyproject.toml` and the npm metadata grant or-later | `P-0014`; no gate reads the licence field, so `R-23` is the real defect |
| AC-2 | three banner connectors at 2.78:1 against a 3:1 bar; the author's own probe had classified them as decoration | `P-0013`, after the CEO ruled the connectors meaningful and the outlines decorative |

Neither verifier passed a criterion it could not reproduce, and neither invented a
record to fill the matrix.

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

The invariants are executable: `teamwork.records.task_graph_problems()` resolves
role-qualified node keys, and `teamwork.py task check` reports the same problems
over the queues on disk - a dangling dep, a self-dependency or cycle (with its
path), a queue holding one open id twice, and a task with no priority.
`tests/unit/test_task_graph_integrity.py` is the invariant record that calls it,
and the `task add` / `task set --deps` write gates refuse a graph the checker
rejects, so a deadlocked queue is never written in the first place.

```sh
teamwork.py task check
PYTHONPATH=src python -m pytest tests/unit/test_task_graph_integrity.py -q
```

## Parallel rules

- Interfaces were frozen in [Architecture](Architecture.md) before any lane
  started; one writer per file (see the ownership table there).
- Tests are written from the frozen contract, in parallel with implementation.
- Docs never block code or tests.
- Only the CEO pushes, tags, releases or writes to GitHub.
