# CI pipeline - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [CLI reference](cli.md) · [Architecture](architecture.md)

The same pipeline runs in GitHub Actions and locally. Each step has a `make`
target; the underlying command is shown so it can be run without `make`.

## One-shot

```console
$ make ci
```

Runs lint, tests, the engine selftest, the skill-sync check, build/verify, release
consistency, privacy scan, docs build, link check and the commit-identity audit
in order, stopping at the first failure.
The target is `release-check`, and `make ci` is its alias - the same recipe, not
a superset. `make typecheck` is deliberately not in it: mypy is a report, not a
gate, in CI as well as locally.

## Steps and targets

| Target | Underlying command | What it proves |
|---|---|---|
| `make lint` | `ruff check .` + `ruff format --check .` + `python scripts/check_comments.py` | Style, import order, formatting and the no-comment rule. |
| `make ci-fast` | `make lint` + `python scripts/teamwork.py links` + `pytest -q tests/unit/test_docs_contracts.py` | The single local gate the team preflight runs: the lint job's gates, link health and the docs contract, in about two seconds. It refuses an interpreter below the 3.11 floor, which is what CI runs. |
| `make typecheck` | `mypy src/teamwork` | Type report (non-blocking in CI). |
| `make test` | `pytest -q` | Unit, integration and acceptance tests. |
| `make build` | `python -m build` | An sdist and a wheel are produced. |
| `make verify` | `python scripts/verify_release.py` | The wheel bundles the skill and installs cleanly. |
| `make release-consistency` | `python scripts/check_release_consistency.py` | Every published fact (a tag, a CHANGELOG section, a version token in a document) agrees with `src/teamwork/version.py`. Offline; the online half runs in `release.yml`. |
| `make privacy` | `python scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` | No personal data, credentials, agent-host configuration or local state in the tree, the index or the history. The allowlist exempts specific committed values by exact literal, each with a written reason; a credential on the same line is still reported. |
| `make docs` | `python -m mkdocs build --strict` | The docs site builds with no warnings. |
| `make links` | `python scripts/teamwork.py links` | No broken links, bare URLs or missing back-links. |
| `make identity` | `python scripts/teamwork.py identity --audit` | Every team commit is authored and committed by its role. |
| `make selftest` | `python scripts/teamwork.py selftest` | The installed engine passes its smoke check. |
| `make clean` | - | Remove build output and caches. |

!!! note "Make wrappers"
    The `Makefile` is a convenience wrapper over these commands. If a target is
    not present in your checkout, run the command in the middle column directly.

## Environment setup

```console
$ python -m venv .venv
$ . .venv/bin/activate            # Windows: .venv\Scripts\activate
$ python -m pip install -e ".[dev]"
$ python -m pip install -r docs/requirements.txt
```

The `dev` extra installs `pytest`, `pytest-cov`, `ruff`, `mypy` and `build`;
`docs/requirements.txt` installs `mkdocs-material`.

## What CI runs

`.github/workflows/ci.yml` runs the jobs below. The first column is the job id in
that file:

```text
scope -> lint -> committer-guard -> typecheck -> test -> build -> privacy
      -> release-consistency -> docs
```

`scope` is the classifier the rest hang off. The logic lives in
`scripts/ci_scope.py`; the `scope` job runs it with the event, ref and push range,
and it answers two questions: `code` (did anything that ships change?) and `prose`
(did anything in the documentation set below change?). They are separate because a
prose-only push answers them differently - `code=false`, `prose=true` - and the
jobs they gate must be a different set.

* `lint`, `typecheck`, `test` and `build` follow `code`. A prose-only push skips
them: nothing they read changed.
* `privacy` and `docs` follow `code || prose`. They are the prose-relevant gates,
and both still run when only documentation changed: a documentation leak is
still a leak, so the privacy scan reads prose too, and the `docs` job is the link
check plus the strict site build of the very pages the push edited.
* A pull request and a manual run execute every job.
* A tag push runs only the consistency gate and `committer-guard`, because the
tagged commit already passed the matrix as a `main` push (neither of those two
jobs is filtered by `scope`, so neither can be skipped).

Prose is exactly `scripts/ci_scope.py::prose_paths()`: `docs/`, `assets/`, and
these root files - `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
`CODE_OF_CONDUCT.md`, `CITATION.cff`, `LICENSE`, `AGENTS.md`, `mkdocs.yml`. There
is no `*.md` wildcard. The `paths:` list of `docs.yml` is pinned to those globs by
`tests/unit/test_ci_scope.py`, so a path that leaves one list without joining the
other fails a test instead of becoming a hole in a gate.

**`SKILL.md` is not prose.** It ships inside the wheel (`pyproject.toml`,
`[tool.hatch.build.targets.wheel.force-include]`: `"SKILL.md" =
"teamwork/data/SKILL.md"`), so a push touching only `SKILL.md` runs the full
matrix - the wheel content changed and has to be rebuilt and verified. The other
root files are outside both lists for the same kind of reason: `Makefile`,
`pyproject.toml` and `release-exceptions.json` are tooling, `NOTICE` ships in the
packaged skill tarball, and `.gitignore`, `.gitattributes` and `.editorconfig`
configure the build. `NOTICE` beside `LICENSE` is the asymmetry to remember:
`LICENSE` is prose, `NOTICE` is not.

| Job | Matrix | Step |
|---|---|---|
| `scope` | ubuntu | `scripts/ci_scope.py` classifies the changed paths and publishes `code=true/false` and `prose=true/false` |
| `lint` | ubuntu | `ruff check .`, then `ruff format --check .`, then `python scripts/check_comments.py` (the no-comment rule), then the commit identity audit on a full-history checkout |
| `committer-guard` | ubuntu | `teamwork.py identity --guard-committer --range ...` on every push, naming a forge-stamped committer before it reaches `main` |
| `typecheck` | ubuntu | `mypy src/teamwork` with `continue-on-error: true` - a report, not a gate |
| `test` | 5 cells: ubuntu 3.11/3.12/3.13, macOS 3.13, Windows 3.13 | `pytest -q`, with the coverage gate on ubuntu 3.11 only |
| `build` | ubuntu | `make build` then `make verify` |
| `privacy` | ubuntu | `make privacy`; runs when `code` **or** `prose` is true |
| `release-consistency` | ubuntu | `check_release_consistency.py` offline: R1, R2, R6, R7 and R9 evaluate, R3/R4/R5/R8 print `SKIP` with the reason |
| `docs` | ubuntu | link health (`teamwork.py links`), then `mkdocs build --strict`; runs when `code` **or** `prose` is true |

`docs.yml` builds and deploys the site to GitHub Pages on `main`; `release.yml`
runs on `v*` tags and produces the wheel, sdist, checksums and SBOM.

### Why five cells, not eleven

The matrix used to run every supported interpreter on every OS. Dropping 3.9 and
3.10 (both end-of-life) and testing the newest interpreter on macOS and Windows
keeps the cross-platform signal while removing lanes that could only repeat it.
Durations are the last recorded runs, in minutes; they estimate the saving rather
than claim a measured wall time.

| Lane | Before | After |
|---|---:|---:|
| ubuntu 3.9 / 3.10 | 24 / 24 | - |
| ubuntu 3.11 | 22 | 22 |
| ubuntu 3.12 | 22 | 22 |
| ubuntu 3.13 | 23 | 23 |
| macOS 3.9 | 25 | - |
| macOS 3.11 | 18 | - |
| macOS 3.13 | 17 | 17 |
| Windows 3.9 | 32 | - |
| Windows 3.11 | 51 | - |
| Windows 3.13 | 40 | 40 |
| **Total** | **298** | **124** |

11 lanes to 5, and 298 to 124 runner-minutes: 174 minutes saved (58.4%). The
critical path is **Windows 3.13 at about 40 minutes**, still the long pole; the old
wall-clock bound was the Windows 3.11 lane at 51 minutes. The 3.12 and 3.13
interpreters stay on ubuntu, and the single coverage gate rides the ubuntu 3.11
lane.

## Reproduce a CI failure locally

1. Check out the same revision.
2. Run the target for the failing job, for example `make test`.
3. Fix, then re-run `make ci` before opening a PR.

The `test` job runs pytest like `make test`; only the ubuntu 3.11 lane adds the
coverage gate, so a coverage failure names that lane. A difference between local
and CI usually means a missing dependency or a platform-specific path.
