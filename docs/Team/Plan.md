# PLAN - milestones and task graph

Owner: Project Manager. One row per task; `deps` must be `done` before it runs.
Priority: P0 code, P1 tests, P2 docs.

Related: [Project](Project.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## Status summary (2026-10-19, `main` @ `8444134`)

| milestone | exit condition | state |
|---|---|---|
| M0 Audit follow-up | `loop` STOP + `audit` 0 problems | done - T-0001..T-0007 |
| M1 Package the engine | `selftest` + installed wheel `--version` | done |
| M2 Make it attractive | README demo, strict docs site, 0 broken links | done |
| M3 Independent verification | every deliverable has a Reviewer verdict | done |
| M4 Publish | `v1.0.0` release with wheel, sdist, `SHA256SUMS`, SBOM | done - now at `v1.0.2` |
| M5 Post-1.0 hardening | typed module split, Windows-green matrix, dependency upkeep | done - T-0010..T-0016, closing T-0017 |
| M6 Evidence packets + repro gate | hashed evidence artifacts, repro-first bug gate, Reviewer verdicts | done - T-0020..T-0025 |

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

## Parallel rules

- Interfaces were frozen in [Architecture](Architecture.md) before any lane
  started; one writer per file (see the ownership table there).
- Tests are written from the frozen contract, in parallel with implementation.
- Docs never block code or tests.
- Only the CEO pushes, tags, releases or writes to GitHub.
