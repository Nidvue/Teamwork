# ARCHITECTURE - Teamwork

Owner: Architect. Frozen interface contract for every parallel lane. Nothing in
this file changes without a recorded decision in [Decisions](Decisions.md).

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md) · [AuditReport](AuditReport.md) · [user guide](../guide/architecture.md)

## 1. What the system is

`Teamwork` is simultaneously:

1. **A Pi skill** - `SKILL.md`, `roles/`, `references/`, `templates/` at the
   repository root, loadable as `~/.pi/agent/skills/teamwork`.
2. **A Python package** - `src/teamwork/`, installable with `pip install .`,
   exposing the `teamwork` console script and `python -m teamwork`.
3. **A workspace format** - markdown + JSON under
   `<project>/.pi/Teamwork/Teams/<Team>/`.

The three share one engine. The engine is a port of the original 7,416-line
`teamwork.py` monolith with **behaviour unchanged**.

## 2. Frozen repository layout

```
Teamwork/
├── SKILL.md                  # canonical skill entry (Pi loads this)
├── roles/*.md                # 15 role charters
├── references/*.md           # policy detail
├── templates/                # AGENTS.md, Docs/*.md, TeamMap.md skeletons
├── src/teamwork/
│   ├── __init__.py           # __version__, lazy re-exports
│   ├── __main__.py           # python -m teamwork -> cli.main()
│   ├── cli.py                # build_parser() + main(argv) -> int
│   ├── engine.py             # the ported monolith (single module)
│   ├── resources.py          # locate the skill bundle (checkout or wheel)
│   └── version.py            # __version__ = "1.0.0"
├── scripts/
│   ├── teamwork.py           # thin compat shim -> teamwork.cli.main
│   ├── verify_release.py     # build + install + smoke-test a wheel
│   └── privacy_scan.py       # tree + history privacy gate
├── tests/{unit,integration,acceptance}/  # pytest
├── docs/                     # mkdocs site (index/install/quickstart/...)
├── docs/Team/                # team-generated project documents
├── .github/workflows/        # ci.yml, release.yml, docs.yml
├── assets/                   # SVG logo, banner, terminal demo
├── pyproject.toml, Makefile, mkdocs.yml
└── community files           # README, CONTRIBUTING, SECURITY, CHANGELOG, CITATION
```

**File ownership (one writer per file) is binding for parallel work:**

| Lane | Owns |
|---|---|
| developer-1 | `src/teamwork/**`, `scripts/teamwork.py` |
| developer-2 | `tests/unit/**`, `tests/integration/**`, `tests/conftest.py` |
| tester-1 | `tests/acceptance/**` |
| developer-3 | `pyproject.toml`, `Makefile`, `scripts/verify_release.py`, `.editorconfig` |
| release-engineer | `.github/**` |
| technical-writer | `docs/*.md`, `mkdocs.yml`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `CITATION.cff` |
| designer-1 | `README.md`, `assets/**` |
| security-auditor | `scripts/privacy_scan.py`, `docs/Team/AuditReport.md` |
| architect | `docs/Team/Architecture.md`, `tests/unit/test_portability.py` |
| product-manager | `docs/Team/Research.md` |
| project-manager | `docs/Team/Plan.md`, `docs/Team/Board.md` |

## 3. Resource-resolution contract (`resources.py`)

The engine needs four resource groups: `SKILL.md`, `roles/`, `references/`,
`templates/`, and a runnable engine path. Resolution order, first hit wins:

```
1. $TEAMWORK_SKILL_DIR                     (explicit override, tests use this)
2. importlib.resources.files("teamwork") / "data"   (installed wheel)
3. <repo root>/   where repo root = engine.py.parents[2]   (checkout)
```

Public API (frozen):

```python
skill_root() -> Path            # directory holding SKILL.md + roles/ + references/ + templates/
asset(*parts) -> Path           # skill_root() joined with parts
self_invocation() -> str        # how a teammate should invoke the CLI
has_asset(name: str) -> bool
```

`self_invocation()` returns, in order of preference:
`teamwork` when a console script is importable/on PATH, else
`python -m teamwork`, else `python <path-to scripts/teamwork.py>`.

`engine.py` must call `resources` instead of the old
`SKILL_DIR = Path(__file__).resolve().parent.parent`.

## 4. CLI contract (frozen, backward compatible)

Invocation forms, all equivalent:

```
teamwork <cmd> ...            # console script
python -m teamwork <cmd> ...  # module
python scripts/teamwork.py <cmd> ...   # checkout shim
```

Additions to the original surface (no removals, no renames):

| Addition | Behaviour |
|---|---|
| `--version` | prints `teamwork <version>` and exits 0 |
| `version` subcommand | same as `--version` |
| `teamwork selftest` | runs an offline smoke check of the workspace (used by CI) |

Every existing subcommand, flag and exit code is unchanged. Exit codes: `0`
success, `1` generic error, `3` "nothing to dispatch" (pulse), `4` lock timeout,
`5` evidence/gate refusal.

## 5. Workspace-format contract (frozen)

Unchanged from the skill: `.pi/Teamwork/Teams/<Team>/` with `Roles/<Role>/`
(shared memory + `TaskQueue.md`), `Agents/<Instance>/` (private), `Global/`,
`Runtime/`, `Ledger.jsonl` (hash-chained), `Criteria.md`, `Tests.md`,
`TestPlan.md`, `Reviews.md`, `Disputes.md`.

The ledger record shape and chain (`_digest(prev, record)`) are frozen; changing
them invalidates every existing workspace.

## 6. Portability contract

* Runtime: CPython **3.9 - 3.13**, Linux, macOS, Windows. No third-party import
  at runtime.
* Forbidden in the runtime path: `fcntl`, `termios`, `pwd`, `grp`, `os.fork`,
  `resource`, `shell=True`, POSIX-only signal use.
* All file I/O passes `encoding="utf-8"`; generated text is written with
  `newline="\n"` for byte-identical output across platforms.
* Process liveness for stale-lock recovery must use a portable helper:

```python
def pid_alive(pid: int) -> bool   # Windows-safe; never kills anything
```

* Paths never hardcode `/tmp`, `/home` or a drive letter; use
  `tempfile` / `pathlib` only.

## 7. Packaging contract

* Build backend: `hatchling`. `python -m build` produces
  `dist/teamwork_agents-<v>.tar.gz` and `dist/teamwork_agents-<v>-py3-none-any.whl`.
* Distribution name `teamwork-agents` (PyPI `teamwork` is taken); import name
  `teamwork`; console script `teamwork`.
* Canonical assets are force-included into the wheel at `teamwork/data/`:
  `SKILL.md`, `roles/`, `references/`, `templates/`.
* Runtime dependencies: none (`dependencies = []`). `requires-python = ">=3.9"`.
* The wheel must contain `teamwork/data/SKILL.md` and
  `teamwork/data/templates/AGENTS.md` - `scripts/verify_release.py` asserts this.

## 8. Test contract

| Layer | Location | Owner | Must prove |
|---|---|---|---|
| unit | `tests/unit/` | developer-2, architect | pure functions: parsing, slugify, pascal, identity, ledger digest, task deps, portable locks |
| integration | `tests/integration/` | developer-2 | init → memory → task → criteria → tests → ledger on a tmp workspace |
| acceptance | `tests/acceptance/` | tester-1 | three entrypoints, full selfcheck→review→loop STOP, installed-wheel bootstrap |

Tests must run with `pytest -q` from the repo root and also with an installed
wheel (no reliance on the source tree). `conftest.py` sets
`TEAMWORK_SKILL_DIR` to the repo root and runs each test in a `tmp_path`.

## 9. CI / release contract

* `ci.yml`: `lint` (ruff), `typecheck` (mypy, non-blocking report), `test`
  matrix `{ubuntu,macos,windows} x {3.9,3.11,3.13}`, `build`
  (sdist+wheel+verify_release), `privacy` (`privacy_scan.py --history`),
  `docs` (mkdocs build --strict).
* `release.yml`: on `v*` tags - build, checksums (`SHA256SUMS`), SBOM
  (CycloneDX JSON + SPDX), attestation, GitHub Release with all assets.
* `docs.yml`: build and deploy the site to GitHub Pages on `main`.
* Nothing is pushed, tagged or released by any agent other than the CEO.

## 10. Seams for testing

* `resources.skill_root()` honours `TEAMWORK_SKILL_DIR` → tests point the engine
  at a fixture bundle.
* `engine` is importable as a module (`teamwork.engine`) → unit tests call
  functions directly instead of parsing CLI output.
* `--project` / `--team` already exist → every test isolates its workspace.
