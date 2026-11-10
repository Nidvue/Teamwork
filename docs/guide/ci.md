# CI pipeline - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [CLI reference](cli.md) · [Architecture](architecture.md)

The same pipeline runs in GitHub Actions and locally. Each step has a `make`
target; the underlying command is shown so it can be run without `make`.

## One-shot

```console
$ make ci
```

Runs lint, type-check, tests, build, privacy scan, docs build and link check in
order, stopping at the first failure.

## Steps and targets

| Target | Underlying command | What it proves |
|---|---|---|
| `make lint` | `ruff check .` | Style and import order. |
| `make typecheck` | `mypy src/teamwork` | Type report (non-blocking in CI). |
| `make test` | `pytest -q` | Unit, integration and acceptance tests. |
| `make build` | `python -m build` | An sdist and a wheel are produced. |
| `make verify` | `python scripts/verify_release.py` | The wheel bundles the skill and installs cleanly. |
| `make privacy` | `python scripts/privacy_scan.py --history` | No personal data, credentials, agent-host configuration or local state in the tree, the index or the history. |
| `make docs` | `python -m mkdocs build --strict` | The docs site builds with no warnings. |
| `make links` | `python scripts/teamwork.py links` | No broken links, bare URLs or missing back-links. |
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

The `dev` extra installs `pytest`, `ruff` and `mypy`; `docs/requirements.txt`
installs `mkdocs-material`.

## What CI runs

`.github/workflows/ci.yml` runs the jobs below; each maps to a `make` target:

| Job | Matrix | Step |
|---|---|---|
| `lint` | ubuntu | `make lint` |
| `typecheck` | ubuntu | `make typecheck` (non-blocking report) |
| `test` | ubuntu/macos/windows × Python 3.9/3.11/3.13 | `make test` |
| `build` | ubuntu | `make build` then `make verify` |
| `privacy` | ubuntu | `make privacy` |
| `docs` | ubuntu | `make docs` |

`docs.yml` builds and deploys the site to GitHub Pages on `main`; `release.yml`
runs on `v*` tags and produces the wheel, sdist, checksums and SBOM.

## Reproduce a CI failure locally

1. Check out the same revision.
2. Run the target for the failing job, for example `make test`.
3. Fix, then re-run `make ci` before opening a PR.

The `test` job uses the same command as `make test`; a difference between local
and CI usually means a missing dependency or a platform-specific path.
