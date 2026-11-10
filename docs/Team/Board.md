# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Archive](Archive.md)

## Audit snapshot (2026-10-18)

- Milestone: full-project code/design/workflow/CI audit
- Result: `main` @ `81301d9`; `loop` STOP, `audit` 0 problems, ledger chain intact,
  `make ci` green, privacy PASS, links 0
- Tasks: T-0001..T-0007 done (engine integrity, ledger, paths, locks, privacy,
  CI/docs, local identity, exit-code docs)
- Residual: engine split/typing remains the tracked post-1.0 refactor; coverage
  floor is 38% and the measured value is 51.45%
- Push: local `main` is ahead of `origin/main`; remote push is a Release Engineer /
  owner action, not done by this audit

## Snapshot

- Date: 2026-10-17
- Milestone: M4 - Publish (M1-M3 delivered and now review-gated)
- Verified criteria: 0/16 recorded as verified so far; evidence for AC-1/2/3/9/10
  is green locally, AC-13..16 green locally, AC-4/5/7/8 await the pushed revision
- Remote: `main` cleaned of the personal author and force-pushed once; the old
  object is still retrievable by direct SHA on GitHub until it is purged (see
  [Risks](Risks.md) R-2 and the final report)

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | T-0000 bootstrap: brief, criteria, interfaces, package, engine, docs | P0 | done | `docs/Team/`, `src/teamwork/` |
| developer | T-0001/2 packaging + unit & integration tests | P0 | done | `pyproject.toml`, `Makefile`, `scripts/verify_release.py`, `tests/` |
| tester | T-0001 acceptance tests + CI certification | P0 | doing | `tests/acceptance/` |
| release-engineer | T-0001 CI/CD + staged pushes | P0 | doing | `.github/workflows/` |
| security-auditor | T-0001 privacy scanner + audit report | P0 | done | `scripts/privacy_scan.py`, `docs/Team/AuditReport.md` |
| designer | T-0001 README, SVG assets, social preview, Design.md (incl. imaging) | P0 | done | `README.md`, `assets/`, `docs/Team/Design.md` |
| technical-writer | T-0001 docs site + community files | P1 | done | `docs/guide/`, `mkdocs.yml` |
| architect | T-0001/2 portability test, engine verification, link reciprocity | P0 | done | `tests/unit/test_portability.py` |
| reviewer | re-review of the current revision | P0 | doing | verdict to be recorded |

## CI findings from the first pushed revision (main@8ee248f)

| id | job | finding | owner | resolution | state |
|---|---|---|---|---|---|
| CI-1 | test (windows-latest, py3.9/3.11/3.13) | `test_cross_platform.py::test_generated_files_have_no_cr_bytes` failed: 37 generated files contained CRLF because `Path.write_text`/`open` did not pin `newline` | Developer | every text write in `src/teamwork/engine.py` now pins `newline="\n"`; local static guard added in `tests/unit/test_portability.py` | fixed locally, re-verify on the next push |
| CI-2 | privacy scan (tree + history) | the six Dependabot branches were based on the pre-rewrite history and still carried the old author identity and the fixture blob | Release Engineer | stale PRs closed and their branches deleted; only `main` remains | fixed, re-verify on the next push |
| CI-3 | docs | `configure-pages` failed: Pages was not enabled | Release Engineer | Pages enabled with `build_type=workflow`; the run is green | resolved |

Everything else on that revision was green: lint, typecheck, build, docs, all
ubuntu/macos jobs and windows/py3.13 before the CRLF assertion.

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| publish + tag | Reviewer re-verdict, then CI green on the pushed SHA | CEO | push the fixed revision, watch CI, tag `v1.0.0` |
| purge of the old commit object | GitHub garbage collection or Support | CEO | owner decision: leave, delete+recreate the repo, or a Support purge request |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
