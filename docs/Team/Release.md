# RELEASE - build, ship, roll back

Owner: Release Engineer. The canonical answer to "how does this get built, shipped,
verified and reverted". Keep it executable: every command here must run as written.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Archive](Archive.md) · [pi packaging](Pi-Packaging.md)

## Build

| step | command | expected result |
|---|---|---|
| clean checkout | `git clone https://github.com/Nidvue/Teamwork && cd Teamwork` | clean tree |
| dev setup | `make dev` | editable install with dev extras |
| selftest | `python3 scripts/teamwork.py selftest` | `5/5 checks passed`, exit 0 |
| build | `make build` | `dist/teamwork_agents-<version>.tar.gz` and `dist/teamwork_agents-<version>-py3-none-any.whl`, where `<version>` is what `python3 scripts/teamwork.py --version` prints (read it from `src/teamwork/version.py`; the filenames follow it and are never pinned here) |
| verify | `make verify` (runs `scripts/verify_release.py`) | every bundled skill file (`teamwork/data/SKILL.md`, roles, references, templates) is present in the wheel and the sdist, the wheel metadata declares no ungated `Requires-Dist`; clean-venv install; `teamwork --version`, `teamwork selftest`, the full gate loop to `STOP` and a temp-dir `teamwork init` all pass; `dist/SHA256SUMS` is written last, only after every check passed |
| pi package | `make package` | `dist/@nidvue/teamwork` pi bundle (built by `scripts/build_pi_package.py`) |
| provenance | GitHub Actions attestation (release workflow) | `gh attestation verify <file> --repo Nidvue/Teamwork` |

## CI gates

| gate | command | blocks a merge? |
|---|---|---|
| lint | `ruff check . && ruff format --check .` | yes |
| identity | `scripts/teamwork.py identity --audit --range <base>..HEAD` | yes (team-domain commits) |
| committer guard | `scripts/teamwork.py identity --guard-committer --range <before>..<head>` | yes |
| typecheck | `mypy src/teamwork` | no (`continue-on-error: true`, a report not a gate) |
| unit + integration | `pytest tests/unit tests/integration -q` | yes |
| acceptance | `pytest tests/acceptance -q` | yes |
| coverage | `pytest --cov=teamwork --cov-fail-under=55` | yes, as part of `test` |
| matrix | ubuntu/macos/windows x py3.9/3.11/3.13, plus py3.10/3.12 on ubuntu | yes |
| build | `python -m build && python scripts/verify_release.py` | yes |
| privacy | `python3 scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` | yes |
| docs | `teamwork links` + `mkdocs build --strict` (in `docs.yml`) | yes |
| release consistency | `python scripts/check_release_consistency.py --offline` (the `release-consistency` job in `ci.yml`) | yes (a registered required check) |
| release consistency (online) | `python scripts/check_release_consistency.py --online` (the `consistency` job in `release.yml`, which lands with task T-0007) | yes (on a `v*` tag) |

The `release consistency (offline - docs + tags + version)` context **is
registered** in the branch protection of `main` (16 contexts, `strict=true`).
It must not be *blocking* until `scripts/check_release_consistency.py` and
`release-exceptions.json` are merged (developer task **T-0005**): without the
checker the job cannot run and exits 2, so a merge to `main` would be blocked
by a check that has nothing to run. The same landing must carry the R6/R8/R9
prose repairs (CEO task **T-0061**), because `main` is red on those rules
today. The CEO owns that sequencing; the gate itself is not softened to
compensate.

The consistency gate runs twice on purpose. In `ci.yml` it runs **offline**: R1,
R2, R6, R7 and R9 evaluate from the tree and the tags, and R3/R4/R5/R8 print
`SKIP` with the reason, because the npm registry, the GitHub API and PyPI need
credentials and rate-limit headroom that do not belong in every pull request.
The **online** half - the same checker with `--online` - lands with the release
task **T-0007**; it is not in `release.yml` on `main` today, so R3/R4/R5 are
still permanently `SKIP` in every automated run until that task lands.

## Release candidate gate

The gate is measured on a revision that is reachable from the default branch - never
on a detached head or a discarded amend, because such a revision can never ship. The
table carries no pinned revision: it is a description of what each gate must print,
and the revision it applies to is always the head you are about to tag -
`git rev-parse --short HEAD` (equivalently `git log --oneline -1`). Re-run every row
on that head before a tag and read each result from the command, never from this page.

| gate | command | what a passing result prints |
|---|---|---|
| build | `python -m build && python scripts/verify_release.py` | `verify_release: OK - release verified` and `wrote dist/SHA256SUMS`; the two digests in that file are the values to record |
| selftest | `python3 scripts/teamwork.py selftest` | `teamwork selftest: 5/5 checks passed`, exit 0 |
| unit + integration + acceptance | `pytest -q` | every test passes; the only legitimate skips are the console-script check (covered by `verify_release.py`) and the two that need the gitignored team tree, so read the skip reasons rather than a count |
| lint + format | `ruff check . && ruff format --check .` | `All checks passed!`; `... files already formatted` |
| typecheck | `mypy src/teamwork` | `Success: no issues found` |
| privacy | `privacy_scan.py --tree --history --allow .github/privacy-allow.txt` | `PASS - 0 finding(s) in tree, history`, exit 0 |
| docs | `teamwork links` + `mkdocs build --strict` | `# issues: 0`; the strict build finishes without a warning |
| identity | `teamwork identity --audit --range origin/main..main` | `# commits: 0 | problems: 0` on a clean push, and `problems: 0` otherwise |
| code scanning | `teamwork code-scanning` | `- no open alert`. Any open `error`/`critical`/`high` alert is a red gate and is filed to the role that owns the file, never dismissed (`D-20261020-SEC-1`, below) |

The privacy row is quoted with `--allow` because that is what CI and `make privacy`
run. The allowlist exempts two quoted path families (the pi install tree and one
operator user name) and three fabricated probe values a reviewer quoted as evidence;
every pattern rule still fires on the same line.

The code-scanning row no longer quotes a triage. `D-20261020-SEC-1` originally
triaged alerts #2 and #3 (`py/clear-text-logging-sensitive-data` on
`scripts/privacy_scan.py`) as false positives; the reporting path was then refactored
instead (`2e7810f`, T-0053: the raw value lives on the `Finding` object as an
attribute, never as an item, and every sink names the rule, not the value). The forge
reports all three alerts as `fixed`, not `dismissed`, so `teamwork code-scanning`
prints `- no open alert`. The decision stays in [Decisions](Decisions.md) as the record
of that triage; it is not the current answer.

### Trigger policy - code in, prose and media out

On a **push to `main`**, a documentation or image-only change must not run the
code matrix. `ci.yml` has **no `paths-ignore`**: the workflow always fires on
`main`, on a `v*` tag and on every pull request, and a `scope` job classifies
the changed paths. The prose/media set is: `docs/**`, the root prose files
(`README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
`CODE_OF_CONDUCT.md`, `AGENTS.md`), `LICENSE`, `CITATION.cff`, `assets/**` and
`mkdocs.yml`. A push that touches nothing outside that set skips the code jobs;
every shipping path (`src/`, `scripts/`, `tests/`, `roles/`, `references/`,
`templates/`, packaging, `.github/workflows/`, `SKILL.md`) still runs the full
matrix.

`paths-ignore` was removed because it was the wrong tool: a workflow-level
ignore skips **every** job in the file, including the `release-consistency`
gate, whose whole subject is prose that disagrees with a tag, `version.py` or
`CHANGELOG.md`. A gate skipped exactly when the documentation drifts is
worthless. The `scope` job replaces it: the cheap jobs skip, the gate does
not. `docs.yml` still triggers on the same prose/media set (`paths:`) and runs
the checks that matter for prose: `teamwork links`,
`privacy_scan.py --tree --history` and `mkdocs build --strict`. The `scope`
prose set and that workflow's `paths:` list must stay identical.

The `scope` job measures the change set from `github.event.before` to
`github.sha`. When `before` is unusable - the all-zero sha of a first push, or
a sha that no longer exists after a rewritten history - the change set is
measured from the merge base with the default branch instead. When even that
base is **not behind** HEAD the change set is **undetermined**, and the code
jobs **run**: an unknown change set must never silently skip the matrix. The
only case with a determinate change set and no usable base is a **root
commit** (HEAD has no parent): every file it carries is the change set, and it
is listed with `git diff-tree --root`. Every change set is measured with
`--no-renames`, so a rename is seen as a delete plus an add and **both** paths
are classified. Without it, rename detection reports only the *destination*:
a push that moved `src/teamwork/foo.py` to `docs/foo.md` would list only the
prose path, be classified as prose, and skip the matrix on a change that
removed shipping code. A push whose remote already holds HEAD
- which is the normal state after a push, because `origin/main` then points at
the pushed SHA - is therefore *undetermined*, not "prose only", and the matrix
runs.

On a **pull request both workflows always run**, regardless of paths: branch
protection requires every check to be *reported* on the head (read the list with
`gh api repos/Nidvue/Teamwork/branches/main/protection --jq
'.required_status_checks.contexts[]'`), and a path-filtered skip reports nothing, so a
docs-only PR would wait forever. The path filter is a push-time cost optimisation, not
a merge gate. Evidence: PR #16 (docs only) ran CI and Docs on its head `0e00001`, both
success; the Docs-only push `39175948257` ran only Docs, success.

| change touches | on push to `main` | on a PR |
|---|---|---|
| `src/**`, `scripts/**`, `tests/**`, packaging | CI full matrix | CI + Docs |
| `.github/workflows/**` | CI full matrix | CI + Docs |
| `roles/**`, `references/**`, `templates/**`, `SKILL.md` (shipped in the wheel) | CI full matrix | CI + Docs |
| `docs/**`, root prose files, `LICENSE`, `CITATION.cff` | scope skips the code jobs; the consistency gate and Docs still run | CI + Docs |
| a rename **out of** a shipping path (e.g. `src/**` -> `docs/**`) | scope sees both paths (`--no-renames`): the code jobs run | CI + Docs |
| `assets/**` (images, banners, the social preview) | scope skips the code jobs; the consistency gate and Docs still run | CI + Docs |

`workflow_dispatch` stays enabled on both, so the full matrix can be forced on a
prose-only change when it is genuinely warranted.

A **tag push** (`v*`) runs the `release-consistency` gate and the tag-sensitive
checks; the tagged commit already passed the matrix as a `main` push, and
`release.yml` re-runs pytest on the tag. R2 itself applies the tag set frozen
in `docs/Team/Architecture.md` section 11.2.2 (`S = A - O`: the version tags
reachable from HEAD, minus the tags that point at HEAD), so the tag a build
publishes is never compared with itself. The **checker** computes that set;
the workflow does not re-implement the rule, and it does not parse the
checker's findings to soften them. Every other finding - a genuine drift, an
unreadable input - still fails the job.

### The gate's exit codes

| situation | exit | what the job prints |
|---|---|---|
| the checker is not in the tree | 2 | `the release consistency checker is not in the tree (scripts/check_release_consistency.py is absent), so the gate cannot run` |
| a rule drifted (R2, R6, R7, R8, R9) | 1 | `::error::<RULE> DRIFT: <detail>` per finding, then `# release consistency: N problem(s)` |
| an input the gate reads could not be read | 2 | `::error::an input the gate reads could not be read (checker exit 2)` |
| everything agrees | 0 | one line per rule, `# release consistency: 0 problem(s)` |

A missing checker is an **unreadable input**, not a skip: the gate fails with
exit 2 and says plainly that the checker is absent. It is never downgraded to
a pass.

## Remote merge policy (2026-10-19)

- Existing reviewed merge commits stay on `main`; they are not rewritten.
- Every future change: branch -> push the branch -> open a GitHub PR -> all
  required checks green on the PR head -> **integrate locally with the role
  identity** -> push `main` -> delete the branch.
- Do **not** use any GitHub merge button. Every host button stamps the signed-in
  account into the commit it creates - squash as the author, rebase as the
  committer - and that fails the privacy gate on history. Since 2026-10-20 the forge
  has squash and merge commits *off* and rebase on (`gh api repos/Nidvue/Teamwork` ->
  `allow_squash_merge=false`, `allow_merge_commit=false`, `allow_rebase_merge=true`,
  `delete_branch_on_merge=true`); the host also needs one method enabled, so the
  guard, not the setting, is what protects `main`.
- Locally: `git merge --squash <branch>` and commit as the acting role, or
  `teamwork.py pr merge --squash`, which does exactly that as the Reviewer mailbox.
- `main` keeps: 1 required approval, 16 required checks (the release-consistency
  context was added to the 15 before it), strict up-to-date, no force-push, no
  deletion, `required_linear_history` disabled so the existing merge commits do not
  need an admin bypass. The required check list is measured, not quoted; the
  committer guard (`identity --guard-committer`) reports a stamped account on the
  push, and `identity --audit` accepts a forge rebase committer
  (`noreply@github.com`) only when the author is a canonical role mailbox.

## Deploy

- Environments: none for the package. The artefact is a Python package; the
  "deployment" is a GitHub Release. `teamwork-agents` is **not on PyPI** (measured:
  `https://pypi.org/pypi/teamwork-agents/json` -> `404`, `pip index versions
  teamwork-agents` -> `No matching distribution found`), so the release asset is the
  only install source and a user needs no index at all:
  `pip install https://github.com/Nidvue/Teamwork/releases/download/<tag>/teamwork_agents-<version>-py3-none-any.whl`.
- Order of operations: `main` green -> push `main` -> CI green on that SHA ->
  CEO tags `v<version>` -> the Release workflow asserts the tag equals
  `src/teamwork/version.py`, re-runs the tests, builds sdist+wheel, writes
  `SHA256SUMS` and two SBOMs, **attests** build provenance and publishes the GitHub
  Release. It does not sign: provenance is the sigstore attestation, verified with
  `gh attestation verify <file> --repo Nidvue/Teamwork` (measured on the published
  `v1.1.0` wheel -> pass, workflow ref `release.yml@refs/tags/v1.1.0`). History
  rewrites are not part of the flow; the pre-release privacy rewrite already happened
  before the first public tag.
- Configuration and secrets *mechanism* (never values): no publish credential exists at
  all. There is no PyPI job in any workflow and no secret in the repository; Trusted
  Publishing (OIDC) would be the mechanism if a PyPI upload were ever enabled. Only the
  operator's local `gh` credential pushes.

## Rollback

- Reverting a user to an earlier version needs no index: install the asset of the
  tag you want. List the tags first - never copy a literal from this page, a released
  tag cannot be re-pointed:
  `git tag -l --sort=-v:refname` -> newest first; `git tag -l --sort=-v:refname | sed -n 2p`
  is the previous one. Then
  `pip install https://github.com/Nidvue/Teamwork/releases/download/<tag>/teamwork_agents-${tag#v}-py3-none-any.whl`.
- Drill (measured 2026-10-20), the recorded rollback transcript:

  <!-- release-consistency: illustrative -->
  ```
  previous tag `v1.0.2` -> wheel installed into a clean
  venv -> `teamwork --version` `teamwork 1.0.2`, `teamwork selftest: 5/5 checks
  passed`
  ```

  Rolling *back* is therefore one command and needs no checkout.
- To retract a bad release: `gh release delete <tag> --yes`, then re-tag after the fix
  (`git tag -d <tag> && git push origin :<tag>`). Deleting a GitHub Release does not
  delete the git tag; both must be handled. Moving or re-pointing a *published* tag is
  a red line - publish a new patch version instead.
- What is *not* reversible: a force-push to `main` rewrites history for anyone who
  already cloned. The privacy rewrite is therefore done **before** the first public
  announcement and before any external clone exists.
- Last release drill: `python3 scripts/verify_release.py` at head `f277ac7` ->
  `verify_release: OK - release verified`, `wrote dist/SHA256SUMS`, 5.7 s (build
  sdist+wheel, every bundled skill file present in both, no ungated `Requires-Dist`,
  clean-venv install, `--version`, `selftest`, the full gate loop to `STOP`, and
  `init`). The CI `build` job runs the same command on every push, and the Release
  workflow runs it on every tag.

## Observability

- Metrics: CI status on the default branch, release asset presence, `gh run list`
  conclusions, open issues and PRs, `teamwork code-scanning`.
- Alerts and their thresholds - read each from its file, never from this page:
  - a red CI run on `main`, on the SHA that is deployed, is a release blocker;
  - coverage below the floor in `.github/workflows/ci.yml` (`--cov-fail-under=55`,
    mirrored by `fail_under = 55` in `pyproject.toml`) fails the `test` job;
  - an open `error`/`critical`/`high` code-scanning alert is a red gate and is filed
    to the role that owns the file;
  - a test that collects as an *error*, or a skipped test whose reason is not one of
    the two known ones (console script not installed; gitignored team tree absent),
    is the regression signal - a collection census is deliberately not quoted, because
    a count in a document is stale before the document is committed.
- Runbooks: this file; [Project](Project.md) for the acceptance criteria;
  [Architecture](Architecture.md) for the interface contract.

## Sources

- [Packaging Python projects - PyPA](https://packaging.python.org/en/latest/tutorials/packaging-projects/) - accessed 2026-10-17
- [GitHub Actions: building and testing Python](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python) - accessed 2026-10-17
- [Trusted publishing for PyPI](https://docs.pypi.org/trusted-publishers/) - accessed 2026-10-17
