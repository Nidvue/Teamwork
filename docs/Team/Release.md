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
| verify | `make verify` (runs `scripts/verify_release.py`) | every bundled skill file (`teamwork/data/SKILL.md`, roles, references, templates) is present in the wheel and the sdist, the wheel metadata declares no ungated `Requires-Dist`; clean-venv install; `teamwork --version`, `teamwork selftest`, the full gate loop to `STOP` and a temp-dir `teamwork init` all pass; `dist/SHA256SUMS` is written last, only after every check passed (in the Release workflow the `build` job then *extends* that one file over the artefacts and both SBOMs - see [Release assets](#release-assets-one-manifest-one-name)) |
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
| release consistency (online) | `python scripts/check_release_consistency.py --online` (the `consistency` job in `release.yml`) | yes (on a `v*` tag) |

The `release consistency (offline - docs + tags + version)` context **is
registered** in the branch protection of `main` - measured, not quoted:
`gh api repos/Nidvue/Teamwork/branches/main/protection --jq
'.required_status_checks.contexts|length'` prints `20`, with `strict=true`. The four
newest are the `test (ubuntu-latest / py3.10)` and `test (ubuntu-latest / py3.12)`
lanes and the two CodeQL contexts `Analyze (python)` and `Analyze (actions)`; read the
list, never this number.
It can only be *blocking* when the gate can actually run, and that is a
re-runnable condition, not a date:

- the checker and its exception file must be in the tree -
  `git ls-tree HEAD scripts/check_release_consistency.py release-exceptions.json`
  prints one line for each. Without the checker the job cannot run and exits
  2, so a merge to `main` would be blocked by a check that has nothing to run.
- the gate must be green - `python3 scripts/check_release_consistency.py --offline`
  prints `# release consistency: 0 problem(s)` and exits 0. A red gate is
  repaired, never softened; the gate is not weakened with `|| true` or
  `continue-on-error` to let a merge through.

Read those two commands instead of trusting a sentence about what has landed.

The consistency gate runs twice on purpose. In `ci.yml` it runs **offline**: R1,
R2, R6, R7 and R9 evaluate from the tree and the tags, and R3/R4/R5/R8 print
`SKIP` with the reason, because the npm registry, the GitHub API and PyPI need
credentials and rate-limit headroom that do not belong in every pull request.
The **online** half - the same checker with `--online` - runs in
`.github/workflows/release.yml`, in the `consistency` job named `release
consistency gate (online, before anything is published)`, before anything is
published; `git grep -c 'release consistency gate (online, before anything is
published)' .github/workflows/release.yml` prints `1`. R3/R4/R5 therefore
evaluate there, where the registry credentials and the rate-limit headroom are
available, and print `SKIP` only in the offline runs of `ci.yml`.

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
- `main` keeps: 1 required approval, 20 required checks (the release-consistency
  context was added to the 15 before it, then the ubuntu `py3.10` and `py3.12` lanes and
  the `Analyze (python)` / `Analyze (actions)` contexts brought it to 20), strict
  up-to-date, no force-push, no deletion, `required_linear_history` disabled so the
  existing merge commits do not need an admin bypass. The required check list is
  measured, not quoted; the committer guard (`identity --guard-committer`) reports a
  stamped account on the push, and `identity --audit` accepts a forge rebase committer
  (`noreply@github.com`) only when the author is a canonical role mailbox.
- `enforce_admins` is `false` and the repository has **one** collaborator with admin
  (`gh api repos/Nidvue/Teamwork/collaborators`). That is the single-owner caveat
  `references/Remotes.md` asks to be stated here: `required_approving_review_count=1`
  cannot be satisfied by the only account, so the admin bypass is the escape, and a
  local merge pushed straight to `main` does not wait for the protection rules at
  all. The push path is guarded by the checks that run **on the push** - `committer
  guard`, `privacy scan`, `release consistency` - and by the Reviewer's verdict; the
  required checks block the host-PR path. Every bypass is a governance event: who,
  when, which revision, and why the Reviewer verdict stands in for the host approval.
  A second account with review rights is the preferred fix and removes the bypass.
- Measured state, and what is still unprotected: the **Integrity drift check**
  section below.

### What the identity audit accepts, and why (T-0010)

`identity --audit --range origin/main..main` on the unpublished line reported 16
problems that the team's own merge policy produces, so the gate was red on a clean
policy-conforming history. The four cases below are now accepted by
`audit_commit_identities` (`src/teamwork/engine.py`); each is proved by a named test
in `tests/unit/test_commit_identity.py`. See [Architecture](Architecture.md#11-release-consistency-contract)
for the contract this gate belongs to.

| # | Case | Decision | Reason |
|---|---|---|---|
| 1 | `committer differs from author` where the committer is a **canonical role mailbox** (`ROLE_DISPLAY` -> `role_identity`, e.g. `Reviewer <reviewer@agents.nidvue.com>`) | **accepted**, and the output still prints `(landed by <role>)` | A lane landing a peer's reviewed work commits as its own role mailbox: that *is* the local merge policy. A committer that is not a role mailbox (a personal address) and differs from the author stays a **FAIL**. |
| 2 | missing `Acting role:` line while the body carries `Role: <role>` | **accepted** as equivalent, provided the `Role:` value resolves to the author's own role | `build_commit_message` (`engine.py:3460-3484`) writes *both* trailers; a commit produced by the tool is never missing the acting role. A commit with neither line stays a **FAIL**, and a `Role:` naming another role stays a **FAIL**. |
| 3 | a **two-parent** `chore(merge): ...` commit with an **empty body** | **exempt** from the acting-role line | It adds no content of its own, so there is no acting role to name (measured: `f5ef807`, parents `bdcc588`+`93f6f4b`, empty body, Reviewer committer). |
| 4 | a **single-parent** `chore(merge)` commit with an empty body | **not exempt** - still a **FAIL** | A squash/fast-forward commit *does* add content, so the exemption above must stay discriminable from it. |

Re-stamping the existing history was refused: it rewrites every descendant sha, and
`docs/Team/Archive.md` pins each landed PR's merge revision.

## Integrity drift check (2026-10-25)

The pipeline is read, not assumed. Each row is a command and its result on `main` at
`7db810a`. Re-run them; a drift is fixed in the same change-set, or filed as a task and
named here with its id - never left silently unprotected.

### 1. The `scope` prose set and the `docs.yml` `paths:` list are one list

| reading | value |
|---|---|
| `ci.yml` `PROSE=` | `docs/`, `assets/`, `README.md$`, `CHANGELOG.md$`, `CONTRIBUTING.md$`, `SECURITY.md$`, `CODE_OF_CONDUCT.md$`, `CITATION.cff$`, `LICENSE$`, `AGENTS.md$`, `mkdocs.yml$` |
| `docs.yml` `paths:` | `docs/**`, `assets/**`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, `LICENSE`, `AGENTS.md`, `mkdocs.yml` |
| as path sets | identical - 11 members, `scope`-only `[]`, `paths`-only `[]` |
| 13 probe paths through both (5 prose + 8 code) | 0 disagreements: `docs/x`, `assets/`, `README.md`, `LICENSE`, `mkdocs.yml` are prose in both; `README.md.bak`, `docsx/a.md`, `assetsfoo/x.png`, `SKILL.md`, `NOTICE`, `release-exceptions.json`, `src/teamwork/cli.py`, `.github/workflows/ci.yml` are code in both |

The `$` anchors are load-bearing: the file members are exact names, so `README.md.bak` is
code, not prose. Of the 17 tracked root files (`git ls-files | awk -F/ 'NF==1'`), 9 are
list members - `AGENTS.md`, `CHANGELOG.md`, `CITATION.cff`, `CODE_OF_CONDUCT.md`,
`CONTRIBUTING.md`, `LICENSE`, `README.md`, `SECURITY.md`, `mkdocs.yml` - and the other 8
are matched by neither list: `.editorconfig`, `.gitattributes`, `.gitignore`, `Makefile`,
`NOTICE`, `SKILL.md`, `pyproject.toml`, `release-exceptions.json`. `NOTICE` is therefore
not the only one; it carries no link and no site page, `ci.yml`'s privacy job still scans
it on every code push, and an unclassified path falls towards *running* the matrix, never
towards skipping it.

### 2. Every command a workflow runs exists in this tree

0 missing over `ci.yml` (19 `run` blocks), `docs.yml` (4) and `release.yml` (8). Every
path they name exists - `scripts/teamwork.py`, `scripts/privacy_scan.py`,
`scripts/verify_release.py`, `scripts/check_release_consistency.py`,
`.github/privacy-allow.txt`, `docs/requirements.txt`, `tests/{unit,integration,acceptance}`
- and every flag is in the script's own `--help` (`privacy_scan.py --tree --history
--allow`, `check_release_consistency.py --offline|--online --json`,
`teamwork.py identity --audit|--guard-committer --range`, `teamwork.py links`).
`pytest`, `build` and `mkdocs` come from `.[dev]` (`pytest>=8,<10`, `pytest-cov>=5,<8`,
`build>=1.2,<2`) and `docs/requirements.txt` (`mkdocs-material>=9.7.7,<10`). No workflow
invokes `make`, and every target named on this page exists in the `Makefile`.

One reproducibility defect sits in that job list: the `lint` job installs ruff with
`python -m pip install --upgrade ruff` (`ci.yml:192`), ignoring the project's own
`ruff>=0.9,<0.18` pin (`pyproject.toml:45`). The newest ruff on PyPI on 2026-10-25 is
0.17.2, inside the range, so the required check is correct today and leaves the pin the
day 0.18.0 ships - on a revision that changed nothing. Filed: `release-engineer` T-0002.

### 3. Actions are pinned, and no deprecation is pending

Every `uses:` in the three workflows is a 40-hex SHA - 10 distinct pins, each resolving
to a real commit (`gh api repos/<owner>/<repo>/commits/<sha>`), and 9 of the 10 equal the
commit their file comment names (`gh api repos/<owner>/<repo>/git/ref/tags/<v>`, which
needs the tag object dereferenced for `attest-build-provenance`). The one that lags is
`actions/setup-python@v7`: pinned `5fda3b95` (2026-07-20), tag tip `6d4fd22b`
(2026-10-22), and no update is queued (`gh pr list --state open` -> empty) although
`.github/dependabot.yml` watches `github-actions` weekly. A frozen pin is what pinning
means; it is recorded so the next drift check sees it move.

Annotations on the last five runs (`gh run list -L 5 --json databaseId,conclusion,headSha`
then `gh api repos/Nidvue/Teamwork/check-runs/<id>/annotations`) carry **one** `notice`
and no warning or error: "the ubuntu-latest label will migrate to Ubuntu 26 beginning
October 19, 2026"
([actions/runner-images#14748](https://github.com/actions/runner-images/issues/14748),
accessed 2026-10-25). No deprecated action, no deprecated runner expression, no
`ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION` anywhere in the three files. That date has
already passed, and the newest green ubuntu lanes ran 2026-10-22 - read the first ubuntu
run after it. A SHA pin is runner-image independent, so no `uses:` changes for it.

Two CI runs failed on 2026-10-21 (`9b82f84`, `4be25e8`) and they are not one defect class.
`9b82f84` had three failing `windows-latest` lanes - a payload-digest assertion and
`test_dry_run_prints_without_executing`, i.e. test defects, not runner deprecations.
`4be25e8` had **four** failing checks: those same three `windows-latest` lanes (`py3.9`,
`py3.11`, `py3.13`) plus `committer guard (no account stamped into main)` in the `CI`
workflow - run `39662780079`, job `119439857709`, failing step "Guard the committer of the
pushed revision" - i.e. an identity-gate failure, not a test defect. Recorded separately on
purpose: folding it into "three test lanes" would hide a gate class from this drift record.
All 11 lanes are green again at `67df036`.

### 4. The forge still matches `references/Remotes.md`

Measured 2026-10-25, re-measured 2026-10-26 after the forge hardening (`ceo` T-0010), with
`gh api repos/Nidvue/Teamwork/branches/main/protection`, `gh api
repos/Nidvue/Teamwork`, `gh api repos/Nidvue/Teamwork/actions/permissions`,
`.../actions/permissions/workflow`, `gh api repos/Nidvue/Teamwork/rulesets`,
`gh api repos/Nidvue/Teamwork/rulesets/<id>` and `gh api
repos/Nidvue/Teamwork/tags/protection`:

| policy | measured | verdict |
|---|---|---|
| no force-push | `allow_force_pushes.enabled=false` | ok |
| no branch deletion | `allow_deletions.enabled=false` | ok |
| required checks, strict | `strict=true`, 20 contexts | ok |
| >= 1 non-author approval, stale dismissed | `required_approving_review_count=1`, `dismiss_stale_reviews=true`, `require_last_push_approval=false` | ok - last-push approval is not a policy rule |
| the whole matrix is required | all 11 `test` lanes are contexts, including the two `include:` lanes `test (ubuntu-latest / py3.10)` and `test (ubuntu-latest / py3.12)`, and the two CodeQL contexts `Analyze (python)` / `Analyze (actions)` block a merge as well | ok - closed by `ceo` T-0010; the lanes run *and* block |
| no merge commits on the default branch | `required_linear_history.enabled=false` | **drift**, rationale only in this page -> `ceo` T-0005 |
| one canonical merge shape, host buttons off | `allow_squash_merge=false`, `allow_merge_commit=false`, `allow_rebase_merge=true`, `delete_branch_on_merge=true` | ok - the `references/Remotes.md` rebase-only variant; the host stamps the signed-in account and the required `committer guard` catches it |
| admin bypass only as a recorded event | `enforce_admins.enabled=false`, one admin collaborator | ok with the caveat stated above |
| protected `v*` tag, CEO only | one active ruleset `protect v* release tags` (id `25840176`, `target=tag`, condition `refs/tags/v*`, rules `deletion` + `non_fast_forward` + `update`, `bypass_actors -> []`, `current_user_can_bypass=never`); `tags/protection -> HTTP 404` is the retired endpoint the ruleset replaces | ok - closed by `ceo` T-0010 |
| least-privilege CI | `default_workflow_permissions=read`, `can_approve_pull_request_reviews=false`; `allowed_actions=all`, `sha_pinning_required=true`, and `grep -ho 'uses: *[^ ]*' .github/workflows/*.yml \| sed 's/uses: *//' \| sort -u` -> 10 distinct actions, every one a 40-hex SHA (0 tag refs) | ok - the forge enforces the pinning the tree already has, closed by `ceo` T-0010 |
| code scanning as a gate | CodeQL default setup `configured` (`actions`, `python`) and both `Analyze (python)` and `Analyze (actions)` are required contexts | ok - closed by `ceo` T-0010 |

### 5. The hooks refuse a plain commit

In a throwaway clone under this worktree's `Scratch/` (`git clone --shared` ->
`Scratch/clone`, never the repository itself), on `main` at `7db810a`:

| command | result |
|---|---|
| `teamwork.py hooks status` | `pre-commit absent`, `pre-push absent` |
| `teamwork.py hooks install` | `pre-commit installed`, `pre-push installed` |
| `echo x >> README.md && git commit -am ...` on `main`, personal identity | **refused, exit 1**: `teamwork: refusing to commit on 'main': it only receives merges performed by the Reviewer.`; `git log` still `7db810a` |
| the same commit on a new branch | accepted, exit 0, plus `teamwork: warning: commit identity ... is not a role mailbox` |

The branch rule blocks; the identity rule warns by design - `check_commit` in
`src/teamwork/hooks.py` is documented as "R1 default branch, R2 large non-LFS blob, R3
identity (a warning, never a block)". Identity is enforced on the push instead, by the
required `committer guard` and the `identity --audit` step in the `lint` job.

### 6. Release truth: `v1.3.0` - any role scales, one holds the memory pen

| fact | command | value |
|---|---|---|
| the version the package claims | `grep __version__ src/teamwork/version.py` | `1.4.0` - the unreleased tree; the record below describes the tag before it |
| the newest tag | `git tag --sort=-v:refname \| head -1` | read it from the command, never here: after the first landing past a tag every older version is stale prose under R6, so this row names no tag at all. The admitted exception is listed in `release-exceptions.json` |
| the tag on the released head | `git rev-parse v1.3.0^{commit}` | `df97067`; `git tag --points-at HEAD` is empty because the tree carries the next change-set |
| `CHANGELOG.md` | `grep -n '^## \[1.3.0\]' CHANGELOG.md` | read the line from the command: it moves whenever a section is added above it. The section is dated 2026-10-28 with the compare link `v1.2.1...v1.3.0`, and the unreleased 1.4.0 section sits above it |
| the offline gate | `python scripts/check_release_consistency.py --offline` | exit 0, `# release consistency: 0 problem(s)` |
| the online gate | `python scripts/check_release_consistency.py --online` | exit 0 on the tagged revision (R3/R4/R5/R8 read the registry and the forge) |
| the CI/release record | `gh run list --workflow Release` on the pushed tag | the run id and conclusions on that SHA are the post-push record |

`1.3.0` is cut from reviewed `main` and adds three things: **any role** can run
several instances (`instance add|list|retire`) against one shared
`Roles/<Role>/` memory, **one instance at a time revises that memory**
(`memory claim|release|renew|status`, `Runtime/Locks/memory-<Role>.claim`), and a
lease that runs long is **contested by a peer and ruled by the CTO**
(`memory contest|extend|revoke`; the arbiter folds to the CEO when the CTO is
unstaffed, and a party never rules its own lease). No protocol gate changed. The
tag push runs `release.yml`'s online consistency gate, the test matrix,
build/attest and the GitHub Release.

Rollback needs no index: install the wheel asset of the tag you want.

### Open drift

| # | drift | owner / task |
|---|---|---|
| 1 | the R8 marker is missing at `docs/Team/Decisions.md:1284` - blocks every release | `ceo` T-0004 |
| 2 | `required_linear_history=false`, rationale not in `Decisions.md` | `ceo` T-0005 |
| 3 | the lint job installs an unpinned ruff | `release-engineer` T-0002 |

The three forge drifts this table used to carry - the two matrix lanes that ran without
blocking, the unprotected `v*` tag and the CodeQL/SHA-pinning pair - are closed by `ceo`
T-0010 and measured in section 4 above, not restated here. Items 1-2 are not changed by
this document: a branch-protection change is a forge governance event and belongs to the
CEO. Item 3 is this lane's own file and is scheduled, not silently reverted.

## Release assets: one manifest, one name

A published Release carries exactly **one** asset per name. The build job writes
one manifest, `dist/SHA256SUMS`, extended over every asset it publishes, and the
`files:`, `subject-path:` and `path:` lists all draw from it - never a second
file with the same basename.

| asset | written by | published as |
|---|---|---|
| `teamwork_agents-<version>.tar.gz`, `…-py3-none-any.whl` | `scripts/verify_release.py` (`python -m build`) | `dist/*` |
| `SHA256SUMS` | the last step of the `build` job, over the two artefacts and both SBOMs | `dist/*` (it lives in `dist/` and nowhere else) |
| `sbom.cyclonedx.json`, `sbom.spdx.json` | `anchore/sbom-action` | their own `path:` entries at the repository root |

The manifest lists bare asset names, because the Release flattens the asset set:
a user who downloaded everything into one directory runs `sha256sum -c SHA256SUMS`.

Measured defect this rule closes - tag `v1.3.0`, on the Release run that
`gh run list --workflow Release --json attempt,headBranch,headSha -L 3` names (the id
belongs in that command's output, not in this page): `verify_release.py`
wrote `dist/SHA256SUMS` **and** a later shell step wrote a root-level `SHA256SUMS`,
so `files: dist/* + SHA256SUMS` resolved two assets with one name. The action
uploaded it once and then failed with
`Not Found - releases/assets#update-a-release-asset`, leaving the release a draft
until the failed job was re-run. `v1.2.1` hit the same error and continued with
`Matching asset is present after refresh`; `v1.3.0` turned it into a hard failure.
The manifest step now also refuses a non-file entry in `dist/` (a directory there
would be swept into `dist/*`) and any duplicated asset name before the upload
starts.

Read the current asset set, never a count:

```sh
# the three lists that must agree, from the workflow itself
grep -n -A4 'path:\|subject-path:\|files:' .github/workflows/release.yml
```

## Deploy

- Environments: none for the package. The artefact is a Python package; the
  "deployment" is a GitHub Release. `teamwork-agents` is **not on PyPI** (measured:
  `https://pypi.org/pypi/teamwork-agents/json` -> `404`, `pip index versions
  teamwork-agents` -> `No matching distribution found`), so the release asset is the
  only install source and a user needs no index at all:
  `pip install https://github.com/Nidvue/Teamwork/releases/download/<tag>/teamwork_agents-<version>-py3-none-any.whl`.
- Order of operations: `main` green -> push `main` -> CI green on that SHA ->
  CEO tags `v<version>` -> the Release workflow asserts the tag equals
  `src/teamwork/version.py`, re-runs the tests, builds sdist+wheel, extends the one
  `SHA256SUMS` over the artefacts and both SBOMs, **attests** build provenance and
  publishes the GitHub Release (asset set: [Release assets](#release-assets-one-manifest-one-name)).
  It does not sign: provenance is the sigstore attestation, verified with
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
