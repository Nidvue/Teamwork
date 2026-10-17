# PLAN - milestones and task graph

Owner: Project Manager. One row per task; `deps` must be `done` before it runs.
Priority: P0 code, P1 tests, P2 docs.

Related: [Project](Project.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## M1 - Package the engine (parallel with everything else)

Exit: `python3 scripts/teamwork.py selftest` passes and `python -m teamwork --version`
prints `teamwork 1.0.0`, from a checkout and from an installed wheel.

| id | task | role | prio | deps | artifact | status |
|---|---|---|---|---|---|---|
| T-0001 | Package + build + verify script | developer | P0 | - | `pyproject.toml`, `Makefile`, `scripts/verify_release.py` | doing |
| T-0003 | Portability test + engine verification | architect | P0 | - | `tests/unit/test_portability.py` | doing |
| T-0002 | Unit + integration tests | developer | P0 | - | `tests/unit/`, `tests/integration/` | doing |
| T-0004 | Acceptance tests + full-loop proof | tester | P0 | - | `tests/acceptance/` | doing |
| T-0005 | CI/CD + release pipeline | release-engineer | P0 | - | `.github/workflows/` | doing |
| T-0008 | Privacy scanner + audit report | security-auditor | P0 | - | `scripts/privacy_scan.py`, `docs/Team/AuditReport.md` | doing |

## M2 - Make it attractive

Exit: README leads with a demo and a comparison table; the docs site builds
`--strict`; every internal link resolves.

| id | task | role | prio | deps | artifact | status |
|---|---|---|---|---|---|---|
| T-0007 | README, banner, terminal demo, Design.md | designer | P0 | - | `README.md`, `assets/`, `docs/Team/Design.md` | doing |
| T-0006 | Docs site + community files | technical-writer | P1 | - | `mkdocs.yml`, `docs/guide/`, `CONTRIBUTING.md`, ... | doing |

## M3 - Independent verification

Exit: every deliverable has a Reviewer verdict with reproducible evidence and the
team-level `loop` reports STOP.

| id | task | role | prio | deps | artifact | status |
|---|---|---|---|---|---|---|
| T-0009 | Second review of the package + tests | reviewer | P0 | T-0001..T-0005 | `docs/Team/Reviews.md` | todo |
| T-0010 | Second review of docs, README, privacy | reviewer | P0 | T-0006..T-0008 | `docs/Team/Reviews.md` | todo |

## M4 - Publish

Exit: `v1.0.0` is released on GitHub with wheel, sdist, `SHA256SUMS` and an SBOM;
CI is green on the pushed revision; repository metadata is set.

| id | task | role | prio | deps | artifact | status |
|---|---|---|---|---|---|---|
| T-0011 | Merge, set metadata, tag and release | ceo | P0 | T-0009, T-0010 | `docs/Team/Release.md`, GitHub release | todo |
| T-0012 | Final audit: `ledger verify`, `audit`, `links`, `loop` | ceo | P0 | T-0011 | `docs/Team/AuditManifest.json` | todo |

## Parallel rules

- Interfaces were frozen in [Architecture](Architecture.md) before any lane
  started; one writer per file (see the ownership table there).
- Tests are written from the frozen contract, in parallel with implementation.
- Docs never block code or tests.
- Only the CEO pushes, tags, releases or writes to GitHub.
