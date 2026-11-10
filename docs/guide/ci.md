# CI pipeline - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [CLI reference](cli.md) · [Architecture](architecture.md)

The same pipeline runs in GitHub Actions and locally. Each step has a `make`
target; the underlying command is shown so it can be run without `make`.

## One-shot

```console
$ make ci
```

Runs lint, tests, build/verify, release consistency, privacy scan, docs build,
link check and the commit-identity audit in order, stopping at the first failure.
The target is `release-check`, and `make ci` is its alias - the same recipe, not
a superset. `make typecheck` is deliberately not in it: mypy is a report, not a
gate, in CI as well as locally.

## Steps and targets

| Target | Underlying command | What it proves |
|---|---|---|
| `make lint` | `ruff check .` + `ruff format --check .` | Style, import order and formatting. |
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

`scope` is the classifier the rest hang off. A pull request and a manual run
execute every job; a tag push runs the consistency gate alone, because the tagged
commit already passed the matrix as a `main` push. A push skips the matrix only
when every changed path is prose, and prose is exactly this set: `docs/`,
`assets/`, and these root files - `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
`SECURITY.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, `LICENSE`, `AGENTS.md`,
`mkdocs.yml`. There is no `*.md` wildcard. The `PROSE` pattern in `ci.yml` and
the `paths:` list of `docs.yml` must hold the same set, so this is the whole
story.

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
| `scope` | ubuntu | classifies the changed paths and publishes `code=true/false` |
| `lint` | ubuntu | `ruff check .`, then `ruff format --check .`, then the commit identity audit on a full-history checkout |
| `committer-guard` | ubuntu | `teamwork.py identity --guard-committer --range ...` on every push, naming a forge-stamped committer before it reaches `main` |
| `typecheck` | ubuntu | `mypy src/teamwork` with `continue-on-error: true` - a report, not a gate |
| `test` | ubuntu/macos/windows × Python 3.9/3.11/3.13, plus 3.10/3.12 on ubuntu | `make test` |
| `build` | ubuntu | `make build` then `make verify` |
| `privacy` | ubuntu | `make privacy` |
| `release-consistency` | ubuntu | `check_release_consistency.py` offline: R1, R2, R6, R7 and R9 evaluate, R3/R4/R5/R8 print `SKIP` with the reason |
| `docs` | ubuntu | link health (`teamwork.py links`), then `mkdocs build --strict` |

`docs.yml` builds and deploys the site to GitHub Pages on `main`; `release.yml`
runs on `v*` tags and produces the wheel, sdist, checksums and SBOM.

## Reproduce a CI failure locally

1. Check out the same revision.
2. Run the target for the failing job, for example `make test`.
3. Fix, then re-run `make ci` before opening a PR.

The `test` job uses the same command as `make test`; a difference between local
and CI usually means a missing dependency or a platform-specific path.
