# ARCHITECTURE - Teamwork

Owner: Architect. Frozen interface contract for every parallel lane. Nothing in
this file changes without a recorded decision in [Decisions](Decisions.md).

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md) · [AuditReport](AuditReport.md) · [user guide](https://github.com/Nidvue/Teamwork/blob/main/docs/guide/architecture.md) · [pi packaging](Pi-Packaging.md)

## 1. What the system is

`Teamwork` is simultaneously:

1. **A skill** - `SKILL.md`, `roles/`, `references/`, `templates/` at the
   repository root, loadable from a project or user skills directory
   (`.agents/skills/teamwork`).
2. **A Python package** - `src/teamwork/`, installable with `pip install .`,
   exposing the `teamwork` console script and `python -m teamwork`.
3. **A workspace format** - markdown + JSON under
   `<project>/.pi/Teamwork/Teams/<Team>/`.

The three share one engine. The engine started as a behaviour-preserving port of
the original 7,416-line `teamwork.py` monolith. It is now a command layer over
typed modules - `config`, `io`, `names`, `layout`, `records`, `gitutil`,
`imaging` were moved out (D-20261018-CEO-3) and `engine.py` re-exports them - but
it is not thin: `wc -l src/teamwork/engine.py` -> **10,566**, i.e. 3,150 lines
(+42%) more than the monolith it replaced, because every command still lives in
it. The move was behaviour-preserving and is covered by the same suite; "one
module" describes the command layer's ownership, not its size.

## 2. Frozen repository layout

```
Teamwork/
├── SKILL.md                  # canonical skill entry (the host loads this)
├── roles/*.md                # 15 role charters
├── references/*.md           # policy detail
├── templates/                # AGENTS.md, Docs/*.md, TeamMap.md skeletons
│   └── pi-package/           # pi manifest fragments: skills/teamwork-pi/SKILL.md, prompts/*.md
├── .agents/skills/           # repo-local skills a session can load (ceo-audit-close)
├── src/teamwork/
│   ├── __init__.py           # re-exports __version__ only (no lazy re-exports)
│   ├── __main__.py           # python -m teamwork -> cli.main()
│   ├── bundle.py             # the bundle manifest + the mirror (sync/refresh one source of truth)
│   ├── cli.py                # main(argv) -> int, delegates to engine.main
│   ├── config.py             # workspace paths, record names, caps
│   ├── engine.py             # command layer: build_parser/main + gates, review/PR, memory, model
│   ├── gitutil.py            # git plumbing (branch/merge/LFS)
│   ├── harness.py            # harness surface: registry, whole-proposal lint, always-on budget
│   ├── hooks.py              # the git hooks: install/status/uninstall + the pre-commit/pre-push rules
│   ├── imaging.py            # offline image-model probe
│   ├── io.py                 # atomic writes, the lock, die()
│   ├── layout.py             # team tree paths and cross-links
│   ├── names.py              # names, roles, commit identities
│   ├── records.py            # task/memory/criteria/tests/PR/dispute records
│   ├── resources.py          # locate the skill bundle (checkout or wheel)
│   ├── portable.py           # OS portability seam
│   └── version.py            # the single version source; pyproject and the pi package read it
├── scripts/
│   ├── teamwork.py           # thin compat shim -> teamwork.cli.main
│   ├── verify_release.py     # build + install + smoke-test a wheel
│   ├── build_pi_package.py   # assemble the pi-teamwork tarball (make package)
│   ├── check_release_consistency.py  # the release-truth gate (make release-consistency)
│   ├── sync_skill.py         # mirror this checkout into an installed skills dir (make sync-skill)
│   └── privacy_scan.py       # tree + history privacy gate
├── tests/{unit,integration,acceptance}/  # pytest
├── docs/                     # mkdocs site (index/install/quickstart/...)
├── docs/Team/                # team-generated project documents
├── .github/workflows/        # ci.yml, release.yml, docs.yml
├── assets/                   # SVG logo, banner, terminal demo, social preview
├── pyproject.toml, Makefile, mkdocs.yml
└── community files           # README, CONTRIBUTING, SECURITY, CHANGELOG, CITATION
```

**File ownership (one writer per file) is binding for parallel work:**

| Lane | Owns |
|---|---|
| developer-1 | `src/teamwork/**`, `scripts/teamwork.py`, `scripts/check_release_consistency.py` |
| developer-2 | `tests/unit/**`, `tests/integration/**`, `tests/conftest.py` |
| tester-1 | `tests/acceptance/**` |
| developer-3 | `pyproject.toml`, `Makefile`, `scripts/verify_release.py`, `.editorconfig` |
| release-engineer | `.github/**`, `docs/Team/Release.md` |
| technical-writer | `docs/index.md`, `docs/guide/**`, `mkdocs.yml`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `CITATION.cff` |
| designer-1 | `README.md`, `assets/**`, `templates/Docs/**`, `docs/Team/Design.md` |
| security-auditor | `scripts/privacy_scan.py`, `docs/Team/AuditReport.md` |
| architect | `docs/Team/Architecture.md`, `docs/Team/Decisions.md` (technical entries), `tests/unit/test_portability.py` |
| product-manager | `docs/Team/Research.md` |
| project-manager | `docs/Team/Plan.md`, `docs/Team/Board.md` |
| coo | `docs/Team/Risks.md` |
| cfo | `docs/Team/Costs.md` |
| ceo | `SKILL.md`, `roles/**`, `references/**`, `templates/AGENTS.md`, `templates/TeamMap.md`, `templates/pi-package/**`, `.agents/skills/**`, `scripts/build_pi_package.py`, `scripts/sync_skill.py`, `docs/Team/Project.md`, `docs/Team/Pi-Packaging.md`, `docs/Team/Archive.md`, `docs/Team/AuditManifest.*`, `release-exceptions.json`, `docs/Team/Decisions.md` (governance entries) |

## 3. Resource-resolution contract (`resources.py`)

The engine needs four resource groups: `SKILL.md`, `roles/`, `references/`,
`templates/`, and a runnable engine path. Resolution order, first hit wins:

```
1. $TEAMWORK_SKILL_DIR                             (explicit override, tests use this)
2. importlib.resources.files("teamwork") / "data"   (installed wheel)
3. the repository root                             (git checkout: <repo>/src/teamwork/)
4. Path(__file__).parent.parent                    (the directory holding the package, e.g. src/)
```

Public API (frozen):

```python
skill_root() -> Path            # directory holding SKILL.md + roles/ + references/ + templates/
asset(*parts) -> Path           # skill_root() joined with parts
self_invocation() -> str        # machine-local command (absolute; private .pi/ state only)
portable_invocation() -> str    # committed command, never a machine path (AGENTS.md)
has_asset(name: str) -> bool
```

`self_invocation()` returns, in order of preference:

1. `teamwork` when the console script is on `PATH`;
2. `<sys.executable> <skill>/scripts/teamwork.py` when the shim exists (a checkout);
3. `<sys.executable> -m teamwork` (an installed package without the shim).

`config.py` calls `resources.skill_root()`; `engine.py` and every other module
import the resolved paths from `config`. The dependency direction is
`config <- io/names <- layout <- records`, and `engine` sits on top. Only the
`cli` entry point imports `engine` at import time, so the command layer can be
exercised without a cycle.

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

Every existing subcommand, flag and exit code is unchanged. Exit codes are part
of the contract:

| Code | Meaning | Sites in the engine's current tree |
|---|---|---|
| `0` | success | the completing path of every command |
| `1` | generic error or gate refusal; the `die()` default | `io.die(msg, code=1)`, `loop` CONTINUE (`return 1 if blockers else 0`) |
| `2` | usage error, or a gate that calls `die(..., 2)` explicitly | `identity --audit` bad range, dispute round past `MAX_ROUNDS`, unrecoverable workspace state, `review --claim/--release` misuse, review independence refusals |
| `3` | nothing to dispatch, or nothing matched the query | `criteria list` empty, `tests plan` with no declared area, `trace` no match, `task next` no executable task, `pulse` nothing to assign |
| `4` | lock acquisition timeout (`io.LOCK_TIMEOUT`, default 60s, `$TEAMWORK_LOCK_TIMEOUT`) | `io.lock()`; the message tells the reader to wait, never to delete a live lock |

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

The table above assigns **file writers**. Who must *certify* a layer is a
separate frozen map, `config.LAYER_OWNER`: `unit` -> developer, `integration` ->
tester, `acceptance` -> reviewer, `system` -> architect, plus one owner for each
remaining layer (`goal` -> ceo, `requirements` -> product-manager, `plan` ->
project-manager, `tech` -> cto, `release` -> release-engineer, `data` ->
data-engineer, `process` -> coo, `cost` -> cfo, `ui` -> designer, `docs` ->
technical-writer, `security` -> security-auditor). `tests add` refuses a record
from the wrong role, so the two maps must not be conflated.

## 9. CI / release contract

* `ci.yml` always fires: on a push to `main`, on a `v*` tag, on every
  `pull_request` and on `workflow_dispatch`. There is no workflow-level
  `paths-ignore`; the filtering is a job, not a trigger.
  * Jobs: `scope` (classifier), `lint` (ruff check + format --check +
    commit-identity audit), `typecheck` (mypy, non-blocking report), `test`
    matrix `{ubuntu,macos,windows} x {3.9,3.11,3.13}` plus ubuntu
    `3.10`/`3.12`, `build` (sdist+wheel+verify_release), `privacy`
    (`privacy_scan.py --tree --history --allow .github/privacy-allow.txt`:
    personal data, credentials, agent-host config and tracked local state),
    `committer-guard`, `release-consistency` (offline release gate),
    `docs` (mkdocs build --strict).
  * The `scope` job computes the changed-path set from git and publishes one
    output, `code` (`true` = something that ships changed). The expensive jobs
    (`lint`, `typecheck`, `test`, `build`, `privacy`, `docs`) carry
    `needs: scope` and
    `if: github.event_name != 'push' || needs.scope.outputs.code == 'true'`,
    so they skip on a **push only**, and only when the change set is
    prose/media only. Every `pull_request` runs the full set: a path-filtered
    skip reports no check at all, and a required check that is never reported
    blocks the merge. A **tag push** (`v*`) is not a code change: the tagged
    commit already passed the matrix as a `main` push and `release.yml` re-runs
    pytest on the tag, so the six expensive jobs are filtered out by `scope`
    (`code=false`) and the jobs that still run are the `scope` classifier
    itself and the two jobs that are not filtered by it -
    `committer-guard` and `release-consistency`. Both of those are unfiltered
    jobs, not "the consistency gate alone": `scope` can skip only the jobs
    that declare `needs: scope`, and every job without that declaration runs
    on every event.
  * The prose/media set the classifier uses is `docs/**`, `assets/**` and the
    root prose files `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
    `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, `LICENSE`, `AGENTS.md`
    and `mkdocs.yml`. This set and `.github/workflows/docs.yml`'s `paths:`
    list **must stay identical** - a path that leaves one list without joining
    the other is a hole in one of the two gates. The identity is checkable
    without a stored count: expand the `scope` job's `PROSE` regex and the
    `paths:` list of `.github/workflows/docs.yml` over the tree and compare the
    two sets - they must be equal, with no path in one list only. Every
    shipping path (`src/`, `scripts/`, `tests/`, `roles/`, `references/`,
    `templates/`,
    packaging, `.github/workflows/`, `SKILL.md`) is outside the prose set and
    still runs the full matrix.
  * The classifier measures every change set with `git diff --no-renames`, so
    a **rename is seen as a delete plus an add** and both paths are classified.
    Rename detection reports only the destination of a rename, so without
    `--no-renames` a move of a shipping file into a prose path would list only
    the prose path and be classified as prose - the matrix would be skipped on
    a change that removed shipping code.
  * The classifier's **undetermined** case is part of the contract: it enters
    the root-commit branch only when HEAD truly has no parent (every file it
    carries is the change set). Every other case whose fork point is HEAD -
    a rewritten history, a push whose `before` is unresolvable - is
    *undetermined*, and an undetermined change set runs the code jobs: an
    unknown change set must never silently skip the matrix.
  * The `release-consistency` gate is **never filtered**. It has no `needs:`
    and no `if:`, so it runs on every event, including a prose-only push,
    because its subject is prose that disagrees with a tag, `version.py` or
    `CHANGELOG.md` - a gate skipped exactly when the documentation drifts is
    worthless. The job graph says the same thing: `scope` can skip only the
    jobs that declare `needs: scope`, and the jobs in `ci.yml` that declare
    neither `needs:` nor `if:` are `committer-guard` and `release-consistency`
    - so a tag push, on which `scope` reports `code=false` and the six
    expensive jobs are skipped, still runs the classifier and those two jobs.
    The property is checkable without a line number: read the `needs:` and
    `if:` keys of every job in `.github/workflows/ci.yml`; the jobs with
    neither are `committer-guard` and `release-consistency`.
    It runs the checker offline
    (`scripts/check_release_consistency.py --offline --json`); the online half
    is the `consistency` job in `release.yml` (see below). Exit 0 is clean,
    exit 1 is drift, exit 2 is an unreadable input, and 1 and 2 both fail the
    job - there is no `continue-on-error`. A missing checker is an unreadable
    input (exit 2), not a pass: the checker is the subject of the gate, so its
    absence fails the job. The rule set (R1, R2 and the tag rules) is computed
    by the checker, never re-implemented or softened in the workflow.
* `release.yml`: on `v*` tags - build, checksums (`SHA256SUMS`), SBOM
  (CycloneDX JSON + SPDX), attestation, GitHub Release with all assets. The
  online half of the release-consistency gate is a separate `consistency` job
  there (`--online`), and `build` carries `needs: [consistency]`, so a release
  that cannot be traced is never built and never published. Whether that job
  is in the tree the reader holds is a question with a command, not a
  sentence: `git show HEAD:.github/workflows/release.yml | grep -n
  "consistency:"` prints a line when the job is in the tree and nothing when
  it is not, and the same file with `grep -n "needs: \[consistency\]"` says
  whether `build` waits for it. While that job is not in the tree, the offline
  half in `ci.yml` is the only gate.
* `docs.yml`: build and deploy the site to GitHub Pages on `main`; it triggers
  on the same prose/media set as the `scope` classifier and runs the checks
  that matter for prose (`teamwork links`, the privacy scan, `mkdocs build
  --strict`). The trigger policy and the offline/online split are written out
  in [Release](Release.md); the reason for the design is recorded in
  [Decisions](Decisions.md).
* The Release Engineer pushes reviewed revisions to the remote stage by stage
  (a stage ends with a push, not with a merge)
  (only after the Reviewer passes them, never a red gate); the Tester certifies
  local **and** CI results, routes failures to the owning role, and tags and
  public releases remain the CEO's step.

## 10. Seams for testing

* `resources.skill_root()` honours `TEAMWORK_SKILL_DIR` → tests point the engine
  at a fixture bundle.
* `engine` is importable as a module (`teamwork.engine`) → unit tests call
  functions directly instead of parsing CLI output.
* `--project` / `--team` already exist → every test isolates its workspace.

## 11. Release consistency contract

One file, `scripts/check_release_consistency.py`, compared against one committed
record, `release-exceptions.json`. The sibling gate on commit identity - which
committer, which acting role, which merge shape counts - is specified in
[Release](Release.md#what-the-identity-audit-accepts-and-why-t-0010). Its job: prove that every *published* fact
(git tag, npm version, GitHub Release, PyPI project, committed prose) agrees with
the *local* fact (`src/teamwork/version.py`, the tree at that commit, the tag
list). It is the release gate of [Release](Release.md); it is read-only (it
never tags, publishes, pushes or writes), it runs offline by default, and a
missing or unreadable input is an error, never a pass.

**What is implemented and what is pending (read this before the code).** This
section is the **target**, not a description of the running program; where the
two differ, the target wins - but the difference is stated here, once, so
nobody reads section 11 as a changelog of the current implementation. The
implementation this section is measured against is the Developer lane's commit
`d998801` (parent `c66c387`), reproducible with
`git show d998801:scripts/check_release_consistency.py`. Whether that
implementation is in the tree you are reading is a question with a command,
not a sentence: the checker file is in the tree when
`git ls-tree HEAD scripts/check_release_consistency.py` prints a line, and the
implementation is in the tree when `git merge-base --is-ancestor d998801 HEAD`
exits `0`. Against that code:

| Clause | Status | Where |
|---|---|---|
| 11.3 - on the local side the payload always comes from a git object; `rev=None` means `HEAD` | **implemented** | `d998801` `payload_digest` (`revision = "HEAD" if rev is None else str(rev)`) |
| 11.3 - link policy, all five cases, every refusal exit `2` | **implemented** | `d998801` `_extract_tar` / `_link_target` / `_materialise_links` |
| 11.3 - an unreadable payload file and an unresolvable link are input errors (exit `2`) | **implemented** | `d998801` `_digest_of_files` (`unreadable payload file`) and the link refusals |
| 11.2.2 - R2's tag set `S = A - O` (reachable version tags, minus the tags at `HEAD`) | **implemented** | `d998801` `rule_r2_head_is_newer` uses `_reachable_version_tags` and `_tags_at_head` |
| 11.2.2 - the `detail` counts `|S|`, never a negative number | **implemented** | the same function reports `is newer than {len(comparable)} tag(s)` over `S` |
| 11.2.2 - a shallow or tag-less checkout is exit `2` | **implemented** | `d998801` `_complete_tag_set_error` (`git rev-parse --is-shallow-repository`) |
| 11.2.4 - the frozen `TAGGED_TOKEN` regex | **implemented** | `d998801` `TAGGED_TOKEN` is the regex block of 11.2.4, verbatim |

Every row of the table names a symbol in `d998801`, so the "implemented" column
is re-derivable instead of a status word: for a row whose symbol is `<name>`,
`git show d998801:scripts/check_release_consistency.py | grep -c "<name>"`
prints `1` when the row is implemented and `0` when it is not.

Everything section 11 freezes is therefore implemented in the revision
`d998801`; whether that revision is in the tree the reader is holding is a
question with a command - `git merge-base --is-ancestor d998801 HEAD` exits `0`
when it is - and not a property of the document. The two amendments this
section introduced into the contract (`rev=None` and the link policy) were
implemented first, at `c66c387` (`git merge-base --is-ancestor c66c387 HEAD`
exits `0` when that is in the tree too); R2's `S = A - O`, the shallow guard and
`TAGGED_TOKEN` followed at `d998801`. The third amendment, that a published version which is
not `X.Y.Z` is DRIFT unless a 11.4 entry admits it (`T-0016`), lands at
`37ef0ed`: `git show 37ef0ed:scripts/check_release_consistency.py | grep -c
PUBLISHED_VERSION` prints `2` when it is in that revision. The table exists so
that a reader of section 11 does not read it as a changelog of the repository:
**the contract is the target, and each row names the revision that implements
it**.

### 11.1 CLI (frozen)

| Flag | Default | Meaning |
|---|---|---|
| `--offline` | on when no flag is given | no socket is opened; rules that need a registry print `SKIP` |
| `--online` | off | the registry/API rules (R3, R4, R5, R8) query npm, the GitHub API and PyPI |
| `--json` | off | emit the JSON object of 11.1.3 instead of the table |
| `--exceptions PATH` | `<repo-root>/release-exceptions.json` | the exception record of 11.4; a relative path resolves against `--repo-root` |
| `--repo-root PATH` | the current directory | every path and git call is rooted here (tests point it at a fixture tree) |

* `--offline` and `--online` together is a usage error: one line on stderr
  (`# check_release_consistency: --offline and --online are mutually exclusive`),
  nothing on stdout, exit `2`.
* `--repo-root` must be the top level of a git work tree
  (`git rev-parse --show-toplevel` normalises to it); otherwise exit `2`.
* Callable surface, for tests that do not want to spawn a process:

```python
main(argv: Optional[Sequence[str]] = None) -> int   # the frozen entry point
payload_digest(root: Path, rev: Optional[str]) -> str  # 11.3; rev None = HEAD
_http_get_json(url: str) -> object                  # the single network seam (11.1.4)
```

* Python **3.9+**, standard library only, no third-party import, no `subprocess`
  shell, and annotations written so they import on 3.9 (`from __future__ import
  annotations`). It is linted and formatted like the engine (`ruff check`,
  `ruff format --check`).

#### 11.1.1 Exit codes

| Code | Meaning |
|---|---|
| `0` | every rule is `ok` or an admitted `SKIP`; no DRIFT |
| `1` | at least one rule is `DRIFT` and no input failed |
| `2` | at least one input could not be read: malformed or missing exceptions file, not a git repository, a shallow or tag-less checkout for a tag rule (11.2.2), or `--online` with a registry/API call that answered nothing (5xx, timeout, DNS/TLS - *not* a 404, see 11.1.4) |

Precedence is `2` > `1` > `0`: a run that finds drift *and* cannot read the
registry exits `2`. An unreadable input is never downgraded to a `SKIP` that
leaves the exit code at `0`.

#### 11.1.2 stdout (table mode)

Exactly one line per rule, in R1..R9 order, then one summary line:

```text
<RULE-ID> <ok|DRIFT|SKIP> <detail>
...
# release consistency: <N> problem(s)
```

* `RULE-ID` is `R1`..`R9`; the status field is one of the three literals.
* Fields are separated by a single space; `detail` is the rest of the line, is
  never empty, contains no newline, and joins several findings with `; `.
* `N` counts **DRIFT findings**, not rules, and the summary line is printed even
  when `N` is `0` and on exit `2`.
* `detail` carries the evidence, not an opinion: the tag, the file and line, the
  digest, the URL and the HTTP status. A `SKIP` detail must say *why* it cannot
  be evaluated (`offline: npm registry unreadable`), never just `skipped`.
* Stray warnings go to stderr; stdout stays parseable.

#### 11.1.3 `--json`

One JSON object on stdout, keys in this order, `json.dump(obj, sys.stdout,
indent=2, ensure_ascii=False)` plus a trailing newline - and nothing else:

```json
{"problems": [{"rule": "R3", "detail": "..."}], "rules": [{"id": "R1", "status": "ok", "detail": "4 tag(s) agree with version.py"}], "exit_code": 0}
```

`rules` carries every rule in R1..R9 order with the same `status`/`detail` as
the table; `problems` carries exactly the DRIFT findings in rule order, so
`len(problems)` equals `N` in the summary line. There is no fourth key: the
reason an input failed is the `detail` of the `SKIP` it produced.

#### 11.1.4 The network seam

Every HTTP call goes through `_http_get_json(url)`. `--offline` must not reach
it (a test monkeypatches it to raise and asserts `0`/`1`, never an exception),
and `--online` uses it only for R3 (npm), R4/R5 (GitHub) and R8 (PyPI). It uses
`urllib.request` with a 20 s timeout, an explicit `User-Agent`, no credential
and no token from the environment (a secret must never be logged, and an
anonymous read is enough for all three endpoints).

**The one split - an answer about the artefact vs an unreadable input.** This
paragraph is the only place the contract states it, and no rule restates it
differently:

* **HTTP 404 is a *finding about the artefact*, not a failure to read.** The
  registry answered, and the answer was "this does not exist". 404 therefore
  belongs to the rule that asked (R8: the distribution is unpublished, so each
  unmarked channel line is DRIFT; R3: a version's `dist.tarball` is gone, so the
  version is DRIFT unless 11.4 admits it) and **never** produces exit `2` on its
  own.
* **5xx, a timeout, a DNS failure, a TLS failure, a connection error, or a
  non-JSON body is an unreadable input.** Nothing was learned about the
  artefact, so the rule prints `SKIP` whose `detail` says why and the run exits
  **`2`** (11.1.1). `_http_get_json` raises `HttpError`/`InputError`, the rule
  converts it to that `SKIP`, and the code is never downgraded to `0`.

So a non-200 that is *not* a 404 is the "failed API call" of exit `2`, while a
404 is the answer the rule was waiting for.

### 11.2 The nine rules

The **local** column is always readable offline from `--repo-root`. A rule whose
published half needs a network is `SKIP` under `--offline` and says so; it never
invents an `ok`.

| Rule | Published fact | Local fact | DRIFT when | Offline |
|---|---|---|---|---|
| R1 | every git tag `vX.Y.Z` | `src/teamwork/version.py` **at that tag's commit** | the file is missing there, has no `__version__`, or its value is not `X.Y.Z` | evaluates |
| R2 | `version.py` at HEAD | the version tags **reachable from HEAD**, minus those that point at HEAD (`S`, 11.2.2) | the HEAD version is not **strictly greater** than some version in `S` | evaluates (needs the complete tag set, 11.2.2) |
| R3 | every npm-published version | a git tag whose bundled-payload digest (11.3) equals that tarball's payload digest, or an entry in 11.4 | neither exists (a 404 on the advertised tarball is also DRIFT - 11.1.4) | `SKIP` |
| R4 | every GitHub Release | `git tag -l` | no tag has the release's name | `SKIP` |
| R5 | every git tag | the GitHub Release list | no release carries the tag's name | `SKIP` |
| R6 | committed markdown that prints a version, names a `releases/download/<tag>/` asset, or pins `--branch`/`--tag`/`git checkout` at a version | `version.py` at HEAD, and `git tag -l` for a release asset or a pin | a printed literal version is **older** than HEAD's, or a release-asset tag / pin names no tag or one **older** than the newest, and its line/block is not illustrative-marked | evaluates |
| R7 | `CHANGELOG.md` | every tagged version | a tagged version has no `## [X.Y.Z]` section, or more than one | evaluates |
| R8 | committed markdown that advertises an install channel | the shipped name/entry point, and (online) PyPI | the channel names a package or executable the repository does not ship, or `--online` finds the channel does not resolve and the text does not mark it unavailable | partial (see 11.2.4) |
| R9 | committed markdown that names a tag | `git tag -l` | a `vX.Y.Z` token, or a bare `X.Y.Z` token in a pin/tag context (11.2.4), names a tag that does not exist | evaluates |

#### 11.2.1 R1 detail

* Tag set: `git tag -l` filtered by `^v\d+\.\d+\.\d+$`; any other tag name is
  ignored (not a version claim).
* Tag content is read with `git show <tag>:src/teamwork/version.py` - the tag, not
  HEAD, and the tag object's commit for an annotated tag.
* `__version__\s*=\s*["']([^"']+)["']` is the parse; a non-semver value is drift.

#### 11.2.2 R1/R2 on a tag-push checkout

Versions compare as integer tuples `(major, minor, patch)`. R1 evaluates every
tag against **its own commit** and never against HEAD (11.2.1), so it is
indifferent to what is checked out.

**R2's tag set (frozen).** R2 asks *is this checkout ahead of the newest release
on its own line of history?* It is evaluated over a set `S` computed in three
steps, the only place the rule reads git:

1. `A` - the **version tags** (`^v\d+\.\d+\.\d+$`, 11.2.1) whose commit is
   **reachable from HEAD**, i.e. `git merge-base --is-ancestor <tag> HEAD`
   exits `0`. This is `git describe --tags --abbrev=0`'s ancestry, not
   `git tag -l`.
2. `O` - the subset of `A` that **points at HEAD** (`git tag --points-at HEAD`).
3. `S = A - O` - the tags R2 compares against, and the set its `detail` counts.

DRIFT iff some tag in `S` has a version that is **not** strictly less than
HEAD's, and the `detail` names each such tag. `ok` reads
`HEAD <X.Y.Z> is newer than <|S|> tag(s)`, where `|S| = len(A) - len(O)` over
**reachable version tags only**, so the count is never negative. The rule it
replaces (`c66c387:891-899`) compared HEAD against **every** version tag in the
repository and counted `len(tags)` - a count that is never negative either, but
that has no notion of reachability, so it was red against tags which were
never the checkout's ancestors. The arithmetic this subsection forbids is
`len(git tag -l) - len(O)`: it subtracts the tags-at-HEAD from *every* tag in
the repository, so on one version tag with two doc tags at HEAD it evaluates to
`-2`. No revision of the checker implements it and none prints a negative
count; it is the defect the freeze removes, not an output of any shipped code.

Two consequences of the ancestry freeze, both intended:

* **A maintenance branch is not permanently red.** A `1.0.x` line branched off
  `v1.0.0` with `v1.0.1` on it sees only `v1.0.0` and its own tag; the later
  `v1.1.0`/`v1.1.2` of the main line are not its ancestors, so they are outside <!-- release-consistency: illustrative -->
  `A` and R2 is `ok`. Under a "compare against every tag in the repository"
  rule such a branch could never be green again - the defect this freeze
  removes.
* **A tag that is not an ancestor of HEAD is invisible to R2.** R1 still checks
  it against its own commit, R4 and R5 still see it, R7 still requires its
  CHANGELOG heading; R2 alone ignores it, because it says nothing about whether
  *this* checkout is ahead of *its* history. It is neither an error nor a
  finding and never contributes to the count.

Why `O` is excluded is structural, not a convenience: R1 requires `version.py`
at a tag's commit to **equal** that tag's name, so the commit that carries
`vX.Y.Z` has `version.py == X.Y.Z`, and comparing HEAD against that tag could
only ever ask whether a release is greater than itself. Including it makes the
two rules mutually exclusive on exactly the revision
`.github/workflows/release.yml` builds (a `v*` tag push), so the gate could
never be green on the build it exists to gate.

| HEAD state | R1 | R2 |
|---|---|---|
| HEAD is exactly tag `vX.Y.Z`, its `version.py` is `X.Y.Z`, no other tag at HEAD | `ok` (the tag agrees with its own commit) | `ok` - `O` is HEAD's own tag; the detail counts `\|S\|` (= `\|A\| - 1`, because `O` holds exactly that one tag) |
| HEAD newer than every reachable tag | `ok` | `ok`, detail counts `\|S\|` |
| HEAD older than the newest *reachable* tag | `ok` (each tag still agrees with its own commit) | DRIFT - names each reachable tag ahead of HEAD |
| HEAD between two reachable tags | `ok` | DRIFT - names the reachable tags ahead of HEAD only |
| HEAD on a maintenance line; later main-line tags are not ancestors | `ok` | `ok` - those tags are outside `A` |

The first row is the *detached HEAD that is exactly a tag*: a fresh
`git checkout vX.Y.Z`, the release CI checkout, or the tag commit on `main`
before the next bump all land there. R2 is `ok`; the gate is green on the
release build. It stays meaningful on `main`: once `main` moves past the tag
without a bump, HEAD's version equals the newest reachable tag, that tag no
longer points at HEAD, and R2 is DRIFT (the release tag is then simply an older
tag). The release order is unchanged - tag the payload commit, then bump
`version.py` on `main` immediately after; R2 simply no longer punishes the
tagged commit for being tagged.

**The complete tag set is a required input; a shallow clone is exit `2`.** Any
workflow that evaluates R1, R2, R4 or R5 must check out the repository with the
**complete tag set** (`actions/checkout` with `fetch-depth: 0`), and the checker
must treat the alternatives as input errors, never as passes:

* `git rev-parse --is-shallow-repository` printing `true`, or
* a version-tag set that is empty while the remote carries tags.

Either makes every tag rule exit `2` with the reason in its `detail`; it never
prints `R1 ok 1 tag(s)` / `R2 ok ... 0 tag(s)` from a clone that simply cannot
see the tags. This matters most where it is least visible:
`.github/workflows/release.yml` builds exactly the revision R2 exists to gate, so
a shallow checkout there turns the gate green *because the build is blind*. The
**tarball path** carries the same guard: a tarball unpacked without `.git` has no
tag list at all, so R1/R2 against it are an unreadable input (exit `2`), never a
clean run.

**This subsection changes a rule's meaning, and is marked as a meaning change.**
Before it, R2 compared HEAD against *every* version tag in the repository; the
frozen rule compares only the version tags reachable from HEAD, excludes the
tags that point at HEAD, and counts `|S|`. The old and new behaviour are both
stated above so the change is reviewable from this file alone. The matching `D-` entry is
[D-20261021-Architect](Decisions.md#d-20261021-architect---r2-compares-head-only-against-the-version-tags-reachable-from-head),
which carries this task's measurements, the alternatives rejected and the
falsifier.

#### 11.2.3 R3 detail

Two comparisons, both on the same digest definition (11.3):

1. **npm side.** Read `https://registry.npmjs.org/@nidvue%2Fteamwork` (the
   published name is `@nidvue/teamwork`, `scripts/build_pi_package.py`), take
   every version key, and for each download `dist.tarball`; unpack the `.tgz`
   into a temporary directory (`tarfile`, `tempfile`, never into the repo), **map
   the tarball paths back to payload paths with the table in 11.3.1**, and
   compute the 11.3 digest on those payload-relative paths. Hashing the tarball
   where it sits is not the definition: a tarball path is not a payload path.
2. **local side.** The tag whose version equals the npm version, at that tag's
   commit; its digest must equal the tarball's.

An npm version is satisfied by (a) such a tag or (b) a 11.4 entry. Note what (a)
implicitly forbids: a tag at a commit whose payload differs from the tarball,
which is exactly the npm `1.1.0` case of 11.5.

**There is no third path, and the version's shape is not one.** "Take every
version key" means every key is enforced: a key that is not `X.Y.Z` cannot have
a `vX.Y.Z` tag, so it is DRIFT unless a 11.4 entry admits it. Classifying such a
key as "ignored" let a published version escape both paths of AC-REL-1 by its
spelling alone (measured: npm's `0.0.0-stage` staged-publish placeholder, no tag,
no `gitHead`, published before `1.1.0`) - which is why 11.4's `version` key
accepts the published string, not only `X.Y.Z`. A 11.4 entry is the only way a
published version can be untagged, whatever its shape (`T-0016`).

**`scripts/build_pi_package.py` is excluded from both sides of every digest.**
It is the build-time generator that *assembles* the tarball; it is not shipped
payload, so a change in it does not change what a user receives, and including
it would report a drift for a repository-side edit (11.5, third example). The
exclusion is part of the definition, applied uniformly, not per-version.

Every exception is visible in R3's `detail` on every run, whatever R3's status:
the note `<version> admitted by exception (<reason>)` is appended to the R3
`detail` (`_exception_notes`), so a clean run reads
`R3 ok 1 npm version(s) match a tagged payload digest; 1.1.1 admitted by exception (...)`
and an offline run reads `R3 SKIP offline: npm registry not queried; 1.1.1
admitted by exception (...)`. An exception never turns a DRIFT into an ok: a
DRIFT line names the version, the tarball digest, the local digest and the tag
that was tried. An exception naming a version that *does* have a `vX.Y.Z` tag is
itself DRIFT (`exception names a traceable version ...; remove the entry`): an
entry admits an untraceable version, it does not retire a traceable one.

#### 11.2.4 R6, R8, R9 detail - the markdown scanners

**Scope.** Committed markdown is enumerated with `git ls-files -- '*.md'` and read
from the working tree (so an uncommitted edit is caught before it is committed).
A tracked path that no longer exists on disk is skipped, not a drift.
`docs/Team/Archive.md` is **out of scope for every scanner** (R6, R8, R9): it is
historical evidence, and rewriting the past to satisfy a gate is worse than the
drift.

**R6 scope** is the narrower prose set `README.md`, `docs/guide/*.md`,
`docs/index.md`, `docs/Team/Release.md`. **R8 and R9 scan every committed `.md`**
of the 11.2 scope above.

**Version token (R6).** `(?<![\w./-])v?(\d+\.\d+\.\d+)(?![\w./-])`, on a line
that is *about this project*: the line, or the fenced block containing it,
matches `(?i)teamwork`. Two exclusions keep it from inventing drift:

* a token inside a URL or a link destination does not match the regex (a `/` or
  `.` abuts it), so `.../compare/v1.1.2...HEAD` and `semver.org/spec/v2.0.0.html`
  are not version claims;
* a line that declares a foreign tool's version is skipped:
  `(?i)\b(python3?|cpython|node|npm|pi)\s*[:=]\s*\d` (`python: 3.12.13` in
  `docs/guide/install.md` is not a teamwork version).

**The one URL that is a version claim: a release asset.** The exclusion above
was written to keep a `compare/` *range* out, and it also blinded R6 to the one
URL shape whose tag is a claim: a `releases/download/<tag>/<asset>` link names
the release an install command downloads, so a superseded tag installs a
superseded wheel. That shape is read by its own literal-path pattern
`(?<=releases/download/)v?(\d+\.\d+\.\d+)(?=/)`. Because the lookbehind is the
path and not a lone `/`, `.../compare/v1.1.0...v1.1.2` still matches nothing -
the two rules read the same URLs in opposite directions on purpose.

**The second kind of version claim: a pin.** A version inside a
`--branch`/`--tag`/`--ref` value, or after `git checkout`/`git switch`, is a claim
even when the line never names the project - `docs/guide/install.md` pins a tag in
a console block with no `teamwork` on it, so the project-context gate read nothing
there, and R9 (which sees the same shape through `TAGGED_TOKEN`) only asks whether
the tag exists, never whether it is stale. R6 therefore reads pins through its own
local pattern, not through `TAGGED_TOKEN`:

```python
PIN_VERSION = re.compile(
    r"(?<![\w./-])(?:--(?:branch|tag|ref)[\s=]+|git\s+(?:checkout|switch)\s+)"
    r"v?(\d+\.\d+\.\d+)(?![-/\w])(?!\.\w)"
)
```

It is separate for two reasons: R6 must stay blind to a bare `vX.Y.Z` in prose (a
measurement, a drill) and to the `releases/tag/` and `compare/` shapes it reads the
other way, and a pin claim must not depend on the line's wording. The illustrative
marker exempts a pin exactly as it exempts prose, and the pin is judged against the
tag baseline below.

**Two baselines, one rule.** A prose token is judged against **HEAD**; a release
asset tag and a pin are judged against `git tag -l` - each must **name an existing
tag** and must not be **older than the newest one**. They differ because a released
asset or a pin can only name a release while `version.py` legitimately leads the
newest tag between releases: with HEAD `1.1.3` and newest tag `v1.1.2`, a pin for
`v1.1.2` is correct and a pin for `v1.1.0` is stale. Judging either against HEAD
would make the correct command unfixable without an illustrative
marker, which would hide exactly the staleness the rule exists to report. R6's
`detail` still reports only the count of illustrative lines; an asset or pin
finding names the file, line, tag and the baseline it missed - `installs the
v1.1.0 release asset, older than the newest tag v1.1.2` for an asset and `pins
--branch v1.1.0, older than the newest tag v1.1.2` (or `git tag -l has no such
tag`) for a pin, so the two shapes stay distinguishable in the gate output.

**Illustrative marker (R6 and R9).** The exact literal
`<!-- release-consistency: illustrative -->`. It exempts a physical line when it
appears on that line, and exempts a whole fenced block when it stands on a line
of its own immediately above the opening fence. It is an HTML comment, so it is
invisible in the rendered page; anything else (a word like "example", a suffix
in the text) is not a marker. R6 and R9 report how many lines/blocks they
exempted inside the rule's `detail` (`2 illustrative`), so an exemption is
visible in the gate output rather than silent.

**R7.** Headings are matched with `^## \[(\d+\.\d+\.\d+)\]` (bare or linked).
A `## [Unreleased]` heading and a heading for a version that has **no** tag are
both fine - the changelog may lead the tag; only a tagged version without a
heading, or a duplicate heading, is drift.

**R8 offline half.** The three channel forms are matched literally on one line:
`pip install teamwork-agents` (and the `python -m`, `python3 -m`, `py -m` <!-- release-consistency: channel-unavailable -->
variants), `pipx install teamwork-agents`, `uvx --from teamwork-agents`. Each <!-- release-consistency: channel-unavailable -->
must agree with the shipped metadata - the distribution name
(`version.DIST_NAME`, `teamwork-agents`) and the console script
(`[project.scripts]` `teamwork` in `pyproject.toml`) - and must be covered by the
channel marker below or by `--online`. A name that does not match resolves
nowhere, so it is drift **offline**; the online half is the resolver.

**Channel-unavailable marker.** The exact literal
`<!-- release-consistency: channel-unavailable -->`, with the same line/fence
reach as the illustrative marker. It is the text's own statement that the
channel is not live yet, so an unmarked channel line is a claim and a marked one
is an admission.

**R8 online half.** `https://pypi.org/pypi/teamwork-agents/json`: HTTP 200 means
the channel resolves and every unmarked channel line is `ok`; HTTP 404 means the
distribution is unpublished, so each **unmarked** channel line is DRIFT (name
the file and line, and the 404) while marked ones stay `ok`. That 404 is a
*finding*, not an unreadable input - 11.1.4 states the split once and this rule
does not restate it: a 5xx, a timeout, a DNS/TLS error or a non-JSON body here is
`SKIP` and exit `2`, exactly as there.

**R9.** R9's DRIFT clause is about a *tag* name, so a bare semver is a claim
only where the surrounding text makes it one. The pattern is frozen exactly as
below and has **one capture group**:

```python
TAGGED_TOKEN = re.compile(
    r"(?:(?<![\w./-])v"
    r"|(?<![\w./-])(?:--(?:branch|tag|ref)[\s=]+|git\s+(?:checkout|switch)\s+"
    r"|releases/tag/|compare/)v?)"
    r"(\d+\.\d+\.\d+)(?![-/\w])(?!\.\w)"
)
```

**Group 1 carries the version in every alternative.** The tag claimed is always
`v` + `match.group(1)` (the reader is `f"v{match.group(1)}"`), so no branch of
the alternation can produce `vNone`: the context prefixes match inside a
non-capturing group and only the semver is captured. There is no group 2.

The two alternatives:

* **a `v`-prefixed token anywhere** - `v1.0.0` in prose, or a rollback paragraph
  quoting a deleted tag;
* **a bare semver in a pin/tag context** - immediately after `--branch`,
  `--tag` or `--ref` (whitespace or `=`), after `git checkout`/`git switch`, or
  inside `releases/tag/<token>` or `compare/<token>` - each with or without the
  `v`. This is what catches a pin naming a version that was never tagged, the
  defect a `v`-mandatory pattern missed.

Two boundary guards, and why each is written as it is:

* **leading `(?<![\w./-])`**, on *both* alternatives - a claim never starts
  inside a word or a path, so `xcompare/9.9.9` and `my--branch 9.9.9` match
  nothing.
* **trailing `(?![-/\w])(?!\.\w)`** - two assertions, not one character class,
  because `.` means two different things at a token's end. A `.` followed by a
  word character is a domain or file extension (`semver.org/spec/v2.0.0.html`,
  `v2.0.0.html`) and the token ends before it; a `.` followed by anything else
  ends a sentence or starts a git range, so `released at v9.9.9.` and <!-- release-consistency: illustrative -->
  `compare/9.9.9...HEAD` **are** claims. A `-` or `/` keeps its old meaning (a <!-- release-consistency: illustrative -->
  pre-release suffix `v9.9.9-rc1`, a path segment, a longer token), and a
  trailing word character is a longer token.

R6 owns bare version prose; R9 owns tag claims. A bare semver outside those
contexts is not a tag claim - the Python interpreter line `python: 3.12.13` in
`docs/guide/install.md` names an interpreter, and reporting it as a missing tag
would be a defect, not a finding - and so are `version: 3.12.13` and a bare
`foo/bar/9.9.9`: with no context keyword the pattern does not match at all.

**One rule, not two: where the keyword sits.** A `compare/` or `releases/tag/`
keyword preceded by `/` or `.` is part of a link destination
(`https://github.com/Nidvue/Teamwork/compare/v1.1.2...HEAD`, the CHANGELOG
`[Unreleased]` heading), and the leading lookbehind rejects it - that URL
matches nothing. The *same* keyword in prose or in a code span
(`compare/9.9.9...HEAD`, `releases/tag/9.9.9`) is a claim and **is** reported. <!-- release-consistency: illustrative -->
That is one guard read two ways, not a promise that `compare/<token>` is covered
beside a claim that it is not.

Any matched token that is not illustrative-marked must name a tag in
`git tag -l`.

### 11.3 Bundled payload and its digest (frozen)

The **bundled payload** is the shipped set, and it is exactly
`teamwork.bundle.BUNDLE_FILES` + `teamwork.bundle.BUNDLE_TREES` as asserted by
`scripts/build_pi_package.py`: the files `SKILL.md`, `AGENTS.md` and the trees
`roles/`, `references/`, `templates/`, `scripts/`, `src/`. Nothing else ships -
not `tests/`, not `docs/`, not the community files, not build output.

```python
files = every file under root/{roles,references,templates,scripts,src}
        plus root/SKILL.md and root/AGENTS.md
files -= {"scripts/build_pi_package.py"}          # 11.2.3: build-time generator
lines = sorted(f"{sha256(file_bytes).hexdigest()}  {relpath_posix}" for f in files)
digest = sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()[:16]
```

* `relpath_posix` is the path relative to the payload root, with `/` separators
  on every OS - the digest must be identical on Linux, macOS and Windows.
* Two spaces between digest and path (the `sha256sum` line shape), lines sorted
  as strings, one trailing newline, hashed **once**. Symlinks are resolved under
  the link policy below; a payload file that cannot be read, and a link that
  cannot be resolved, are the **same case - an input error (exit `2`)**, never a
  skip and never drift (11.1.1: an unreadable input is never downgraded, and
  `2` takes precedence over `1`).
* `payload_digest(root, rev)`: on the local side the payload **always comes
  from a git object**.
  The tree is materialised with `git archive <rev>` into a temporary directory
  (never `git checkout`), and `rev=None` means the commit **`HEAD`** names - not
  the working tree. The working tree is never a digest source, so it contributes
  no bytes, the archive path and the npm path always read the same tree, and
  the two can never disagree about what the payload is. The npm side passes a
  staging tree built from the published tarball by 11.3.1, never the unpacked
  tarball itself.

* The first 16 hex characters are the published comparison form
  (`a01d9f0cbee641c3`, 64 bits) - long enough that a collision is not a
  realistic accidental pass.

**Link policy (frozen).** A link is resolved inside the payload tree; it is
never followed out of it, and the refusal never names the target.

1. **Target inside the repository and inside the commit** - the link is
   materialised as a regular file holding the target's bytes, and the digest
   reads those bytes. A link to a tracked but gitignored file resolves the same
   way. Measured: a committed `references/l -> references/keep.md` gives
   `rev=None` and `rev=HEAD` the same digest `1e24271d36f868d3`, and that
   digest does **not** move when the target is edited on disk. The fixture is
   committed: `tests/unit/test_release_consistency_digest.py` -
   `test_an_in_commit_link_resolves_on_both_paths` asserts
   `payload_digest(root, None) == payload_digest(root, "HEAD")` on it, and
   `test_a_link_to_a_tracked_but_gitignored_file_resolves_and_is_stable`
   asserts the digest is unchanged by an edit to the target on disk. The
   assertion is the contract; the digest is what the committed fixture
   produces.
2. **Absolute target** - refused, **exit `2`** (input error): `archive member
   links to an absolute path: <the link's own path>`.
3. **Target outside the repository / outside the tree** - refused, **exit `2`**:
   `archive member links outside the tree: <the link's own path>`.
4. **Target inside the git directory** (`.git` anywhere in the target's parts) -
   refused, **exit `2`**: `archive member links into the git directory: <the
   link's own path>`.
5. **Broken, cyclic or self-referential target** - refused, **exit `2`**: `archive
   link does not resolve to a readable file (broken, cyclic or self-referential):
   <the links' own paths>`.

Every refusal names the **link's own path** and never the target's path, so a
refusal cannot carry a name from outside the tree into the digest or into the
printed output.

**11.3.1's closing bullet is a restatement of this subsection.** It states that a
payload file which cannot be read - like a link which cannot be resolved - is
an **input error (exit `2`)**, never drift, and it points here for the
precedence rule: where 11.3 and 11.3.1 differ, this subsection governs, and
11.1.1 keeps `2` above `1`. 11.3.1's remap table and its "no recognizable
prefix → exit `2`" rule are otherwise byte-identical to the frozen text.

**Why an unresolvable link is an input error (exit `2`) and not drift (exit
`1`).** DRIFT means a published fact disagrees with the local fact; a link
pointing out of the tree means there is no local fact to compare - the checker
could not read an input at all. That is the class 11.1.1 already reserves for
exit `2` (a missing exceptions file, a shallow checkout), and exit `2` outranks
exit `1`, so the run stops instead of reporting a release inconsistency that was
never measured. DRIFT would also be the wrong label for a link into `.git`,
which is not a claim about the release at all. The measurement that forced the
rule: with the working tree as the digest source, a committed
`references/l -> ../.git/config` gave the digest `f2aeb5b8a144fe47`, and
appending a token-bearing remote URL to **`.git/config` alone** moved it
again - a byte of git configuration changing a published digest. The
mechanism is the contract, and it is pinned by the committed fixture
`tests/unit/test_release_consistency_digest.py`
(`test_a_link_into_the_git_directory_is_refused_on_both_paths` and
`test_editing_git_config_does_not_move_the_digest`).
With the payload read from a git object the same tree is refused outright:
`archive member links into the git directory: references/l`.

#### 11.3.1 Payload-path layout of a published tarball (frozen)

`scripts/build_pi_package.copy_skill` **re-lays** the payload: a tarball path is
not a payload path. Hashing a `.tgz` where it sits therefore produces a digest no
commit can reproduce - measured, in place and package-relative over all files,
npm `1.1.2` gives `7c540615af001e46` and `1.1.0` gives `c7bc2b6d4ec6bfde`, neither
of which matches any tag. The mapping below is part of the digest definition,
applied to every npm version, never per-version:

| Tarball prefix (under `package/`) | Payload prefix | Produced by |
|---|---|---|
| `skills/teamwork/` | `` (payload root) | `copy_skill`, the portable skill, `SKILL_FILES` + `SKILL_TREES` |
| `skills/teamwork-pi/` | `templates/pi-package/skills/teamwork-pi/` | `copy_skill`, copied from that repository path |
| `prompts/` | `templates/pi-package/prompts/` | `copy_skill`, copied from that repository path |

Everything else in the tarball (`package.json`, `README.md`, `LICENSE`,
`NOTICE`, `CHANGELOG.md`, `SECURITY.md`) is package metadata, not bundled
payload, and is ignored. A tarball with none of the three prefixes is an input
error (exit `2`), not an empty payload.

To build the npm-side `root`: unpack the `.tgz`, create an empty staging
directory, and copy every file under each tarball prefix to the corresponding
payload prefix, preserving the relative path below the prefix. Then run the 11.3
digest on the staging directory. Measured with this mapping (and 11.2.3's
exclusion), `1.1.2` gives `a01d9f0cbee641c3` = the payload of commit `3f4981d`,
`1.1.0` gives `ebfc2538e3d3d605` = tag `v1.1.0`, and `1.1.1` gives
`726bc547afc41ead`, which matches no commit.

Two implementation consequences, both measured:

* **Line order is by string over the whole line** (`digest-then-path`), not by
  path. Sorting by path alone gives `b1ba21e39436bf09` for `1.1.2` and
  `0786a4ff3c2f84ba` for `1.1.1` when `scripts/build_pi_package.py` is included;
  those are **not** 11.3 digests and must never be published as such.
* Symlinks are resolved under the link policy of 11.3, and a payload file that
  cannot be read - like a link that cannot be resolved - is an **input error
  (exit `2`)**, never drift; where 11.3 and this subsection differ, 11.3 governs
  (its precedence note, above).

### 11.4 `release-exceptions.json` (frozen)

A JSON **array** at the repository root, committed, sorted by `version`; an empty
array is valid and is the initial state. Every entry has exactly these four keys
and no others:

```json
[
  {
    "version": "1.1.1",
    "reason": "published from a workspace whose commit was never pushed",
    "evidence": "digest 726bc547afc41ead matches no commit in git rev-list --all",
    "recorded": "2026-10-20"
  }
]
```

| Key | Contract |
|---|---|
| `version` | the npm version it admits: `X.Y.Z`, or a published `X.Y.Z-<prerelease>`/`X.Y.Z+<build>` string that no `vX.Y.Z` tag can carry (11.2.3); anything else is an input error; duplicate versions are an input error (exit `2`) |
| `reason` | one sentence a reviewer can judge; empty is an input error |
| `evidence` | the measurement, not a restatement: a digest, a command with its result, a URL |
| `recorded` | `YYYY-MM-DD`, the ISO date the entry was written |

It is read **before** any rule runs. Missing file, invalid JSON, a non-array, a
non-object entry, a missing/extra key, a version that is not an npm version (see
`version` above), or a date that is not `YYYY-MM-DD` is an input error: exit `2`,
with the offending path and problem in the `detail` of the `SKIP` that R3 prints.

An exception is a **recorded, reviewable admission**, never a silent pass: it is
committed, it goes through the two-stage gate like any other artifact, and R3
prints a line for it on every run. It admits one version's missing or
mismatching tag - it does not suppress any other rule, and it cannot silence a
DRIFT that R3 found for a *different* version.

### 11.5 Worked examples - three measured facts

Every digest below is an **11.3 digest**: the mapping of 11.3.1 applied to the
tarball and `scripts/build_pi_package.py` excluded, lines sorted as strings.
The checker must reproduce them and the implementer must not contradict them.

| # | Measurement | What the contract makes of it |
|---|---|---|
| 1 | npm `1.1.2` payload digest `a01d9f0cbee641c3` equals the bundled-payload digest of commit `3f4981d` | `v1.1.2` must be tagged **at `3f4981d`**; then R1, R3, R5 hold for it and R2 forces the next `version.py` bump <!-- release-consistency: illustrative --> |
| 2 | npm `1.1.1` payload digest `726bc547afc41ead` matches **no** commit in `git rev-list --all`; its `version.py` sha256 `545fc1605b3997460a1cf348562c43fed5a8315c83ac8291f9cbf4078703d36d` appears in no commit | `1.1.1` is the 11.4 exception entry, never a tag: there is no commit to tag, so a tag would be a lie the digest can prove <!-- release-consistency: illustrative --> |
| 3 | npm `1.1.0`, mapped per 11.3.1 and excluding `scripts/build_pi_package.py`, gives `ebfc2538e3d3d605` = tag `v1.1.0`; **including** that file the same comparison gives `acec49f6cd1fe99a` for the tarball vs `cd43f09293a49c68` for the tag, and they differ only in that file | the payload comparison must map the paths (11.3.1) and exclude that file (11.2.3), or a green release reads as drift <!-- release-consistency: illustrative --> |

Commands behind the numbers (reproducible from any checkout): the three
tarballs were fetched with `npm pack @nidvue/teamwork@<version>` into a temporary
directory, unpacked, mapped per 11.3.1 and hashed per 11.3; the local side is
`payload_digest(root, "3f4981d")` and `payload_digest(root, "v1.1.0")`. The
1.1.1 absence was checked by digesting **every** commit of `git rev-list --all`
with the same function: no match. The count-free form of the measurement is the
predicate itself - `git rev-list --all` contains no commit whose 11.3 payload
digest is `726bc547afc41ead` - so it can be re-run at any revision without
re-reading a number.

Example 1 also fixes the release order: tag the payload commit, then let CI's
`release.yml` build from the tag - never retag a later doc-only commit, whose
payload digest no longer matches the tarball.

The checker's own unit tests live in `tests/unit/` (section 8) and use fixture
trees through `--repo-root`; they are not a second contract.

## 12. Harness surface and hook contract (frozen)

Owner: Architect. The frozen interface for the `harness`, `hooks` and `hook`
lanes; decided in D-20261020-Architect to D-20261020-Architect-9, with the hook
directory and the layer tests fixed by ruling D-0001 R1-R6
(`D-20261020-Architect-8`). No removal, no rename and no extra flag lands
without a new entry in [Decisions](Decisions.md) and a notice to the affected
lane.

### 12.1 The two command groups

```text
teamwork.py harness list
teamwork.py harness lint [--verbose]
teamwork.py harness budget [--limit KB]
teamwork.py hooks install [--force]
teamwork.py hooks status
teamwork.py hooks uninstall
teamwork.py hook pre-commit
teamwork.py hook pre-push <remote> <url>
```

`hook pre-commit` and `hook pre-push` are **shim entry points, not operator
commands**: git calls them with git's own arguments and they are never part of
an agent's workflow. `hook` and `hooks` coexist because argparse matches a
subcommand exactly before trying an abbreviation, so `teamwork.py hook` and
`teamwork.py hooks` both resolve while `teamwork.py hookk` exits 2.

Nothing with these names existed before this contract: the parser registered 43
top-level commands and none of them is `harness`, `hook` or `hooks`; no
`HARNESS`/`HOOK` constant and no `TEAMWORK_SKIP_HOOKS`, `TEAMWORK_ALLOW_MAIN` or
`TEAMWORK_ALLOW_FORCE` variable was taken.

### 12.2 The surface registry (C1..C8)

`harness list` prints exactly **eight** rows, one per Harness^2 component, in
component order, with four whitespace-separated columns and no header line:

```text
<class>  <bytes>  <path>  <role>
```

- `class` is one of `always-on`, `on-demand`, `in-loop` (12.3).
- `bytes` is the total size in bytes of the files the `path` spec selects **at
  run time**; `-` only for C5, which has no file. `0` is a measurement and
  therefore only allowed when the spec was resolved and the files it names
  genuinely do not exist. A spec that can select nothing **by its spelling** is
  a defect in the row, never a zero: the row must name a path the command can
  actually reach, or the number it prints describes the spelling, not the tree.
- `path` is the spec exactly as tabulated below, `/` separators: repository-
  relative for C1..C7, and for C8 the resolver call its files are found through
  (§12.6), printed as the template `hook_dir(root)/{pre-commit,pre-push}`. C8 is
  a template and not a repository-relative path because the hooks live in the
  git directory git reports, which differs per repository, per worktree and per
  `core.hooksPath`; the absolute directory that was actually probed is printed
  by `hooks status` (§12.6), never guessed here.
- C3 is summed over every role directory and the global memory of the project,
  because the command is not scoped to one instance.
- `role` is the owner of that path under section 2, or `-` where section 2
  assigns none.
- exit code 0.

| C | Harness^2 component | `path` spec | `class` | `role` |
|---|---|---|---|---|
| C1 | system prompt | `SKILL.md` | always-on | ceo |
| C2 | guardrails | managed block in `AGENTS.md` | always-on | ceo |
| C3 | memory | `Roles/<Role>/*.md` + `Global/GlobalMemory.md` | always-on | - |
| C4 | tool guidance | `references/*.md` | on-demand | ceo |
| C5 | subagents | `n/a` (lane packet, no file) | - | - |
| C6 | skills | `.agents/skills/*/SKILL.md` | on-demand | ceo |
| C7 | scripts | `scripts/*.py` + `src/teamwork/*.py` | in-loop | developer |
| C8 | plugin | `hook_dir(root)/{pre-commit,pre-push}` | in-loop | - |

C8 is the one row that is not a repository-relative path, and that is
`D-20261020-Architect-8`, not a preference. In a linked worktree - which is
where every lane of this team works - `<toplevel>/.git` is a 66-byte **file**
(measured in this lane's own worktree), so a spec spelled
`.git/hooks/{pre-commit,pre-push}` selects nothing:
`os.path.getsize` raises `NotADirectoryError` and `glob` returns `[]`, and the
row would report `0` bytes for a hook that is installed and executing. Measuring
through `hook_dir(root)` makes the measured directory and the executed directory
the same one by construction.

The registry names files that already exist; it adds no generated manifest and
no copy of the text it measures (D-20261020-Architect).

### 12.3 Activation classes

| Class | Meaning | Consequence |
|---|---|---|
| `always-on` | in context on every call, before the task is known | paid by every run; the only class the budget caps |
| `on-demand` | loaded by a tool call only when it is invoked | paid once per invocation a task actually needs |
| `in-loop` | executed inside the tool loop instead of being reasoned about | costs latency and process, not context |
| `n/a` | an inference context, not a file (C5) | not measured; the lane packet is not an artifact |

C5 is `n/a` rather than a path: a subagent is a second context, not a file, and
the engine has no artifact for it. Inventing one would make the registry lie.

### 12.4 `harness lint`

Whole-proposal invalidators, run before a change is accepted. Exit 1 when any
finding exists, 0 on a clean tree.

| Rule | Refuses |
|---|---|
| `IDENTITY` | frontmatter `name` differs from the skill's directory, or `description` is empty |
| `TRIGGER` | the skill name appears in no always-on surface (`AGENTS.md`, `SKILL.md`, `roles/*.md`) |
| `SUBCOMMAND` | a `teamwork.py <word>` in a skill file names a command the parser does not register |
| `HELPER` | a repo-relative path a skill file references does not exist |
| `EVIDENCE` | a `status: shared` skill carries no `verdict: helped\|hurt\|no observed effect\|confounded` |

Output, one line per finding, in rule order `IDENTITY`, `TRIGGER`, `SUBCOMMAND`,
`HELPER`, `EVIDENCE` and sorted by path within a rule:

```text
- PROBLEM <RULE> <path>: <detail>
# problems found: N
```

`--verbose` also lists every file checked. `EVIDENCE` is skipped when no
workspace exists, because `Skills.md` lives in the team tree; the other four
rules are pure tree checks and always run. The `SUBCOMMAND` vocabulary is the
parser itself, never a list (D-20261020-Architect-3).

On this tree the rule fires: `ceo-audit-close` appears in no always-on surface.
That is a true positive (a skill with no trigger line), fixed in the always-on
text that the CEO owns, never by weakening the rule.

### 12.5 `harness budget`

One line per instance, then one total line, same four columns with `total` in
the first:

```text
<instance>  <always_on_bytes>  <budget_bytes>  <ok|OVER>
total       <sum_bytes>        <budget_bytes x instances>  <ok|OVER>
```

- `always_on_bytes` = managed `AGENTS.md` block + `SKILL.md` + that role's
  charter + that role's memory. The unit is **one instance**, never the roster.
- `budget_bytes` = `AlwaysOnBudgetKb` x **1024** (KiB, frozen so the number is
  reproducible). The key lives in the workspace `Settings.json`, defaults to
  `120` in `config.py`, and **must be listed in `config.SETTINGS_NON_PROVIDER`**:
  the Settings loader reads every undeclared key as a provider concurrency cap
  (`D-20261020-Architect-6`).
- `--limit KB` overrides the workspace value for one run.
- exit 1 when any instance is `OVER`; exit 0 otherwise. With no workspace it
  dies with code 1 and the message that says to run `teamwork.py init`.
- the managed block is read through the engine's `BEGIN`/`END` markers, the same
  pair `agents-md` writes; no second marker literal.

The default is 120 KiB = 122880 B against a measured worst instance of 93379 B
(76%): 27386 B block + 46575 B `SKILL.md` + 18069 B largest charter + 1349 B
role memory (`D-20261020-Architect-4`).

### 12.6 The hook shim contract

**One resolver, three subcommands.** `hooks install`, `hooks status` and
`hooks uninstall` all take the hook directory from the same helper
`hook_dir(root)`. None of them may build a path from `.git` plus a suffix, none
may spell `.git/hooks` as a constant, and none may re-derive the directory its
own way: the write side and the read side must be the same call, or `status`
reports `absent` while a live hook runs. No default is hardcoded and
`core.hooksPath` is honoured for free, because git computes the answer
(`git -C <root> -c core.hooksPath=/tmp/x rev-parse --git-path hooks` ->
`/tmp/x`); special-casing it is a defect.

The resolver is correct only as an **atomic pair**:

```text
hook_dir(root) = git -C <root> rev-parse --path-format=absolute --git-path hooks
```

or, equivalently, `git -C <root> rev-parse --git-path hooks` with a **relative**
result joined onto `<root>`. The `-C <root>` pin is mandatory and is part of the
rule, not style: `--git-path` answers relative to the cwd of the git invocation,
so from `scripts/` it prints `../.git/hooks`, and joining that onto
`--show-toplevel` lands in the PARENT directory of the repository - a path that
is not this repository at all. Joining a relative result onto the project root
is therefore **not** a contract on its own; it holds only inside the `-C <root>`
pairing (`D-20261020-Architect-8`).

`root` is `git rev-parse --show-toplevel`, and it stays that: the hook
**directory** answers "where git reads hooks", the **toplevel** answers "which
work tree the rules act on", and the two legitimately differ - in a linked
worktree they are not even under the same repository root. The installer must
not assert a common prefix or a common parent between them.

`hooks status` prints the literal directory it probed, so its answer can be
checked against `git rev-parse --git-path hooks` instead of trusted:

```text
pre-commit  <installed|absent|foreign>
pre-push    <installed|absent|foreign>
# hooks directory: <the directory the resolver returned>
```

The hooks are per **common git dir**, so installing from any lane worktree
installs for every worktree of that repository at once.

Mode `0755`, LF endings, and exactly this body:

```sh
#!/bin/sh
# teamwork-managed hook (stage: pre-commit) - remove with: teamwork.py hooks uninstall
# the hook file lives in the git dir; the rules act on the work tree below
[ -n "${TEAMWORK_SKIP_HOOKS:-}" ] && exit 0
root=$(git rev-parse --show-toplevel) || exit 0
# -f, not -x: scripts/teamwork.py is committed 100644, so an executable-bit
# test would turn every hook into a silent no-op in this repository
[ -f "$root/scripts/teamwork.py" ] || exit 0
exec python3 "$root/scripts/teamwork.py" hook pre-commit "$@"
```

with `pre-push` and `hook pre-push` in place of `pre-commit` in the stage lines.
That body is `hooks.py shim()`, verbatim at the merged revision
(`git show main:src/teamwork/hooks.py`); three constructs in it are contract, not
detail (`D-20261020-Architect-9`):

- **`[ -f ]`, never `[ -x ]`.** `scripts/teamwork.py` is committed mode
  `100644` (`git ls-files -s scripts/teamwork.py`), so an executable-bit test is
  false in every checkout of this repository and every installed hook would
  `exit 0` without running one rule - enforcement that silently does nothing is
  worse than no hook, because `hooks status` still says `installed`.
- **`${TEAMWORK_SKIP_HOOKS:-}`.** An unset bypass means "run the rules"; the
  `:-` makes the expansion total so it can never be the thing that fails. A bare
  `$TEAMWORK_SKIP_HOOKS` aborts under an inherited `set -u`
  (`sh -u -c 'echo "[$UNSET_VAR]"'` -> `UNSET_VAR: unbound variable`, rc 127),
  which git reads as a refusal: the bypass would become a blocker.
- **`root=$(git rev-parse --show-toplevel) || exit 0`.** The `|| exit 0` is the
  whole failure path, so nothing else may swallow git's error: the contract has
  **no** `2>/dev/null` on that call. Outside a work tree the shim is a no-op, and
  a silent redirection would hide why it is one.

| Rule | Contract |
|---|---|
| marker | one constant, `config.HOOK_MARKER = "teamwork-managed hook"`, rendered **as one line 2**: `# <marker> (stage: <stage>) - remove with: teamwork.py hooks uninstall`. `install` (overwrite refusal), `status` and `uninstall` all key on that one constant; a hook file without it is `foreign` and is never overwritten or removed without `--force` |
| escape | a set (non-empty) `TEAMWORK_SKIP_HOOKS` exits 0 before anything else; the bypass is documented, never silent |
| root | the shim resolves the project root with `git rev-parse --show-toplevel`; the rules act on the work tree, the file lives in the git directory |
| engine | `python3 "$root/scripts/teamwork.py"`; a tree without the shim (an installed wheel) is a no-op, not a guessed command |
| install | refuses to overwrite a hook without the marker unless `--force`; exit 0 when the hook is written or already correct |
| status | `<stage> <installed\|absent\|foreign>` for both stages, then the literal `# hooks directory: <path>` line naming the directory the resolver probed, exit 0 |
| uninstall | resolves through the same `hook_dir(root)`, removes only marked hooks, leaves a foreign hook and says so, exit 0 |
| not a git repo | every `hooks` subcommand dies with code 1 and a message naming the missing repository |

### 12.7 Hook rules

Exit 0 for a pass; exit 1 for a refusal (git aborts the operation on any
non-zero).

| Id | Stage | Rule | Override |
|---|---|---|---|
| R1 | pre-commit | refuse the commit whose HEAD is `config.DEFAULT_BASE`, resolved with `git symbolic-ref --short HEAD` (it answers on an unborn branch) | `TEAMWORK_ALLOW_MAIN=1` |
| R2 | pre-commit | refuse a staged **binary** file larger than `config.LFS_MAX_BYTES` (1048576) that no `.gitattributes` LFS pattern covers; a text record is never refused **by the threshold**; and refuse a staged **text** file that an LFS pattern **does** cover, because a document in LFS is a pointer (section 11.10) | add the pattern (first case) / drop the pattern (second case); no env override |
| R3 | pre-commit | warn on stderr when the commit identity is not a role mailbox (`<role>@IDENTITY_DOMAIN`), and exit **0** | - |
| P1 | pre-push | refuse a non-fast-forward update of `refs/heads/<DEFAULT_BASE>` | `TEAMWORK_ALLOW_FORCE=1` |
| P2 | pre-push | refuse deleting `refs/heads/<DEFAULT_BASE>` (zero local sha) | none |

Reuse is part of the contract: R1 and P1-P2 read `config.DEFAULT_BASE` (one
constant, no literal); R2 calls `gitutil.lfs_tracked`, compares against
`config.LFS_MAX_BYTES` and asks `gitutil.is_binary_content` and
`gitutil.lfs_text_mismatch` for the two tests, the same calls
`commit --check-lfs` uses; P1 asks
`git merge-base --is-ancestor`, the engine's own fast-forward test; R3 compares
against `IDENTITY_DOMAIN` and `names.role_identity`, never a second domain
string. Re-implementing any of them is a defect, not a shortcut.

R1 must also refuse the **root commit**, and that is why it resolves the branch
through `gitutil.current_branch` and falls back to `git symbolic-ref --short
HEAD` whenever that answer is empty or `HEAD`. On an unborn branch
`git rev-parse --abbrev-ref HEAD` prints `HEAD` and fails, so a rule that stops
there waves the first commit on the default branch straight through: measured by
the Tester, the root commit lands on `main` and only the second one is refused
(`D-20261020-Architect-9`). `symbolic-ref --short HEAD` answers `main` there, and
a detached HEAD stays `HEAD`, which is not `DEFAULT_BASE`, so the rule does not
fire. The rule compares the resolved name to `DEFAULT_BASE` and refuses on
equality, bypass included.

R3 is a warning **by contract**: it is the only rule here with no engine gate
behind it, and an identity mismatch is a provenance problem, not a correctness
one (`D-20261020-Architect-2`). The pre-push reader consumes git's stdin
refspec lines: `<local ref> <local sha> <remote ref> <remote sha>`.

### 12.8 Exit codes for the new surface

The codes in section 4 are unchanged and no new code is introduced:

| Code | Sites |
|---|---|
| `0` | `harness list`, a clean `harness lint`, an `ok` `harness budget`, every `hooks` subcommand on success, every hook rule that passes or only warns (R3) |
| `1` | any `harness lint` finding, an `OVER` budget line, a hook refusal (R1, R2, P1, P2), no workspace, not a git repository, a `hooks` misuse |
| `2` | argparse usage error only, including an ambiguous abbreviation of `hook`/`hooks` |

### 12.9 The layer test

`tests/unit/test_cli_contract.py` - layer `system`, area `cli-contract`, owner
Architect - parses this section and the CLI and fails when either drifts: the
documented command and flag list, the eight-component registry with a class from
the closed set, `hook` and `hooks` registered as subcommands. Atomicity is
**per group**, not across the three: a group this revision *has* registered must
be registered **completely** - every frozen verb with every frozen flag, so a
`hooks` group without `uninstall` or a `harness list` without `harness budget`
fails the test, and a partial landing cannot pass review quietly. A group this
revision has not landed at all is reported as **NOT LANDED** by the same test and
does not fail it: `hooks` + `hook` may ship while `harness` is still pending, and
which lane lands first is not this contract's business. The landing itself is
enforced by the acceptance criteria and the lane's own tests, not by this one.

A primary-checkout test does **not** cover this contract. Two further cases are
mandatory, both hermetic (`git init` and `git worktree add` in the test's own
temporary directory, no network, no lane worktree, nothing under `/tmp` outside
the test root):

| Case | Construction | Assertions |
|---|---|---|
| linked worktree | `git init -q` in a fresh directory, one commit, `git worktree add -q ../wt -b probe`, CLI run with cwd inside `../wt` | (a) the hook file exists under the **primary** repository's `.git/hooks`; (b) `<wt>/.git` is still a **file** afterwards; (c) a commit made from `../wt` **executes** the hook (a probe hook that writes or prints a marker proves it ran); (d) `hooks status` from `../wt` reports `installed` and prints that directory; (e) `hooks uninstall` from `../wt` removes it |
| subdirectory (negative) | the CLI run from a **subdirectory** of the primary checkout, e.g. `repo/scripts`, with the repository passed as root | the hook lands in `<repo>/.git/hooks` and never in `<parent-of-repo>/.git/hooks`; the directory `status` prints is the same one the file was written to |

The subdirectory case is the `-C <root>` pin under test: it is the only shape in
which a cwd-relative `--git-path` answer is observably wrong. **A skipped
worktree test is a review failure, not a pass** - the linked worktree is where
every lane of this team actually works, so a suite that only exercises the
primary checkout has not tested the contract at all (`D-20261020-Architect-8`).

### 11.10 The LFS threshold applies to binaries, not to text records (frozen)

`config.LFS_MAX_BYTES` (1048576) is a **binary** threshold. It is not a size
limit on the repository: a tracked **text** record that grows past it is still a
document, and a document in Git LFS is broken - a reader without an LFS client
sees a pointer, and the link check follows a pointer instead of a document
(`D-20261021-Architect`).

The three gates that read the threshold are the **audit**, **`commit
--check-lfs`** and the **pre-commit rule R2**. All three ask the **same
predicate**, `gitutil.is_binary_content(path)`, and all three compare against
**the same constant**, `config.LFS_MAX_BYTES`. A fourth literal is a defect:
`cmd_commit`'s `--lfs-threshold` default reads the constant, and the audit's
own size test reads the constant. There is exactly one number and one binary
test in the codebase.

| Question | Answer (frozen) |
|---|---|
| What does the threshold apply to? | **Binary content only.** A text record is never refused **by the threshold**, at any size. |
| How is "binary" decided? | **By content**, through `gitutil.is_binary_content` - never by extension, never by path, never by an allow-list of directories. |
| Which files are exempt? | Every file whose content is text: the `docs/Team/` records, the skill files, the tracked markdown/json/text files the team reads and the link check follows - and every other text file in the tree. The exemption is a property of the **content**, not of the location. |
| What happens when a text record is large? | **Nothing.** It is a document. It is committed as a plain file and it grows. The threshold says nothing about it. |
| What happens when a binary is large? | The gate refuses it and names the file, exactly as before, and the remedy is the same: add the `.gitattributes` LFS pattern. |
| Is a text record ever pushed into LFS? | **No.** `.gitattributes` routes a file into LFS **by name**, so a text file can be routed there by accident - and a document in LFS is broken. The gates therefore **refuse** a text file that a pattern would capture, with a message naming the mismatch. This check is **size-independent**: a text file in LFS is broken at any size. |

**The two refusals, and the difference between them.** The gates refuse for two
distinct reasons, and a file can hit either one:

| Refusal | Trigger | Message |
|---|---|---|
| the threshold | a **binary** above `LFS_MAX_BYTES` that no LFS pattern covers | "refusing to commit large file(s) that no Git LFS pattern covers" - the remedy is to add the pattern |
| the mismatch | a **text** file that an LFS pattern **does** cover | "refusing to commit text file(s) that .gitattributes routes into Git LFS" - the remedy is to drop the pattern or make the content binary |

The two are opposites and both are needed. The first stops a binary from
reaching history unarchived; the second stops a document from being archived as
if it were a binary. Together they are what makes the promise in this section
**true**: a text record is never pushed into LFS, because the gate that would
push it refuses the commit first.

**Why content and not the name.** A name-based rule is a rule the content can
defeat: a real binary renamed `.md` is exempt, and a genuine binary dropped
into `docs/Team/` is exempt. Git itself decides "binary" from the bytes, not
from the name (`git diff --numstat` prints `-  -` for a random-byte `.md`), so
a content test is the model the repository already trusts. The test is
`gitutil.is_binary_content`: read the first 8192 bytes; if they contain a NUL
byte the file is binary, **except** when the head decodes as printable UTF-16 -
a UTF-16 document also contains NUL bytes and is still a text file. This is the
same rule `git` uses and the same shape `scripts/privacy_scan.py` already
applies to a file's head.

**The pattern check reads `.gitattributes` last-match-wins.** A later
`-filter` line cancels an earlier `filter=lfs` pattern, exactly as git reads
it: the shipped `.gitattributes` opts the small social-preview PNG and the
brand assets OUT of LFS, and a check that ignored the opt-out would report a
text brand asset as a misconfiguration that does not exist.

**The test is a gate, not a helper.** The layer test for this section must call
the **audit** and the **commit path**, not a private predicate: a test that only
calls the predicate passes while the product is broken, because the defect lives
in the *wiring*. The suite must fail when (a) the audit stops exempting a large
text record, (b) the audit stops flagging a large binary, (c) `commit
--check-lfs` refuses a large text record, (d) the hook's R2 refuses a large
text record, and (e) any of the three gates stops refusing a text file that an
LFS pattern would capture. A predicate-only test is a review failure, not a
pass (`D-20261021-Architect`).

**The three gates, one predicate.** `gitutil.is_binary_content` and
`gitutil.lfs_tracked` are the only two questions any of the three gates asks,
and each gate asks them in the same order: is the content binary, and does an
LFS pattern cover it. The engine's audit, the engine's `cmd_commit` and the
hook module must not each grow their own copy of the test.
