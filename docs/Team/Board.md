# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## Snapshot (2026-10-19, `main` @ `6905869`)

- Milestone: M5 post-1.0 hardening (M1-M4 delivered; `v1.0.2` is the latest release)
- Local gate: `pytest -q` -> 350 passed, 1 skipped; coverage 62.38%
  (floor 55%, enforced in `pyproject.toml` and `ci.yml`)
- CI: run `39173857076` green on `b6dea2a` (16/16 jobs incl. all Windows and
  macOS cells); Docs run `39176294486` green on `6905869`
- Privacy: `privacy_scan.py --tree --history` -> PASS, 0 findings
- Links: `teamwork.py links` -> 0 problems
- Baseline gate at `6905869`: `teamwork.py loop` -> STOP and
  `teamwork.py audit` -> 0 problems with the ledger chain intact (138 records at
  that revision)
- Remote: local `main` and `origin/main` are in sync (0 ahead, 0 behind)

While any M5 task is open, `audit` and `loop` report that open work by design:
unfinished tasks, deliverables awaiting review, an unmerged branch, and any
required test layer without a passing record. The exact count changes with the
queue, so it is not restated here - run `teamwork.py audit` for the live list.
When every M5 task is closed and merged, the closing `audit` runs clean and its
manifest is exported to `docs/Team/AuditManifest.json`.

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | T-0014 dependency upkeep: PRs #11, #12, #13 | P0 | in flight | `.github/workflows/release.yml` |
| ceo | T-0015 governance docs refresh | P1 | in flight, round 3 after two failed reviews | `docs/Team/Plan.md`, `Board.md`, `Risks.md`, `Release.md` |
| ceo | T-0016 `ensure_gitignore` orphan headers and glob-covered entries | P1 | todo | `src/teamwork/engine.py`, tests |

The task queue (`teamwork.py task list ceo`) is authoritative for a task's exact
state; this table only says which lanes are open.

## Open dependency PRs

| PR | bump | head | checks |
|---|---|---|---|
| #11 | `anchore/sbom-action` 0.24.0 -> 0.24.3 | `5874825` | 17 pass, Pages deploy skipped |
| #12 | `actions/attest-build-provenance` -> `4d101475` | `7cb50af` | 17 pass, Pages deploy skipped |
| #13 | `softprops/action-gh-release` -> `efb35369` | `9c10386` | 17 pass, Pages deploy skipped |

All three branches were rebased onto `main` @ `6905869` (the earlier red Windows
jobs came from the retired umask assertion, fixed in `f2e3b5a`). Each bump keeps
the SHA-pinned style (`uses: owner/action@<sha> # vN`). Missing `ci` and
`dependencies` labels were created so Dependabot can label future PRs.

## Closed history

| milestone | result | evidence |
|---|---|---|
| M1 package the engine | done | `scripts/verify_release.py` -> `OK - release verified` |
| M2 attractive docs | done | `mkdocs build --strict` green; `links` -> 0 |
| M3 independent verification | done | `docs/Team/Archive.md` verdicts |
| M4 publish | done | releases `v1.0.0`, `v1.0.1`, `v1.0.2` with wheel, sdist, `SHA256SUMS`, SBOM |
| M5a engine split + Windows green | done | commits `c8fb469`, `f2e3b5a`, `b7fe03b`; CI `39173857076` |
| M5b dependency upkeep + governance refresh | in flight | T-0014, T-0015, T-0016 |

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| purge of the pre-rewrite commit object | GitHub garbage collection or Support | CEO | owner decision: leave it, recreate the repository, or file a Support purge request. It is unreachable from any branch and was already unreachable when the history was rewritten |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
