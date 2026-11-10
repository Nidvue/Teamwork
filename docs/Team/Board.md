# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Archive](Archive.md)

## Snapshot

- Date: 2026-10-17
- Milestone: M1 - Package the engine (M2 in parallel)
- Verified criteria: 0/12 (all open; evidence is recorded as each lane lands)

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | T-0000 bootstrap: brief, criteria, interfaces, package skeleton, engine move | P0 | done | `docs/Team/Project.md`, `docs/Team/Architecture.md`, `src/teamwork/` |
| developer | T-0001 packaging + build + verify | P0 | doing | `pyproject.toml`, `Makefile`, `scripts/verify_release.py` |
| developer | T-0002 unit + integration tests | P0 | doing | `tests/unit/`, `tests/integration/` |
| tester | T-0004 acceptance tests | P0 | doing | `tests/acceptance/` |
| release-engineer | T-0005 CI/CD | P0 | doing | `.github/workflows/` |
| technical-writer | T-0006 docs + community files | P1 | doing | `docs/guide/`, `mkdocs.yml` |
| designer | T-0007 README + visuals | P0 | doing | `README.md`, `assets/` |
| security-auditor | T-0008 privacy scanner + audit | P0 | doing | `scripts/privacy_scan.py`, `docs/Team/AuditReport.md` |
| architect | T-0003 portability test + verification | P0 | doing | `tests/unit/test_portability.py` |
| ceo | T-0009/T-0010 review gate | P0 | todo | `docs/Team/Reviews.md` |
| ceo | T-0011/T-0012 publish + final audit | P0 | todo | GitHub release, `AuditManifest.json` |

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| T-0011 publish | privacy rewrite + green CI | ceo | rewrite the single initial commit, force-push, watch CI |
| T-0006 docs site | mkdocs-material install | technical-writer | `pip install --user mkdocs-material` (local only) |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
