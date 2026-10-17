# RELEASE - build, ship, roll back

Owner: Release Engineer. The canonical answer to "how does this get built, shipped,
verified and reverted". Keep it executable: every command here must run as written.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Archive](Archive.md)

## Build

| step | command | expected result |
|---|---|---|
| clean checkout | `git clone https://github.com/Nidvue/Teamwork && cd Teamwork` | clean tree |
| dev setup | `make dev` | editable install with dev extras |
| selftest | `python3 scripts/teamwork.py selftest` | `5/5 checks passed`, exit 0 |
| build | `make build` | `dist/teamwork_agents-1.0.0.tar.gz` and `dist/teamwork_agents-1.0.0-py3-none-any.whl` |
| verify | `make verify` | wheel contains `teamwork/data/SKILL.md`; clean-venv install; `teamwork --version`, `teamwork selftest`, temp-dir `teamwork init` all pass |
| package | `python3 scripts/verify_release.py` | `SHA256SUMS` written next to the artefacts |
| provenance | GitHub Actions attestation (release workflow) | `gh attestation verify <file> --repo Nidvue/Teamwork` |

## CI gates

| gate | command | blocks a merge? |
|---|---|---|
| lint | `ruff check . && ruff format --check .` | yes |
| typecheck | `mypy src/teamwork` | no (report only for v1.0.0) |
| unit + integration | `pytest tests/unit tests/integration -q` | yes |
| acceptance | `pytest tests/acceptance -q` | yes |
| matrix | same tests on ubuntu/macos/windows x py3.9/3.11/3.13 | yes |
| build | `python -m build && python scripts/verify_release.py` | yes |
| privacy | `python3 scripts/privacy_scan.py --tree --history` | yes |
| docs | `mkdocs build --strict` | yes |

### Trigger policy - code in, prose and media out

A documentation or image-only change must not run the code matrix, and must not
be blocked by it. `ci.yml` therefore declares `paths-ignore` for the prose/media
set (`docs/**`, `*.md`, `LICENSE`, `CITATION.cff`, `assets/**`, `mkdocs.yml`,
`AGENTS.md`); every shipping path (`src/`, `scripts/`, `tests/`, `roles/`,
`references/`, `templates/`, packaging, `.github/workflows/`) still runs the full
matrix. `docs.yml` triggers on the ignored paths and runs the checks that still
matter for prose: `teamwork links`, `privacy_scan.py --tree --history` and
`mkdocs build --strict`.

| change touches | workflow | what runs |
|---|---|---|
| `src/**`, `scripts/**`, `tests/**`, packaging | CI | full matrix |
| `.github/workflows/**` | CI | full matrix |
| `roles/**`, `references/**`, `templates/**`, `SKILL.md` (shipped in the wheel) | CI | full matrix |
| `docs/**`, `*.md`, `LICENSE`, `CITATION.cff` | Docs | links + privacy + strict build |
| `assets/**` (images, banners, the social preview) | Docs | links + privacy + strict build |

`workflow_dispatch` stays enabled on both, so the full matrix can be forced on a
prose-only change when it is genuinely warranted.

## Deploy

- Environments: none. The artefact is a Python package; the "deployment" is a
  GitHub Release plus, optionally, a PyPI upload by the owner.
- Order of operations: `main` green -> CEO rewrites history for privacy -> CEO
  pushes `main` -> CI green -> CEO tags `v1.0.0` -> release workflow builds,
  signs, attests and publishes the release assets.
- Configuration and secrets *mechanism* (never values): PyPI publishing uses
  Trusted Publishing (OIDC) and is deliberately not enabled; no secret is stored
  in the repository. Only the owner's local `gh` credential is used to push.

## Rollback

- One command to return to the previous version for a user:
  `pip install "teamwork-agents==<previous>"` (or `git checkout v0.9.0`).
- To retract a bad release: `gh release delete v1.0.0 --yes` and re-tag after the
  fix (`git tag -d v1.0.0 && git push origin :v1.0.0`). Deleting a GitHub Release
  does not delete the git tag; both must be handled.
- What is *not* reversible: a force-push to `main` rewrites history for anyone who
  already cloned. The privacy rewrite is therefore done **before** the first
  public announcement and before any external clone exists.
- Last drill: `python3 scripts/verify_release.py` @ `710e68d` -> `OK - release
  verified` (build sdist+wheel, 38/38 bundle files in the wheel, clean-venv
  install, `--version`, `selftest`, `init` and the full gate loop to `STOP`),
  duration ~40 s; the CI `build` job runs the same command on every push.

## Observability

- Metrics: CI status on the default branch, release asset presence, `gh run list`
  conclusions, open issues and PRs.
- Alerts and their thresholds: a red CI run on `main` is a release blocker;
  `pytest` collection count dropping below 60 is a regression signal.
- Runbooks: this file; [Project](Project.md) for the acceptance criteria;
  [Architecture](Architecture.md) for the interface contract.

## Sources

- [Packaging Python projects - PyPA](https://packaging.python.org/en/latest/tutorials/packaging-projects/) - accessed 2026-10-17
- [GitHub Actions: building and testing Python](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python) - accessed 2026-10-17
- [Trusted publishing for PyPI](https://docs.pypi.org/trusted-publishers/) - accessed 2026-10-17
