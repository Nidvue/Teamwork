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
├── .agents/skills/           # repo-local skills a session can load (tw-ceo-audit-close)
├── src/teamwork/
│   ├── __init__.py           # re-exports __version__ only (no lazy re-exports)
│   ├── __main__.py           # python -m teamwork -> cli.main()
│   ├── attention.py          # team-local attention items + the task stage table
│   ├── board.py              # docs/Team/Board.md: render both task tables from the queues, check them
│   ├── bundle.py             # the bundle manifest + the mirror (sync/refresh one source of truth)
│   ├── cli.py                # main(argv) -> int, delegates to engine.main
│   ├── config.py             # workspace paths, record names, caps
│   ├── engine.py             # command layer: build_parser/main + gates, review/PR, memory, model
│   ├── evolution.py          # the self-evolution books: check + snapshot, wired into audit
│   ├── gitutil.py            # git plumbing (branch/merge/LFS)
│   ├── harness.py            # harness surface: registry, whole-proposal lint, always-on budget
│   ├── hooks.py              # the git hooks: install/status/uninstall + the pre-commit/pre-push rules
│   ├── imaging.py            # offline image-model probe
│   ├── io.py                 # atomic writes, the lock, die()
│   ├── lanerun.py            # one lane's detached child: budget + outcome file
│   ├── lanes.py              # the engine's own lane runtime: spawn, supervise, dynamic waves
│   ├── layout.py             # team tree paths and cross-links
│   ├── memorypack.py         # task-aware memory: score, pack, search, dream (Memory.md 4)
│   ├── memverify.py          # memory verify: the focused, score-ranked check pass
│   ├── messages.py           # the agent mailbox: priority queue, take/done, preemption
│   ├── names.py              # names, roles, commit identities
│   ├── records.py            # task/memory/criteria/tests/PR/dispute records
│   ├── resources.py          # locate the skill bundle (checkout or wheel)
│   ├── portable.py           # OS portability seam
│   ├── transcripts.py        # transcript reach: the ledger and the worklogs (Memory.md 10)
│   ├── wiki.py               # the capped wiki: pages of fact lines that point at records (Memory.md 15.5)
│   └── version.py            # the single version source; pyproject and the pi package read it
├── scripts/
│   ├── teamwork.py           # thin compat shim -> teamwork.cli.main
│   ├── verify_release.py     # build + install + smoke-test a wheel
│   ├── build_pi_package.py   # assemble the pi-teamwork tarball (make package)
│   ├── check_release_consistency.py  # the release-truth gate (make release-consistency)
│   ├── check_comments.py      # the no-comment gate (make lint)
│   ├── ci_scope.py            # classify a change set into the code/prose gate answers
│   ├── lane_proof.py         # the repeatable plugin-free fan-out proof (T-0037)
│   ├── sync_skill.py         # mirror this checkout into an installed skills dir (make sync-skill)
│   ├── render_social_preview.py  # draw assets/social-preview.png from the README pitch
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
| release-engineer | `.github/**`, `docs/Team/Release.md`, `scripts/ci_scope.py` |
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
| `teamwork coordination` | coordination health: conformity, trust, lane wars, merge rate, slot starvation |
| `teamwork instance add\|list\|retire` | scale **any** role to N instances sharing the role's memory and queue; retire an idle one and keep the role's memory |
| `teamwork memory claim\|release\|renew\|contest\|extend\|revoke\|status` | the role memory lease: exactly one instance of a role revises that role's memory at a time, held across a multi-entry update; a peer contests a long lease and the arbiter (CTO, folded to the CEO) extends or revokes it |

Every existing subcommand, flag and exit code is unchanged. Exit codes are part
of the contract:

| Code | Meaning | Sites in the engine's current tree |
|---|---|---|
| `0` | success | the completing path of every command |
| `1` | generic error or gate refusal; the `die()` default | `io.die(msg, code=1)`, `loop` CONTINUE (`return 1 if blockers else 0`) |
| `2` | usage error, or a gate that calls `die(..., 2)` explicitly | `identity --audit` bad range, dispute round past `MAX_ROUNDS`, unrecoverable workspace state, `review --claim/--release/--renew` misuse, review independence refusals |
| `3` | nothing to dispatch, or nothing matched the query | `criteria list` empty, `tests plan` with no declared area, `trace` no match, `task next` no executable task, `pulse` nothing to assign |
| `4` | lock acquisition timeout (`io.LOCK_TIMEOUT`, default 60s, `$TEAMWORK_LOCK_TIMEOUT`) | `io.lock()`; the message tells the reader to wait, never to delete a live lock |

## 5. Workspace-format contract (frozen)

Unchanged from the skill: `.pi/Teamwork/Teams/<Team>/` with `Roles/<Role>/`
(shared memory, `TaskQueue.md`, and `Lessons.md` - created lazily by the first
`lesson add`, local state like memory and never committed), `Agents/<Instance>/` (private), `Global/`,
`Runtime/`, `Ledger.jsonl` (hash-chained), `Criteria.md`, `Tests.md`,
`TestPlan.md`, `Reviews.md`, `Disputes.md`, and `Knowledge.md` - the project-wide
`K-` records (section 15), created lazily by the first `knowledge add`, local
state like memory and never committed.

Additive, and the only state `instance`/`memory` introduce:
`Runtime/Locks/memory-<Role>.claim` is the role memory lease - one JSON object
(`role`, `instance`, `token`, `acquired`, `expires_ts`, `minutes`, `explicit`,
`reason`) whose live holder is the single instance allowed to revise that role's
memory. An absent, unreadable or expired file means the role is free. Two fields
carry an arbitration: `contests` (the peers' `--by` / `at` / `reason` requests,
written under the role lock) and `arbitrated_by` / `arbitrated_at` once the
arbiter rules, so a live holder cannot erase a pending case by writing one more
entry. It lives under `Runtime/`, is ephemeral and gitignored, and removing it
never loses a memory entry - the memory itself stays in `Roles/<Role>/`.

The ledger record shape and chain (`_digest(prev, record)`) are frozen; changing
them invalidates every existing workspace.

## 6. Portability contract

* Runtime: CPython **3.11 - 3.13**, Linux, macOS, Windows. No third-party import
  at runtime.
* Forbidden in the runtime path: `fcntl`, `termios`, `pwd`, `grp`, `os.fork`,
  `resource`, `shell=True`, POSIX-only signal use. The runtime path is every
  shipped Python root - `src/teamwork/` and `scripts/`, which the sdist carries
  (`pyproject.toml` include list) - and `tests/unit/test_portability.py` scans
  both, so a POSIX-only import in the release scripts fails the same guard as
  one in the engine. A *required external binary* is a different defect class
  (`du` in `build_pi_package.py`, T-0002) and is pinned functionally instead:
  that build runs with every `argv[0]` refused (`tests/unit/test_pi_package.py`).
* All file I/O passes `encoding="utf-8"`; generated text is written with
  `newline="\n"` for byte-identical output across platforms.
* Process liveness for stale-lock recovery must use a portable helper:

```python
def pid_alive(pid: int) -> bool   # Windows-safe; never kills anything
```

* Paths never hardcode `/tmp`, `/home` or a drive letter; use `tempfile` /
  `pathlib` only. The one exception is the generated git hook, which is POSIX
  `sh` and names its temp file `mktemp "${TMPDIR:-/tmp}/..."`: on win32 `sh`
  exists only inside git, where `/tmp` is git's own MSYS temp directory
  (T-0001: `TMPDIR` unset, `MINGW64_NT-10.0-26200` -> `mktemp ok: /tmp/...`), and
  a `mktemp` that cannot create the file refuses the hook rather than passing it.

## 7. Packaging contract

* Build backend: `hatchling`. `python -m build` produces
  `dist/teamwork_agents-<v>.tar.gz` and `dist/teamwork_agents-<v>-py3-none-any.whl`.
* Distribution name `teamwork-agents` (PyPI `teamwork` is taken); import name
  `teamwork`; console script `teamwork`.
* Canonical assets are force-included into the wheel at `teamwork/data/`:
  `SKILL.md`, `roles/`, `references/`, `templates/`.
* Runtime dependencies: none (`dependencies = []`). `requires-python = ">=3.11"`.
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

A test that executes an external tool guards on it first, through
`tests/tooling.py` (`require_tool`): an absent tool produces a **skip that names
the tool and states why the test needs it** - never a failure, never a silent
pass. The guarded set is the convenience path only (`make`, and `sh`/`bash` for
the git hooks and the workflow run-block fixtures). Tools the product itself cannot run without -
the interpreter and `git` - are deliberately **not** guarded: a skip there would
report a green build for a host that can never work. Pinned by
[tests/unit/test_tool_guards.py](https://github.com/nidvue/teamwork/blob/main/tests/unit/test_tool_guards.py).

The table above assigns **file writers**. Who must *certify* a layer is a
separate frozen map, `config.LAYER_OWNER`: `unit` -> developer, `integration` ->
tester, `acceptance` -> reviewer, `system` -> architect, plus one owner for each
remaining layer (`goal` -> ceo, `requirements` -> product-manager, `plan` ->
project-manager, `tech` -> cto, `release` -> release-engineer, `data` ->
data-engineer, `process` -> coo, `cost` -> cfo, `ui` -> designer, `docs` ->
technical-writer, `security` -> security-auditor). `tests add` refuses a record
from the wrong role, so the two maps must not be conflated.

## 9. CI / release contract

The per-job wall clock is capacity, not a gate: no job drops a check to fit its
bound, and the bound only stops a hung run. The `test` job is bounded at 90
minutes because the suite spawns hundreds of processes and the Windows runner
spawns them several times slower than Linux (measured: 18 min on ubuntu 3.13, 30
on macos 3.13, and windows hit the old 60-minute cap on runs 42530928486 and
42533590196).
`tests/unit/test_ci_contracts.py` pins the same bound in `TIMEOUT_MINUTES` and
fails when the workflow and this table disagree.

* `ci.yml` always fires: on a push to `main`, on a `v*` tag, on every
  `pull_request` and on `workflow_dispatch`. There is no workflow-level
  `paths-ignore`; the filtering is a job, not a trigger.
  * Jobs: `scope` (classifier), `lint` (ruff check + format --check +
    commit-identity audit), `typecheck` (mypy, non-blocking report), `test`
    matrix `ubuntu {3.11,3.12,3.13} + macos 3.13 + windows 3.13`
    (five cells, nine jobs: the Windows cell runs as five path shards, and the
    ubuntu 3.12 cell runs the named subset `tests/unit tests/acceptance` and the
    macOS cell runs that subset plus `tests/integration/test_portability_flow.py`,
    instead of the whole suite),
    `build` (sdist+wheel+verify_release), `privacy`
    (`privacy_scan.py --tree --history --allow .github/privacy-allow.txt`:
    personal data, credentials, agent-host config and tracked local state),
    `committer-guard`, `release-consistency` (offline release gate),
    `docs` (mkdocs build --strict).
  * The Windows cell is sharded because one job per cell was cancelled at the
    90-minute cap (run 43000716956: the a-f row carried unit a-f plus the whole
    integration and acceptance trees). Five shards, disjoint by path and together
    naming every `test_*.py` under `tests/`: `unit-a-f`, `unit-g-o`, `unit-p-z`
    (letter ranges of `tests/unit/`), `integration`, `acceptance`.
    `tests/unit/test_ci_contracts.py` expands those paths over the tree and fails
    on a test file no shard runs or a file two shards run.
  * The matrix is **sized to the portability question**, not run five times over
    (T-0105). The question is "does the suite work on the Python versions and the
    OSes this project supports", and the interpreters that answer it are the
    boundaries: 3.11 (`requires-python`'s floor) and 3.13 (the newest
    classifier). Those two Linux cells run every test, 3.11 under the coverage
    gate. The interior Linux interpreter (3.12) and macOS run the subset
    `tests/unit tests/acceptance`, and macOS adds the one integration module the
    portability question is about there: `tests/integration/test_portability_flow.py`
    runs the spaced-path CLI invocation, the symlink/WinError-1314 guard and the
    GNU-make guard as real subprocesses, on a host other than the one the code was
    written on, so macOS is one of the hosts it exists for. The unit tree's
    `tests/unit/test_portability.py` (over `src/teamwork/portable.py`) and
    acceptance are the cheap proof of the ACs; the rest of the subprocess-heavy
    integration tree (338 tests, 30% of the serial wall clock) runs on both
    boundary interpreters and on the five Windows shards, and no test in the tree
    branches on darwin.
    `tests/unit/test_ci_contracts.py` pins each subset in `SUBSET_CELLS` (a
    cell-to-paths map) with `SUBSET_PATHS` and `PORTABILITY_FLOW`, fails when a
    boundary cell stops running the whole suite or a subset cell drops one of the
    portability contracts, and expands the subset tokens over the tree.
  * Every cell except the Windows shards runs pytest under `--numprocesses=auto` (`-n auto`)
    (`pytest-xdist`, a `dev` extra requirement; T-0105). The suite spawns hundreds
    of processes and a hosted runner gives 3-4 vCPUs, so a cell is wall-clock
    bound rather than CPU bound: measured on the 4-worker emulation of a runner,
    the same tree takes 242s serially and 94s with `-n 4` (4-worker emulation of a
    hosted runner, T-0105), and the two runs reproduce the same outcome: at
    `faeafce` both gave 2742 passed, 2 failed, 10 skipped (Reviewer-2, P-0150). At
    this revision the tree collects 2763 tests and the parallel run gives 2751
    passed, 2 failed, 10 skipped in 36s - the one extra test against `faeafce` is
    the macOS-subset mutant this change adds. The 2 failures are not the parallel
    run's: they are `tests/integration/test_memory_pack_flow.py`, which landed red
    on `main` from T-0097 with a P0 fix task open, and they fail identically
    single-process. The macOS cell's subset takes 22s here (Linux host, `-n auto`,
    2427 passed, 8 skipped) against the 12-18 minute full-suite job it replaces;
    the duration on a macOS host is the CI run's to report. The Windows rows are
    already split by path, so a second split buys nothing there.
  * The `scope` job runs `scripts/ci_scope.py`, which computes the changed-path
    set from git, and publishes **two** outputs, because the filtered jobs ask two different questions and a
    prose-only push answers them differently: `code` (`true` = something that
    ships changed) and `prose` (`true` = something in the prose/media set below
    changed). On a prose-only push `code=false` and `prose=true`, so the jobs
    keyed off `code` skip while the prose-relevant gates still run.
    * Keyed off `code` **alone** - `lint`, `typecheck`, `test`, `build` - with
      `needs: scope` and
      `if: github.event_name != 'push' || needs.scope.outputs.code == 'true'`.
      These are the jobs a prose change cannot affect, and the ones a
      prose-only push must not burn.
    * Keyed off `code || prose` - `privacy` and `docs` - with `needs: scope`
      and
      `if: github.event_name != 'push' || needs.scope.outputs.code == 'true' || needs.scope.outputs.prose == 'true'`.
      Both are prose-relevant gates: a documentation leak is still a leak, so
      the privacy scan reads prose as well as code, and the `docs` job is the
      link health plus `mkdocs build --strict` build of the very pages a prose
      push edited. Keyed off `code` alone they would be skipped on exactly the
      push that edits documentation.
    * Every `pull_request` (and every `workflow_dispatch`) runs the full set: a
      path-filtered skip reports no check at all, and a required check that is
      never reported blocks the merge.
    * A **tag push** (`v*`) is neither a code change nor a prose change: the
      tagged commit already passed the matrix as a `main` push and
      `release.yml` re-runs pytest on the tag, so `scope` reports `code=false`
      and `prose=false`. What still runs is the `scope` classifier and the two
      jobs that declare neither `needs:` nor `if:` - `committer-guard` and
      `release-consistency`. That is the consistency gate *and* the committer
      guard, not the consistency gate alone: `scope` can skip only the jobs
      that declare `needs: scope`, and every job without that declaration runs
      on every event.
  * The prose/media set the classifier uses is `docs/**`, `assets/**` and the
    root prose files `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
    `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, `LICENSE`, `AGENTS.md`
    and `mkdocs.yml`. This set is what the classifier's prose list
    (`scripts/ci_scope.py::prose_paths`, run by the `scope` job) matches to
    raise the `prose` output, and it and `.github/workflows/docs.yml`'s
    `paths:` list **must stay identical** - a path that leaves one list without
    joining
    the other is a hole in one of the two gates. The identity is checkable
    without a stored count: expand the classifier's prose list and the
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
`1c730d6` (parent `1c730d6`), reproducible with
`git show 1c730d6:scripts/check_release_consistency.py`. Whether that
implementation is in the tree you are reading is a question with a command,
not a sentence: the checker file is in the tree when
`git ls-tree HEAD scripts/check_release_consistency.py` prints a line, and the
implementation is in the tree when `git merge-base --is-ancestor 1c730d6 HEAD`
exits `0`. Against that code:

| Clause | Status | Where |
|---|---|---|
| 11.3 - on the local side the payload always comes from a git object; `rev=None` means `HEAD` | **implemented** | `1c730d6` `payload_digest` (`revision = "HEAD" if rev is None else str(rev)`) |
| 11.3 - link policy, all five cases, every refusal exit `2` | **implemented** | `1c730d6` `_extract_tar` / `_link_target` / `_materialise_links` |
| 11.3 - an unreadable payload file and an unresolvable link are input errors (exit `2`) | **implemented** | `1c730d6` `_digest_of_files` (`unreadable payload file`) and the link refusals |
| 11.2.2 - R2's tag set `S = A - O` (reachable version tags, minus the tags at `HEAD`) | **implemented** | `1c730d6` `rule_r2_head_is_newer` uses `_reachable_version_tags` and `_tags_at_head` |
| 11.2.2 - the `detail` counts `|S|`, never a negative number | **implemented** | the same function reports `is newer than {len(comparable)} tag(s)` over `S` |
| 11.2.2 - a shallow or tag-less checkout is exit `2` | **implemented** | `1c730d6` `_complete_tag_set_error` (`git rev-parse --is-shallow-repository`) |
| 11.2.4 - the frozen `TAGGED_TOKEN` regex | **implemented** | `1c730d6` `TAGGED_TOKEN` is the regex block of 11.2.4, verbatim |

Every row of the table names a symbol in `1c730d6`, so the "implemented" column
is re-derivable instead of a status word: for a row whose symbol is `<name>`,
`git show 1c730d6:scripts/check_release_consistency.py | grep -c "<name>"`
prints `1` when the row is implemented and `0` when it is not.

Everything section 11 freezes is therefore implemented in the revision
`1c730d6`; whether that revision is in the tree the reader is holding is a
question with a command - `git merge-base --is-ancestor 1c730d6 HEAD` exits `0`
when it is - and not a property of the document. The two amendments this
section introduced into the contract (`rev=None` and the link policy) were
implemented first, at `1c730d6` (`git merge-base --is-ancestor 1c730d6 HEAD`
exits `0` when that is in the tree too); R2's `S = A - O`, the shallow guard and
`TAGGED_TOKEN` followed at `1c730d6`. The third amendment, that a published version which is
not `X.Y.Z` is DRIFT unless a 11.4 entry admits it (`T-0016`), lands at
`37ef0ed`: `git show 37ef0ed:scripts/check_release_consistency.py | grep -c
PUBLISHED_VERSION` prints `2` when it is in that revision. The table exists so
that a reader of section 11 does not read it as a changelog of the repository:
**the contract is the target, and each row names the revision that implements
it**.

One subsection is deliberately the exception: 11.2.2.1 is an amendment accepted
at D-20261029-Architect and is **not** implemented at `1c730d6` or at the revision
this paragraph was written. It carries its own implementation spec and the exact
tests; developer task T-0032 implements it, and no row of the rule table above
claims it is green until that revision lands - a reader can tell a frozen target
from a shipped one.

### 11.1 CLI (frozen)

| Flag | Default | Meaning |
|---|---|---|
| `--offline` | on when no flag is given | no socket is opened; rules that need a registry print `SKIP` |
| `--online` | off | the registry/API rules (R3, R4, R5, R8) query npm, the GitHub API and PyPI |
| `--json` | off | emit the JSON object of 11.1.3 instead of the table |
| `--exceptions PATH` | `<repo-root>/release-exceptions.json` | the exception record of 11.4; a relative path resolves against `--repo-root` |
| `--repo-root PATH` | the current directory | every path and git call is rooted here (tests point it at a fixture tree) |
| `--head-is-default-branch {yes,no}` | `yes` | whether the checkout under test is the default branch, i.e. whether its version is a published claim; `no` makes R2 report `SKIP` instead of being evaluated (11.2.2.1, amendment [D-20261029-Architect](Decisions.md#d-20261029-architect---r2-evaluates-the-published-line-the-release-order-still-owes-one-bump-per-tag)) |

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

* Python **3.11+**, standard library only, no third-party import, no `subprocess`
  shell, with `from __future__ import annotations` kept as the one lazy
  annotation convention. It is linted and formatted like the engine (`ruff
  check`, `ruff format --check`).

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
| R2 | `version.py` at HEAD | the version tags **reachable from HEAD**, minus those that point at HEAD (`S`, 11.2.2) | the HEAD version is not **strictly greater** than some version in `S` | evaluates on the default branch, `SKIP` elsewhere (11.2.2.1; needs the complete tag set, 11.2.2) |
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
replaces (`1c730d6:891-899`) compared HEAD against **every** version tag in the
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

#### 11.2.2.1 R2's scope: the published line (amendment, [D-20261029-Architect](Decisions.md#d-20261029-architect---r2-evaluates-the-published-line-the-release-order-still-owes-one-bump-per-tag))

R2 asks one question about what this repository **publishes**: is the version in
`version.py` ahead of the newest release on its own line of history? A feature
branch, a pull-request merge ref and a lane work tree publish nothing, so the rule
is evaluated where a version is actually published - the default branch, and a tag
push, which is `ok` there by construction - and reports `SKIP` on every other
checkout:

* **When the checkout is the default branch** - a `push` to `main`, or a local run
  that says so - 11.2.2 above applies **unchanged**: `S = A - O` over the version
  tags reachable from HEAD, DRIFT iff HEAD's version is not strictly greater than a
  tag in `S`, and the `detail` names each such tag.
* **Off the default branch** - a pull-request merge ref, a feature branch, a lane
  work tree - R2 prints
  `R2 SKIP not the default branch: the published line is evaluated on main only`
  and contributes no finding. It is a `SKIP`, never an `ok` - nothing was proved,
  and the detail says why (11.1.2). The exit code stays `0` while no other rule
  drifts: 11.1.1 already admits a `SKIP`, and this is not an unreadable input, so
  no exit code is redefined by this amendment.

A `v*` tag push is **not** scoped out and needs no flag: the tag is the published
artefact, `O` contains it, so R2 is `ok` there by construction (11.2.2's first
table row) - and leaving it evaluated keeps the catch for the one case that
matters, a tag placed on an older commit, which is DRIFT.

The scope is a **stated input, never a guess**: `--head-is-default-branch=yes|no`
(11.1) carries it, and its default is `yes`. A run that says nothing - including a
workflow that forgets the flag - evaluates the frozen rule, so this amendment
**cannot make a gate green by omission**; the worst a mistake can do is leave the
old false red. A shallow clone still exits `2` through R1, R4 and R5, which keep
the complete-tag-set requirement, so scoping R2 cannot hide a blind checkout.

**The invariant is not loosened.** On the default branch a commit on top of the
newest tag without a version bump is still DRIFT, exactly as 11.2.2 says, and the
tests below measure that pair rather than asserting it in prose.

**Why the scope cannot be finer.** R2 has exactly two coherent scopes, and there
is no third. A rule that evaluates a pull-request checkout's own version flags
every branch cut from a tagged-but-unbumped `main` by arithmetic: the branch's
version *equals* the newest reachable tag, `O` does not contain that tag, so `S`
is non-empty and the comparison is `X <= X`. Refinements that compare the head
with its base ("did this pull request introduce the drift?") do not help, because
the first branch commit after a tag is precisely the one that introduces it, and a
rule that blocks that commit either deadlocks the bump that would clear it or
re-creates the same red. The false red is measured, not argued: CI run
40778031671 (a `push` to `main`) failed on
`R2 DRIFT HEAD version 1.4.1 is not greater than tag v1.4.1`, run 40789321527 (a
`pull_request`) failed on `R2 DRIFT HEAD version 1.4.2 is not greater than tag
v1.4.2`, and `T-0017` cleared it for one release by bumping to `1.4.3` - which is
the definition of a hope, not a gate. The same invariant is implemented a second
time as a test assertion (`tests/unit/test_release_traceability.py`, "the tag of
the current version is HEAD"), so a change that scopes R2 and not that assertion
leaves the trap red in the `test` matrix.

**What is *not* changed.** R1, R3, R4, R5, R6, R7, R8 and R9 are untouched; the
exit-code precedence `2 > 1 > 0` (11.1.1) is untouched; `_complete_tag_set_error`
is untouched; and the `detail` strings of the frozen rule are untouched, so no
consumer that reads them needs a second source of truth.

**Implementation spec (a developer task, filed by the CEO).**

| file | change |
|---|---|
| `scripts/check_release_consistency.py` | `rule_r2_head_is_newer(repo_root: Path, head_is_default_branch: bool = True)` returns `_skip("R2", "not the default branch: the published line is evaluated on main only")` **before** it reads HEAD's version or the tag set; `main()` adds `--head-is-default-branch` (`choices=("yes", "no")`, `default="yes"`) and passes `args.head_is_default_branch == "yes"`; the module docstring states this subsection |
| `.github/workflows/ci.yml` | the `release-consistency` gate passes `--head-is-default-branch=no` when `github.event_name == 'pull_request'` and `=yes` otherwise - one `env:` entry and one flag in the existing `run:` block, no second invocation and no re-implementation of the rule in shell |
| `.github/workflows/release.yml` | **no change**: both call sites run on a `v*` tag push, which stays evaluated by the default, so the release build keeps R2's catch for a tag placed on an older commit |
| `docs/Team/Release.md` (Release Engineer) | line 26's `--range <before>..<head>` becomes the change-set rule of [D-20261029-Architect](Decisions.md#d-20261029-architect---r2-evaluates-the-published-line-the-release-order-still-owes-one-bump-per-tag), and the forward-looking sentence of "Closed: R2 was red off the release tag" ("the next release must bump the version before it tags, or every lane after that tag pays this again") becomes the amended scope plus the release order, because after this amendment the lanes do not pay - `main` does, until the bump lands |

Tests, in the order a reader should run them:

1. `tests/unit/test_release_consistency.py` - five additions:
   * `test_r2_off_the_default_branch_is_a_skip_and_not_an_ok`: the trap as a
     fixture (tag `v1.1.0` at the first commit, a second commit with no bump);
     `rule_r2_head_is_newer(root, head_is_default_branch=False)` returns
     `status == "SKIP"` and a detail containing `not the default branch`.
   * `test_r2_on_the_default_branch_at_a_tag_with_no_bump_is_still_drift`: the
     same fixture with the default argument returns `DRIFT` naming `tag v1.1.0`.
     This pair is the no-loosening proof, and a mutant that returns `ok` for both
     turns it red.
   * `test_the_scope_flag_changes_nothing_but_r2`: a fixture whose only finding is
     an R9 drift, run with `--head-is-default-branch=no`, still exits `1` with the
     R9 finding present and R2 `SKIP`.
   * `test_json_mode_reports_the_scope_skip_and_exits_zero`:
     `run_main(["--offline", "--json", "--head-is-default-branch=no"])` exits `0`,
     `rules[1]` is `{"id": "R2", "status": "SKIP", ...}` and `problems == []`.
   * `test_a_third_value_for_the_scope_flag_is_a_usage_error`:
     `--head-is-default-branch=maybe` exits `2`, prints a usage line on stderr and
     nothing on stdout.
2. `tests/unit/test_release_traceability.py` - **migration, not deletion**: the
   existing assertion keeps its first half (the current version is never excepted)
   unconditionally and scopes the second half (the tag of the current version is
   HEAD) through one helper `published_line()`: `GITHUB_EVENT_NAME ==
   "pull_request"` is false; a `GITHUB_REF` under `refs/heads/` is true iff it is
   `refs/heads/main`; one under `refs/tags/` is true; outside CI it is
   `git symbolic-ref --short -q HEAD` printing `main`, or a tag pointing at HEAD.
   A table-driven unit test pins all five cases with `monkeypatch.setenv`, so the
   scope is a tested predicate rather than a skip that hides.
3. `tests/unit/test_ci_contracts.py` - two tests: every `pull_request`-triggered
   step that invokes `check_release_consistency.py` names
   `--head-is-default-branch=no` (walk `jobs[*].steps[*].run` through
   `workflow_yaml.parse_workflow`), and the `release-consistency` job passes `yes`
   on the non-pull-request arm so both arms are greppable. The mutant twin flips
   the two literals and the second test goes red.
4. `tests/integration/test_ci_release_flow.py` - no edit expected: its existing
   probe runs every workflow-invoked script with `--help` and fails on an
   undocumented flag, so the flag must appear there; the implementer confirms the
   file is still green instead of assuming it.

The developer task must contain, at minimum: the three files this decision owns and
no fifth; 11.2.2.1's rule text verbatim as the acceptance; the no-loosening pair as
two tests; a mutant that flips the flag's default to `no` and must turn the
default-branch DRIFT test red; a run of `check_release_consistency.py --offline` on
`main` that is still `0 problem(s)`; and the implementation-table row below section
11 naming the revision that lands it. Until that revision exists, **no table row
claims this subsection** - that is the table's own rule, not an omission.

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
exclusion), `1.1.2` gives `a01d9f0cbee641c3` = the payload of commit `a5b0cd6`,
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
| 1 | npm `1.1.2` payload digest `a01d9f0cbee641c3` equals the bundled-payload digest of commit `a5b0cd6` | `v1.1.2` must be tagged **at `a5b0cd6`**; then R1, R3, R5 hold for it and R2 forces the next `version.py` bump <!-- release-consistency: illustrative --> |
| 2 | npm `1.1.1` payload digest `726bc547afc41ead` matches **no** commit in `git rev-list --all`; its `version.py` sha256 `545fc1605b3997460a1cf348562c43fed5a8315c83ac8291f9cbf4078703d36d` appears in no commit | `1.1.1` is the 11.4 exception entry, never a tag: there is no commit to tag, so a tag would be a lie the digest can prove <!-- release-consistency: illustrative --> |
| 3 | npm `1.1.0`, mapped per 11.3.1 and excluding `scripts/build_pi_package.py`, gives `ebfc2538e3d3d605` = tag `v1.1.0`; **including** that file the same comparison gives `acec49f6cd1fe99a` for the tarball vs `cd43f09293a49c68` for the tag, and they differ only in that file | the payload comparison must map the paths (11.3.1) and exclude that file (11.2.3), or a green release reads as drift <!-- release-consistency: illustrative --> |

Commands behind the numbers (reproducible from any checkout): the three
tarballs were fetched with `npm pack @nidvue/teamwork@<version>` into a temporary
directory, unpacked, mapped per 11.3.1 and hashed per 11.3; the local side is
`payload_digest(root, "a5b0cd6")` and `payload_digest(root, "v1.1.0")`. The
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
- C3 is summed over every role directory, because the command is not scoped to
  one instance. It counts only `ShortTermMemory.md`: the one memory file startup
  loads into context (`D-20261102-Architect-C3`). Long-term memory, the task queue,
  the archive and the global memory are on-demand and sit outside this registry.
- `role` is the owner of that path under section 2, or `-` where section 2
  assigns none.
- exit code 0.

| C | Harness^2 component | `path` spec | `class` | `role` |
|---|---|---|---|---|
| C1 | system prompt | `SKILL.md` | always-on | ceo |
| C2 | guardrails | managed block in `AGENTS.md` | always-on | ceo |
| C3 | memory | `Roles/<Role>/ShortTermMemory.md` | always-on | - |
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
| `PREFIX` | a `.agents/skills/<dir>/SKILL.md` has no frontmatter `name:` line, or `<dir>` does not start with `tw-`; one finding per file, detail naming the offending value (section 14) |
| `TRIGGER` | the skill name appears in no always-on surface (`AGENTS.md`, `SKILL.md`, `roles/*.md`) |
| `SUBCOMMAND` | a `teamwork.py <word>` in a skill file names a command the parser does not register |
| `HELPER` | a repo-relative path a skill file references does not exist |
| `EVIDENCE` | a `status: shared` skill carries no `verdict: helped\|hurt\|no observed effect\|confounded` |

Output, one line per finding, in rule order `IDENTITY`, `PREFIX`, `TRIGGER`,
`SUBCOMMAND`, `HELPER`, `EVIDENCE` and sorted by path within a rule:

```text
- PROBLEM <RULE> <path>: <detail>
# problems found: N
```

`--verbose` also lists every file checked. `EVIDENCE` is skipped when no
workspace exists, because `Skills.md` lives in the team tree; the other five
rules are pure tree checks and always run. The `SUBCOMMAND` vocabulary is the
parser itself, never a list (D-20261020-Architect-3).

The `TRIGGER` rule fired on this tree before the skill had a trigger line:
`tw-ceo-audit-close` appeared in no always-on surface. That was a true positive
(a skill with no trigger line), fixed in the always-on text that the CEO owns,
never by weakening the rule.

### 12.5 `harness budget`

One line per instance, then one total line, same four columns with `total` in
the first:

```text
<instance>  <always_on_bytes>  <budget_bytes>  <ok|OVER>
total       <sum_bytes>        <budget_bytes x instances>  <ok|OVER>
```

- `always_on_bytes` = managed `AGENTS.md` block + `SKILL.md` + that role's
  charter + that role's short-term memory (`ShortTermMemory.md`, C3). The unit is **one instance**, never the roster.
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
pre-push    <installed|absent|foreign>[(chained: <stage>.teamwork-foreign)]
# hooks directory: <the directory the resolver returned>
```

The hooks are per **common git dir**, so installing from any lane worktree
installs for every worktree of that repository at once.

Mode `0755`, LF endings, and exactly this body:

```sh
#!/bin/sh
# teamwork-managed hook (stage: pre-commit) - remove with: teamwork.py hooks uninstall
# the hook file lives in the git dir; the rules act on the work tree below
# local only: `--no-verify` and a core.hooksPath pointing elsewhere skip this
# file, and a clone that never ran `hooks install` has none of it - the
# forge-side rule covers those, so this hook is never the whole control.
[ -n "${TEAMWORK_SKIP_HOOKS:-}" ] && exit 0
root=$(git rev-parse --show-toplevel)
if [ -z "$root" ]; then
  echo "teamwork: pre-commit hook: cannot resolve the work tree root (git rev-parse --show-toplevel failed); refusing rather than skipping the guard. Bypass deliberately with TEAMWORK_SKIP_HOOKS=1." >&2
  exit 1
fi
# -f, not -x: scripts/teamwork.py is committed 100644, so an executable-bit
# test would turn every hook into a silent no-op in this repository
if [ ! -f "$root/scripts/teamwork.py" ]; then
  echo "teamwork: pre-commit hook: $root/scripts/teamwork.py is missing, so the rules cannot run; refusing rather than failing open. Restore the file, run 'teamwork.py hooks uninstall', or bypass deliberately with TEAMWORK_SKIP_HOOKS=1." >&2
  exit 1
fi
exec python3 "$root/scripts/teamwork.py" hook pre-commit "$@"
```

with `pre-push` and `hook pre-push` in place of `pre-commit` in the stage lines.
That body is `hooks.py shim()`, verbatim at the merged revision
(`git show main:src/teamwork/hooks.py`); three constructs in it are contract, not
detail (`D-20261020-Architect-9`, amended by `D-20261029-Developer-16`):

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
- **`exit 1`, never `exit 0`, on both failure paths.** `root=$(git rev-parse
  --show-toplevel)` stays unredirected - the contract has **no** `2>/dev/null` on
  that call - and a failed resolution or an absent engine file now refuses with a
  message naming `TEAMWORK_SKIP_HOOKS`. The superseded `|| exit 0` form meant a
  renamed engine or a broken checkout disabled every rule while `hooks status`
  still reported `installed` (security audit F-6, `D-20261029-Developer-16`).

A stage whose hook belonged to someone else keeps that hook. `install` moves it to
`<stage>.teamwork-foreign`, takes the stage, and writes this second body, which
runs the rules first and the preserved hook second - the file it replaced is not
ours to delete (`git lfs install` owns `pre-push` in a fresh clone, and the
all-or-nothing installer this replaces refused BOTH stages because of it):

```sh
# this stage had a foreign hook when teamwork installed over it: it is kept
# beside this file as pre-push.teamwork-foreign and runs after the rules pass
hook_dir=$(cd "$(dirname "$0")" && pwd) || exit 1
chained="$hook_dir/pre-push.teamwork-foreign"
if [ ! -f "$chained" ]; then
  echo "teamwork: pre-push hook: the preserved pre-push.teamwork-foreign it was installed to chain is gone; refusing rather than silently dropping that hook. Re-run 'teamwork.py hooks install', or remove this hook with 'teamwork.py hooks uninstall'." >&2
  exit 1
fi
# git hands pre-push the refspec list on stdin and BOTH hooks need it: copy it
# once, then feed each hook from the copy
refspecs=$(mktemp "${TMPDIR:-/tmp}/teamwork-pre-push.XXXXXX") || {
  echo "teamwork: pre-push hook: cannot create a temporary file for git's refspec list; refusing rather than starving the chained hook." >&2
  exit 1
}
trap 'rm -f "$refspecs"' 0
cat > "$refspecs"
python3 "$root/scripts/teamwork.py" hook pre-push "$@" < "$refspecs"
# a refusal from the rules stops here: the chained hook must not run for a
# commit or push that already failed
status=$?
if [ "$status" -ne 0 ]; then exit "$status"; fi
"$chained" "$@" < "$refspecs"
status=$?
exit "$status"
```

preceded by the same head, and with `pre-commit` in place of `pre-push` for the
non-stdin stage; the preserved file is found through this file's own directory,
which is the hooks directory whatever path git used to reach it. The rules run
before the chained hook, so a refused commit or push never reaches it, and the
refspec list is copied once because a stream can only be read once: piping it to
the first hook would hand the second one an empty list. `hooks.py shim(stage,
chain=True)` is that body, verbatim.

| Rule | Contract |
|---|---|
| marker | one constant, `config.HOOK_MARKER = "teamwork-managed hook"`, rendered **as one line 2**: `# <marker> (stage: <stage>) - remove with: teamwork.py hooks uninstall`. `install` (the force check), `status` and `uninstall` all key on that one constant; a hook file without it is `foreign` and is never overwritten or removed without `--force` |
| escape | a set (non-empty) `TEAMWORK_SKIP_HOOKS` exits 0 before anything else; the bypass is documented, never silent |
| local only | `git commit --no-verify`, `git push --no-verify` and a `core.hooksPath` that points elsewhere all skip these files, and a clone that never ran `hooks install` has none of them: the forge-side rule (branch protection / ruleset) is what covers those paths, and the hook is never described as the whole control |
| root | the shim resolves the project root with `git rev-parse --show-toplevel`; the rules act on the work tree, the file lives in the git directory |
| engine | `python3 "$root/scripts/teamwork.py"`; an absent engine file is a refusal with a message naming `TEAMWORK_SKIP_HOOKS`, never a silent pass, and never a guessed command |
| install | **per stage**, each stage installed on its own so a foreign hook on one stage cannot block the other, exit 0 when both land. A foreign hook is preserved as `<stage>.teamwork-foreign` and chained, never deleted. `--force --reason <why>` replaces it instead and records the reason; `--force` without a reason is refused. A stage that could not be installed leaves the others in place and makes the run exit 1 |
| status | `<stage> <installed\|absent\|foreign>`, with ` (chained: <stage>.teamwork-foreign)` when a preserved hook runs after the rules, then the literal `# hooks directory: <path>` line naming the directory the resolver probed, exit 0 |
| uninstall | resolves through the same `hook_dir(root)`, removes only marked hooks, hands a preserved `<stage>.teamwork-foreign` back its own name, and leaves a foreign hook alone and says so, exit 0 |
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

## 13. Feature teams (frozen design; engine support in T-0042)

Owner: Architect. This section freezes the **feature-team surface** that
`D-20261029-CEO-2` authorised and T-0042 lands in the engine. The constitution
surface (`SKILL.md`, `roles/`, `references/`, `templates/`) belongs to the CEO;
what is frozen here is only the part the engine must honour, so a lane can build
it and a Tester can assert on it.

**Measured baseline at `2b3cd30`** - none of this is implemented yet, and the
section says so rather than describing an engine that does not exist:
`config.ROLE_PARENT` has 15 roles and no `team-leader`; `reporting_children("cto")`
is `architect, data-engineer, developer, release-engineer, tester`;
`config.TEST_LAYERS` has 15 layers and `feature` is not one of them, so
`tests add --layer feature` dies today; a task record has no `feature` field
(`records.new_task`) and an instance has no `under` field; `config.DOCS` does not
register `Features.md`; `teamwork.py feature` is not a subcommand. Until T-0042
lands, `feature` is a document and a rule, not a command.

### 13.1 The feature record

A **feature** is one vertical slice one squad can build, test and ship without
another squad's merge. It is a record, not a conversation: everything below is a
field of that record, in that order.

| Field | Exact meaning | Written by | Refused (exit `2`) when |
|---|---|---|---|
| `id` | `F-nnnn`, four digits, allocated by the command as **one more than the highest `nnnn` among the records visible at the caller's revision** (the read path below), starting at `0001`. There is no counter file and no reservation: a refused `add` writes nothing and consumes nothing, so the next successful `add` from that revision offers the same number. An id is never reused - a `done`/`dropped` id stays taken - and a landed record's id never changes; the one id a merge may change is the duplicate of 13.3 rule 5, renumbered **before** that record lands, so a record lands once with one id | the command | - |
| `statement` | one line: what ships, phrased as the slice's user-visible result | the owner | empty. A second feature stating the same thing is **not** a refusal: `add` prints `teamwork: F-0001 already records that statement - not duplicated` and exits `0` |
| `owner` | **exactly one** `team-leader` instance; the squad's only manager | the owner, checked by the command: at `add` it must **be** the caller | an instance that is not a `team-leader`; a role with no instance; an `--owner` naming any instance but the caller; a second open feature on the same owner (throughput rule 2) |
| `interface` | the **frozen-interface reference**: an anchor in this file (`Architecture.md#13`) or a decision id (`D-20261029-Architect-2`) | an `architect` caller, at `add` or on any `set` edit; the command writes `-` when the caller does not set it | an anchor/decision that does not resolve; a caller whose role is not `architect`; and `-` **on the transition to `ready`**. `-` is legal at `add` and for the whole of `proposed` - that is the state every record is created in (13.2) - so a record waiting on its freeze is a record with `interface=-` |
| `paths` | comma-separated **owned writable paths** - the feature's whole write set | the owner proposes, the command validates (13.3) | any overlap with another open feature, a glob, a generated artifact, checkout state, or a path outside the repository by the containment rule of 13.3 (syntactic: nothing is `stat`'ed) |
| `depends-on` | comma list of `F-nnnn` **work** dependencies, or `-` | the owner | an unknown id, itself, or a target whose state is not `done` (13.3) |
| `state` | `proposed` -> `ready` -> `active` -> `done`; `dropped` from `proposed`/`ready`, and from `active` once every task carrying `feature: F-nnnn` is terminal (`done` or `dropped`); `done` and `dropped` are terminal | the command, on `feature set` (13.2): `ready` by an `architect` caller only, every other transition by the record's `owner` instance | an unknown value; `ready` while `interface=-`; `done` while any task carrying `feature: F-nnnn` is not `done`; a state skipped forward; any transition out of `done`/`dropped` |
| `created`, `updated` | ISO dates, the same audit pair every record carries | the command | - |

**Where it lives: one file, `docs/Team/Features.md`, and one authority per row.**
The independence rule of 13.3 is a predicate over **all open features at once**.
Split the records one file per team and the only way to evaluate it is N unlocked
reads, so no single read answers the question at all and two leaders can each
"win" their own check without either having seen the other. So the records are
one file - and the one-owner-per-artifact rule (throughput rule 3) is kept by
naming the **field authority** (13.2), not by proxying the pen:

- the row belongs to the feature's `owner` (its `statement`, `paths`,
  `depends-on`, and the `active`/`done`/`dropped` transitions); the `interface`
  and the `ready` transition belong to the **Architect**; the id, the timestamps
  and every validation belong to the command. One authority per field, and the
  freeze is never written by the lane that will work from it;
- the **Project Manager** owns the record *set* - duplicate-statement
  detection, the dependency graph, and the map of which feature owns which path - and
  `Features.md` is registered in `config.DOCS` with owner `ProjectManager`, so
  `teamwork.py map` lists it with every other one-owner document and no second
  lane claims it. Owning the set is not holding the pen: the caller the command
  authorises runs it (13.2), and the PM reads the same one file;
- the Architect's **policy** stays in this section and the record only *names*
  the interface, so the ownership map has one normative source (these rules) and
  one data file (`Features.md`) and never two.

**The file is an ordinary committed document: the caller commits its own edit on
its own branch, and the merge lands it** - the path `decision add` already walks
for `docs/Team/Decisions.md`. That is the *branch* question, which the
*authority* question above does not answer:

- `feature add` and `feature set` write `docs/Team/Features.md` in the **caller's
  checkout**, with `atomic_write` under `Runtime/Locks/features.lock` (the
  same-checkout lock `decision add` takes on `decisions.lock`), and the caller
  commits that edit on its own branch, as `AGENTS.md` BRANCH PER AGENT requires.
  No command commits on the base branch and nothing here asks for the bypass:
  12.7's R1 (`src/teamwork/hooks.py:503-514`) refuses any commit whose `HEAD` is
  `config.DEFAULT_BASE`, so `TEAMWORK_ALLOW_MAIN` is not part of this design and a
  base-branch checkout is not a precondition. It could not be one: in every lane
  worktree `git branch --show-current` is that lane's branch, never the base;
- the Reviewer's merge (REVIEWER-ONLY MERGE) lands the record the way it lands
  every other document, and a conflict in `Features.md` is a **document
  conflict**: the merging Reviewer resolves one row against another exactly as it
  resolves any other doc. No command picks a winner, and no lock has to serialise
  two worktrees - the lock above is scoped to one checkout and is not offered as
  cross-worktree mutual exclusion;
- **`feature check` and `feature list` answer from the records visible at the
  caller's revision**: the caller's working copy when its branch carries one,
  else `git -C <root> show HEAD:docs/Team/Features.md`. The answer is dated on the
  header line, and the token is the honest one: `@ <short-sha>` when the working
  copy is **clean**, so the bytes read are exactly that revision's, and
  `@ worktree` when it is not - an uncommitted row or edit (the caller's own
  `feature add` before it commits) is at no revision, and printing `HEAD` for it
  would date the answer to a commit that does not contain the row. The `--json`
  `rev` carries the same token. When neither copy exists the read path exits `1`;
- **the consequence for the independence check, stated.** A lane whose branch
  predates another feature's record does not see that record, so its own
  `feature check` can be green while the merged tree is red: this is a per-branch
  read and not a lock across worktrees, and claiming otherwise is the claim F5
  charged. It is caught at the one place that sees both records - the **merge
  path**: T-0042 runs `feature check` at the merged tree before the Reviewer's
  `pr merge` completes, so a merge that would land a second claim on a path is
  refused with the frozen rule-1 finding instead of landing. The cheap prevention
  stays the lane's own: rebase before `feature check`, and read `@ <short-sha>`
  to see which revision answered.

**What the one-file choice costs, and why it is still the right file.** A feature
row is **mutated in place** - `state`, `paths`, `updated` - whereas `Decisions.md`
is append-only: a per-branch copy of that file merges by concatenation, because
the ids are made unique across every branch for exactly that reason (T-0038). Two
mutations of the same feature row cannot be merged by appending; they are the
document conflict of the second bullet above, and the merging Reviewer settles it.
Section 13 accepts that cost with its eyes open: the alternative - a second writer
on `main` - is refused by the project's own R1 gate, and a contested merge is
decided by the frozen predicate, which the merge path runs.

### 13.2 CLI semantics (frozen)

```text
teamwork.py feature add <statement> --owner <team-leader> --paths <p[,p...]>
                        [--interface <ref>] [--depends-on <F-nnnn[,F-nnnn...]>]
                        --by <instance> [--json]
teamwork.py feature set <F-nnnn> --state <state> [--interface <ref>]
                        [--paths <p[,p...]>] [--depends-on <F-nnnn[,F-nnnn...]>]
                        --by <instance> [--json]
teamwork.py feature list [--state <state>] [--json]
teamwork.py feature check [<F-nnnn>...] [--json]
```

`--paths` is required and non-empty: a feature that owns no path cannot be
independent of anything, it is a plan, not a slice. `--by` is **required on
`add` and `set`**: it is the caller naming itself, and `feature` has no default
for it (below). A missing required flag is argparse's usage error, the same for
every verb in the engine, and is not part of the refusal vocabulary.

`--interface` has **one reading, at `add` and on `set` alike**: it is optional and
`-` by default; `-` is legal for the whole of `proposed` and refused on the
transition to `ready`; and a non-`-` value must resolve to an anchor or a decision
id and is the **Architect's** field, so it is refused (`2`) unless the caller is
an `architect` instance. A record is created in `proposed` *because* its interface
is not frozen yet, so `add` with no `--interface` and `add --interface -` are the
same record, and a leader that is not the Architect cannot create one carrying a
freeze it did not issue.

`add` has **no `--state`**: a record whose first state is `ready` would be a
transition hidden inside a create, and the refusals below would then have two
implementations. Every state change is `feature set`.

**`add` files the leader's own slice**: `--by` and `--owner` must name the same
`team-leader` instance, so `statement` and `paths` are written by the field
owner (13.1) from the first line of the record and no lane can file a slice on
another leader's behalf. The redundancy is the assertion: `--owner` is the record
field, `--by` is the caller, and the command refuses them disagreeing.

**`feature set` is the one transition verb**, and it is the only way a record
leaves `proposed`. `--state` is required and names the state the record should
**end in**; naming the state it is already in is a record edit and prints the pair
with nothing after it - `teamwork: features ~ F-0003 [ready] -> [ready]`:

| Transition | Who may issue it (the caller, `--by`) | What it releases |
|---|---|---|
| `proposed` -> `ready` | a caller whose resolved role is `architect` - the freeze is the Architect's (13.5); the shared Architect is one role, so any of its peers may freeze | the record enters the **open set**: `feature check` starts comparing its `paths`, `task add --feature F-nnnn` accepts the id, and `pulse` prints its team line. Nothing executes yet |
| `ready` -> `active` | a caller whose resolved instance **is** the record's `owner` (the leader; a squad instance or a peer leader may not) | **execution**: from this transition on, `task next` hands the squad the tasks carrying `feature: F-nnnn`. A `ready` feature's tasks are queued and held, not executable, so a squad can plan before it starts. `feature`-layer test records may be opened |
| `active` -> `done` | a caller whose resolved instance **is** the record's `owner` | the owned **paths** (13.3: a closed record is released, not compared), every `depends-on F-nnnn` in another open record turns **green** (13.3 rule 2 clears), the leader's one-open-feature slot frees (rule 3), and the `feature`-layer record closes with its merge evidence |
| `proposed`/`ready` -> `dropped`; `active` -> `dropped` once every task carrying the feature is terminal | a caller whose resolved instance **is** the record's `owner` | the same path and slot releases as `done`, and the id stays taken (ids are never reused). From `proposed` nothing was open, so nothing is released |

**`--by` is the caller, and the authority is checked on what it resolves to.**
There is no default, because the engine cannot infer who ran the command - the
same reason `decision add --by` is required. `feature` resolves the flag in
`validate_actor`'s **`allow_role=False`** mode (`engine.py:585-636`), not in the
function's default, because in that mode the result is **always an instance or a
refusal, never a role name**: the default (`allow_role=True`) hands back the
*role* for a bare role however many instances it has, and a role name satisfies
no instance check. The mode resolves in this order:

1. an **instance whose name matches** the flag, compared through `pascal()` - so
   `--by architect` is the instance named `Architect` in a team that has one;
2. a **bare role with exactly one instance**, resolved to that instance - the
   case `--by reviewer` already relies on (`cmd_review`, `engine.py:9399`);
3. otherwise a refusal: the role *name* with several instances is ambiguous, and
   anything matching neither is unknown.

The several-Architect case, stated rather than assumed. 13.5 names its peers
`Architect`, `Architect-2`, ..., so in that team `--by architect` is step 1 - the
first peer - and never step 2; the ambiguous refusal of step 3 is reached only
when no instance is spelled that way (peers named `Architect-1`, `Architect-2`).
Both outcomes are an **instance**, and the ledger records it, so a lane that must
be exact names the instance (`--by Architect-2`). What the freeze never does is
treat a bare role as naming "the role": this mode has no such result, which is
exactly the case the default would have produced and the authority check would
then have compared against nothing.

Both refusals are in the closed set below, frozen verbatim with the rest of the
`<reason>` strings, and both are the exit `2` of a `feature` write.
`validate_actor` reports through `die()`, whose *message text* is what is frozen
(`die` adds the `teamwork: ` prefix, `src/teamwork/io.py:142-144`) and whose code
defaults to `1`, so T-0042 passes the write verb's code into it - one defaulted
parameter, every other caller keeps `1` - and a `feature` write never exits `1`
for a `--by`.

**What a bare role means at `add`.** `--owner` must resolve to an existing
`team-leader` **instance** and to the same instance `--by` resolved to, so the
two are compared as resolved names and never as roles. With exactly one leader,
`--owner team-leader` and `--by team-leader` are both step 2 and resolve to that
one instance, so the owner-is-the-caller check passes; with two or more, a bare
`team-leader` matches no instance name and is refused as ambiguous, and the lane
names itself. (Both spellings are step 2 only once the role exists - today
`team-leader` is not in `ROLE_PARENT`, 13.1 - and T-0042 registers it.) No
bare-role spelling can make `--owner` pass for a different instance: the check
compares the two resolved names, and a role is not one.

The table above is then applied to the **resolved role and instance**, never to
the string: `ready` is refused unless the resolved role is `architect`, and
`active`, `done` and `dropped` are refused unless the resolved instance *is* the
record's `owner` - a peer leader is refused, and so is a squad instance. Every
write appends `feature.set` with the resolved actor to the ledger
(`engine.py:2289`), so who moved a record is itself a record.

**The limit is the engine's, and it is stated rather than papered over.** `--by`
cannot be authenticated; `decision add` has exactly the same property. What closes
it is that nothing in this design gives a caller a reason to borrow an identity:
the transitions a leader needs are its own, the freeze is the Architect's
deliverable on the Architect's own queue (13.5), and a caller that types another
instance's name writes a false record under that instance's name, which the
ledger and the Reviewer hold. No verb here takes a `--pen`, an `--as` or a "run it
for me" path, and the refusal prints the caller the engine resolved.

The refusals below are a **closed set** - nothing else refuses a `feature` write:

- `--by` that is empty, that resolves to no instance in this team, or that is a
  bare role with several instances and no instance spelled that way - the three
  `validate_actor(... allow_role=False)` strings frozen below;
- `ready` from a caller whose role is not `architect`;
- `ready` while `interface` is `-` (the freeze is the interface, not the word);
- `active`, `done` or `dropped` from a caller that is not the record's `owner`;
- a `set` that edits a field whose authority the caller does not hold:
  `interface` from a non-architect, `paths` or `depends-on` from a non-owner;
- `paths` edited once the record is `active` (13.4(a) proves the diff is a subset
  of the claim, and a claim that may grow afterwards proves nothing);
- `done` while any task carrying `feature: F-nnnn` is not `done`;
- `add` with an `--owner` that is not an existing `team-leader` instance, an
  `--owner` that is not the caller, empty `--paths`, or a record failing 13.3 or
  the `depends-on` rules of 13.1;
- a **state skipped forward** in any direction of the arrow above;
- out of a terminal record: `done` and `dropped` are closed, and reopening is a
  new record with a new id (ids are never reused);
- `dropped` from `active` while a task carrying the feature is still open - the
  slice is in flight, and abandoning it has to be a fact in the task graph first.

`--interface`, `--paths` and `--depends-on` on `set` are **record edits**, not
transitions. They are re-validated by 13.3 exactly as at `add`, and they are
applied **before** the state is evaluated: `set F-0003 --state ready --interface
Architecture.md#13` is one command, refused as `ready needs a frozen interface`
when the reference does not resolve. One authority per field, and the freeze is
never written by the lane that will work from it.

| Command | Output (frozen) | Exit |
|---|---|---|
| `feature add` | `teamwork: features + F-0003 [proposed] <statement>  owner=TeamLeader-1 paths=2`; a duplicate statement prints `teamwork: F-0001 already records that statement - not duplicated` | `0` added, `0` not duplicated, `2` refused (the vocabulary below) |
| `feature set` | `teamwork: features ~ F-0003 [proposed] -> [ready] interface=Architecture.md#13` - the from/to pair, then **one `<field>=<value>` per changed field**, in the field order of 13.1 (`interface=<ref>`, `paths=<n>`, `depends-on=<ids>` or `depends-on=-`); a field the command did not change is not printed, so a pure transition prints the pair only and an edit with no transition prints `teamwork: features ~ F-0003 [ready] -> [ready] interface=Architecture.md#13` | `0` moved or edited, `2` any refusal below |
| refusal | **one shape per verb**: the write verbs refuse with `teamwork: F-0003 stays [<state>]: <reason>` (`feature set`; `[<state>]` is the record's current state, `[-]` when no such record exists) and `teamwork: no feature added: <reason>` (`feature add`, no id to name yet); the read verbs refuse misuse with `teamwork: feature <verb>: <reason>` | `2` |
| `<reason>` | **one sentence, from exactly two places**: one of the frozen strings below - the state, authority and `--by` refusals; or, for a per-field validation, the condition of the 13.1 row that refuses it - and for a path, 13.3's frozen finding verbatim, with the candidate id as `<A>`. Nothing refuses a `feature` write in a second shape | - |
| `feature list` | `# Features (<N> open / <M> total) @ <short-sha>` then one block per record: `- F-0001 [active] <statement>`, `    owner=TeamLeader-1 interface=<ref>`, `    paths=<p1>,<p2>`, `    depends-on=-`. The two counts are over **what is printed**: with no filter `<N>` is the open records and `<M>` all of them; with `--state`, both count the filtered set | `0`; `3` after the header line when a `--state` filter matches nothing (the `criteria list` case: both counts read `0`); `2` an unknown `--state` value |
| `feature check` | green: `# feature check: <N> open feature(s), 0 problem(s) @ <short-sha>`; red: `teamwork: feature check: <K> problem(s) in <N> open feature(s) @ <short-sha>:` then one `  - <finding>` line per finding, then the two-line remedy naming throughput rule 6; an unknown id prints `teamwork: feature check: unknown feature F-0009` | `0` green, `2` any finding or an unknown id, `1` only when the records file cannot be read (`die`'s `teamwork: <message>` line, the engine's existing I/O code) |

**The frozen `<reason>` strings** - state, authority and `--by` refusals,
verbatim, one per line so a `feature`-layer record (13.4) can assert them:

- `unknown feature F-0009`
- `unknown state '<x>' (proposed, ready, active, done, dropped)`
- `a state cannot be skipped forward (proposed -> ready -> active -> done)`
- `ready is the Architect's freeze: --by must name an architect instance (you are Developer-2)`
- `ready needs a frozen interface: --interface <anchor-or-decision>`
- `interface is the Architect's freeze: --by must name an architect instance (you are TeamLeader-1)`
- `<state> is the record owner's transition: --by must be TeamLeader-1 (you are TeamLeader-2)`
- `done while 2 task(s) carrying feature: F-0003 are not done (T-0071, T-0072)`
- `a record in [done] is terminal; open a new feature`
- `dropped from [active] needs every task carrying feature: F-0003 terminal (open: T-0071)`
- `paths cannot change from [active]: the claim is final when the work starts`
- `the owner must be the caller: --by ProjectManager cannot file a record owned by TeamLeader-1`
- `the owner must be one team-leader instance: 'Developer-2' is a developer`

`<state>` in the seventh is the state named by `--state`, `(you are <instance>)` is
the caller the engine resolved, and `2` in the eighth is the count. A per-field
validation uses the 13.1 row's condition as its sentence, and a path uses one of
13.3's five findings - those are frozen there, not here, and are cited rather than
restated.

**The three `--by` refusals, frozen verbatim** - the message text
`validate_actor(..., allow_role=False)` prints (`engine.py:585-636`) inside
`die()`'s `teamwork: ` line, which the verb's own wrapper supplies, so the frozen
string is the `<reason>` and not the whole line. `<by>` is the flag as typed,
`<role>` the role it resolved to, and `<instances>` that role's instances in
roster order. They leave a `feature` write as exit `2`, not as `die()`'s `1`
(above):

- `actor must name an agent (an existing instance, or its role)`
- `'<by>' is ambiguous: the <role> role has several instances (<instances>). Name the one acting.`
- `unknown actor '<by>'. Known agents: <list>` - and, when the bare role resolved
  and has instances, the same sentence continues ` The <role> role has
  instances: <instances> - name one of them.`; `<list>` is the roster joined by
  `, `, or `(none initialised)` when the team has no instance at all

`@ <short-sha>` is the first seven characters of the revision a clean working
copy was read at - the caller's `HEAD` under the rule of 13.1 - so a reader can
always date the answer; when the working copy is **not** clean the token is
`@ worktree` (and `"rev": "worktree"` in `--json`), because a row that exists
only in an uncommitted edit is at no revision and naming `HEAD` would date it to
a commit that does not contain it. `feature check <F-nnnn>...` checks exactly the
named records and `feature check` with no argument checks the whole open set,
under **one** scope rule: every rule compares the **open set** except rule 5,
which is evaluated over **every record**, open or closed. A named
`done`/`dropped` record therefore contributes no finding except a rule-5
duplicate - another record carrying its `id` - and a no-argument check evaluates
the open set plus rule 5 over all records, the summary line counting both: `<N>`
the open features, `<K>` every finding from either scope.

**`--json` is frozen wherever it is exposed** (11.1.3's rule: a key is added, never
renamed), and the exit code is identical with and without it:

```json
{"id": "F-0003", "state": "ready", "changed": true, "rev": "<short-sha>"}
```

```json
{"rev": "<short-sha>", "open": 2, "total": 3, "features": [{"id": "F-0001", "statement": "...", "owner": "TeamLeader-1", "interface": "Architecture.md#13", "paths": ["src/a.py"], "depends_on": [], "state": "active", "created": "2026-10-29", "updated": "2026-10-29"}]}
```

```json
{"rev": "<short-sha>", "ok": true, "features": 2, "problems": [{"feature": "F-0001", "rule": 1, "message": "<the frozen wording of 13.3>"}]}
```

One object per invocation, keys in the order written, `json.dump(..., indent=2,
ensure_ascii=False)` and nothing else on stdout - 11.1.3's shape, applied to the
three verbs (the first fence is `add` and `set`, the second `list`, the third
`check`).

A duplicate `add` prints `{"id": "F-0001", "changed": false,
"reason": "duplicate statement", "rev": "<short-sha>"}` and a refusal prints
`{"id": null, "state": null, "changed": false, "reason": "<the plain
line's <reason>>", "rev": "<short-sha>"}` for `add` (no number is allocated, so
none is printed or consumed - 13.1) and `{"id": "F-0003", "state": "proposed",
"changed": false, "reason": "<the plain line's <reason>>", "rev":
"<short-sha>"}` for `set` - the same reason string, so a script never has to parse
prose twice. A read verb's misuse (`feature list --state <unknown>`, `feature
check <unknown id>`) prints `{"rev": "<short-sha>", "error": "<the same reason
string>"}` - one object per invocation, the plain one-line form above without
`--json`, exit `2` either way.

**A violation is always `2`, on the read path and the write path alike.** That is
the code the engine already uses for its independence refusals (`review --claim`
misuse, review independence) and the code `task check` reports a graph problem
with; `1` stays the `die()` default for I/O and internal error.

`task add --feature F-nnnn` adds `feature: F-nnnn` to the task record, rendered
after `deps`, parsed by `records.parse_tasks` and round-tripped by
`render_tasks` like `area` and `kind`. It is refused (`2`) when the id is
unknown, or the feature is not `ready`/`active` - a `proposed` feature is not
frozen yet (`ready` **is** the freeze, 13.1), and a `done` or `dropped` one is not
accepting work. **Execution is gated one state later than creation**: a task of a
`ready` feature is queued and held by `task next` until the record is `active`
(the transition that releases execution, above), and its record shows `[ready]` in
`pulse`, so nothing about the printed shapes changes for a `ready` team. A
`task add` **without** `--feature` renders byte-identically to today: the field
is written only when it is non-empty, so the existing corpus and every existing
test are untouched.

`instance add <role> --under <team-leader>` attaches a squad instance to the
leader it works for, and writes **one private file**, `Agents/<Instance>/Team.md`:

```text
# Team - Developer-2 (developer)

- under: TeamLeader-1 (team-leader)
- since: 2026-10-29
```

`instance list` prints each instance's manager beside it - `(under:<leader>)` when
it is attached to a team, `(reports:<parent>)` on the line `ROLE_PARENT` gives its
role - and `map` renders the **live team**, not just the roster. The *line* is
still `ROLE_PARENT` and the attachment is not a line (13.5); what the tree adds is
the team a leader actually holds, because a member that cannot read its own
escalation path from the map cannot follow it. Under the CTO the map prints one
row per `team-leader` instance carrying the record it owns - its open `F-nnnn`
and state, the last record it owned when it is between slices, or `feature=none`
when it has never owned one; the squad instances whose `Team.md` names that leader
(`instance add <role> --under <leader>`, for the squad roles `data-engineer`,
`designer`, `developer`, `technical-writer`, `tester`) are printed under it with
`(under:<leader>)`; squad instances no leader owns are printed as the CTO's pool;
and the independent lanes - `reviewer`, `security-auditor`, `cfo` - stay on the
CEO's line, never under a leader, with the exception note: a verdict under the
reviewed is not a verdict, and the Security Auditor audits the lane above it and
cannot audit the lane it reports to. No attachment changes `ROLE_PARENT` or the
number of managers an instance has: the map renders the private `Team.md`, and
the one-manager rule is enforced by `instance add` - one name, one `under:` line,
or none - not by the tree.

```text
CEO
  CTO
    Team Leader: TeamLeader-1  feature=F-0001 (active)
      Developer-2  (under:TeamLeader-1)
      Tester-2  (under:TeamLeader-1)
    Team Leader: TeamLeader-2  feature=none
    (squad pool - no leader attached)
    Developer-1
    Architect
  Reviewer
  Security Auditor
  CFO
  note: the Reviewer, the Security Auditor and the CFO serve every feature without reporting to a Team Leader - a verdict under the reviewed is not a verdict.
```

Refused (`2`):

- `--under` naming anything that is not a `team-leader` instance;
- `--under` on a **shared or independent** role - `architect`,
  `project-manager`, `release-engineer`, `reviewer`, `security-auditor`,
  `ceo`, `cto`, `coo`, `cfo`. Each of these holds a standard that spans teams
  (or audits the lane above it), so an attachment would be a second manager,
  which throughput rule 1 forbids. **The Security Auditor is one of these,
  permanently**: it audits the lane above and the team it would be attached to,
  so attaching it is review under the reviewed (`D-20261021-SecurityAuditor`'s
  independence). It serves **every** feature without reporting to a Team Leader,
  and `--under` on `security-auditor` is refused with that reason rather than
  with a generic one. `references/Roles.md` lists Security among the attachable
  specialists; that half of the sentence is **superseded** by
  `D-20261029-Architect-2` and ceo T-0018 removes the word. Until it lands, this
  section and the ADR are the later, narrower text;
- `--under` on a **`team-leader`**: a leader's only manager is the CTO
  (`D-20261029-Architect-2`), so a leader attached under a leader is exactly the
  second line that ADR forbids, and the unstaffed-seat fold does not reach it (a
  fold moves a *seat* to its parent; it never invents one). More teams is
  `instance add team-leader` with **no** `--under`, which puts the new leader on
  the CTO's line where it belongs;
- **re-attaching** an existing instance: `instance add` refuses a name that
  exists, so a squad instance belongs to one team for its life. Moving a
  specialist is `instance retire` + `instance add --under`, which leaves an
  `instance.retire` / `instance.add` pair in the ledger. That is what makes "one
  manager at a time" true by construction rather than by convention: there is no
  command that writes a second `under:` line.

`task next` and `pulse` must **refuse a squad instance claiming another team's
task**. Resolution is offline and total: `feature: F-nnnn` is executable by an
instance `I` iff the record's `owner` is `I`, or `I`'s `Team.md` names that
owner - **and** the record's state is `active`. An instance with no `under:` never
executes a feature task, and a leader executes only its own. A `ready` feature's
tasks are held by the same held line, not handed out, until its owner activates
the record. A task with **no** `feature` field is executable by any instance of
its role - the backward-compatible case, and the honest reading: unsliced work (a
preflight repair, a docs contract) belongs to no team.

| Site | Shape (frozen) | Exit |
|---|---|---|
| `task next`, everything ready is foreign | `teamwork: Developer-2 (developer) has no executable task of its own team` then `  (<N> ready in the queue, <N> held by another team)` and one `  - T-0071 [P1] feature=F-0002 owner=TeamLeader-1` per held task | `3` |
| `pulse` | one `## feature teams (<N>)` block, one line per open feature: `- F-0001 [active] TeamLeader-1: squad=Developer-1,Tester-1  ready=1 doing=1`, then `# shared services: architect <n> lane(s), <k> feature(s) waiting on an interface freeze`, where `<k>` is **the number of features whose `interface` is `-`** - the records still waiting on an Architect's freeze, since `-` is legal only in `proposed` (13.1) and a `proposed` record may already carry an interface the Architect set without having been moved | `0`, `3` unchanged |

`pulse` still prints the review queue, the board and the dependency view **once**
for the whole team; the new block adds the per-team line and never a per-team
copy of a shared print (13.5).

### 13.3 The independence rule, as an executable test

Rules 1-4 are a predicate over the **open** records (`state` in `ready`,
`active`), evaluated in one read of one file. `feature check` is red when any of
them holds among those records; `feature add` and every record edit of `feature
set` refuse the record instead of writing it, comparing the candidate against
**every open record** - so a record is judged before it is created and the same
rules judge it again at the transition that opens it. **Rule 5 is the one rule
over every record**, open or closed, because a closed id still names one feature;
no single-revision `add` can break it (allocation is max+1, 13.1), so like rules
1-4's cross-branch miss it is a fact the merge path finds.

| # | Rule | Finding (frozen wording) |
|---|---|---|
| 1 | no two open features own overlapping writable paths | `<A> <B> share a writable path: <path>` |
| 2 | no open feature depends on another feature's in-flight work | `<A> depends on in-flight <B> (state=<state>)` |
| 3 | one open feature per leader | `<owner> owns <n> open features: <ids> (rule 2: one open feature per leader)` |
| 4 | no owned path is a glob, outside the repository, checkout state, a generated artifact, or the records file | the five strings below, one per case, each with the record id and the path **as it was written** |
| 5 | no two records carry the same `id` - over **every** record, open or closed (see the resolution below) | `<A> is allocated twice (<owner-1>, <owner-2>); renumber the arriving record before it lands` |

The placeholders are records and names from the read: `<A>` a record's id, `<B>` the
other record a rule pairs it with (rules 1-2, in the order the records appear in
the file), `<owner>` the leader in rule 3, and `<owner-1>`/`<owner-2>` the two
owners of the duplicated id in rule 5, in that same order; `<path>` is the path
**as it was written**.

**Rule 4's five findings, frozen verbatim** - a `feature`-layer record (13.4) has
to assert these strings, so there is no "etc." and no paraphrase:

| Case | Frozen finding |
|---|---|
| a glob, any of `* ? [ ] { }` in the raw path | `<A> claims a glob (<path>); name the directory instead` |
| outside the repository by the containment rule below | `<A> claims a path outside the repository (<path>); the claim is relative to the repository root` |
| checkout state | `<A> claims checkout state (<path>); it never merges` |
| a generated artifact | `<A> claims a generated artifact (<path>); it is written at the merge` |
| the records file itself | `<A> claims the records file (docs/Team/Features.md); it is the map every claim is judged against` |

The records file is refused **because it is the records file**, not because it is
written at the merge: it is the map every other record's path claim is judged
against (13.1), and a feature that claims it could rewrite the rule that judges
it. The generated-artifact case covers `Board.md`, `Archive.md`,
`AuditManifest.md`, `AuditManifest.json`, which are rendered on the base branch at
the merge (throughput rule 8).

**The containment rule ("outside the repository"), decided without the filesystem.**
After the one normalisation of the matching rule, a path is *inside the
repository* iff (a) it does not start with `/` and does not carry a drive prefix
(`<letter>:`), and (b) it has no `..` segment. Both tests are string tests on the
normalised spelling: NFKC turns a full-width `／` into `/` and a full-width `．`
into `.` first, so the two spellings cannot disagree, and `..` is caught where it
is written rather than after resolution. Nothing is `stat`'ed and nothing is
resolved against a root, because 13.3's whole premise is that a dirty worktree and
a fresh clone answer the same question - and because a path a feature has not
created yet is a legitimate claim. Consequently `src/new_module.py` is inside the
repository whether or not it exists, `../outside.py`, `/etc/passwd` and
`C:/temp/x.py` are outside, and `src/../src/a.py` is refused as written (it is an
escape spelling, not a normalised path: the normalisation removes `./` and repeated
`/`, and deliberately does **not** collapse `..`).

**The matching rule, exactly.** Both sides are normalised once - `\` -> `/`, no
leading `./`, no repeated `/`, no trailing `/`, Unicode NFKC, then
`str.casefold()` - and then:

```text
covers(P, Q)  =  Q == P  or  Q.startswith(P + "/")
overlap(P, Q) =  covers(P, Q)  or  covers(Q, P)
```

Nothing is `stat`'ed and no glob is expanded, so a dirty worktree and a fresh
clone answer the same question and CI cannot disagree with the lane.

**The false-positive tolerances, and why each is refused rather than ignored.**

| Construct | Verdict | Why |
|---|---|---|
| file vs directory | the **prefix** rule; the trailing `/` is optional noise, so `src/teamwork` and `src/teamwork/` are the same claim and `src/teamwork` covers `src/teamwork/engine.py` | one syntactic rule with no filesystem probe; the reader cannot get a different answer depending on what is checked out |
| sibling names | **not** a collision: `engine.py` vs `engine_extra.py` share no boundary, because the rule matches on `/` | a substring rule would make `README.md` and `README.mdx` one file and force a needless split |
| globs (`*`, `?`, `[`, `]`, `{`, `}`) | **refused** | overlap between two globs is undecidable without expanding them both, and an unexpanded glob silently claims nothing - `src/*.py` reads as "all of src" and behaves as "no file at all". Naming the directory is the same claim and is decidable |
| generated artifacts (`docs/Team/Board.md`, `Archive.md`, `AuditManifest.md`, `AuditManifest.json`) | **refused** | they belong to the base branch and are written at the merge (rule 8); a feature that names one is asking for a render riding its branch, which conflicts with the next merge by construction |
| the records file, `docs/Team/Features.md` | **refused** - with its own finding, not the artifact one | it is the source of every record's path claim (13.1): a feature owning it could rewrite the rule that judges it, and it has one authority per field (13.2) |
| the team's own `.pi/`, `Scratch/`, `Runtime/`, `.venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `dist/`, `build/`, `site/` | **refused** | checkout state, gitignored, never merged: two features cannot conflict there, so claiming it is a design error, not an overlap |
| case (`src/TeamWork/Widget.py` vs `src/teamwork/widget.py`) | a **collision**, on every platform | a rule that differs between the lane and CI is not a rule. Case-folded is the safe direction: a false positive costs a rename, a false negative costs a merge conflict on the one checkout that cannot hold both |
| the same feature listing a path twice | green | one owner; the union is the feature's set |
| `done` / `dropped` | released - not compared at all | else the path map grows monotonically and every feature serialises behind the first one that ever touched a file |

**Dependencies are work, not interfaces.** `depends-on F-nnnn` means "I need that
slice **merged**". It is green only when the target is `done`; a `proposed`,
`ready` or `active` target is red (rule 2 above), and a `dropped` one is red
forever. A feature that only needs an *earlier feature's contract* does not
record a dependency at all - it records the frozen anchor in `interface`, and a
frozen interface is not in-flight work, because the Architect froze it before
either squad started (13.1, definition of ready). That distinction is what makes
"two features in parallel" true: at any moment the open set of records has **no
edges between its members**, so no two teams can be waiting on each other.

`feature check` also proves the rules the task graph relies on without restating
them: a self dependency is refused at `add` (13.1), and a cycle cannot be built,
because `depends-on` accepts only a `done` target and `done` is terminal - no
edge can be added back into an open record. The duplicate-id question is rule 5,
asked of a feature id instead of a task id.

**Rule 5 is resolved at the merge, and this is the choice.** Allocation is max+1
over the records *visible at the caller's revision* (13.1), so a duplicate cannot
be created inside one revision and can be created across two: two leaders cut
from the same base each read `F-0003` as free, and each branch carries a row with
that id. Neither allocation is a mistake and neither row is discarded.
`feature check` reports the duplicate at the merged tree exactly like any other
finding - exit `2`, the frozen line above under `"rule": 5` in the `--json`
object, once per duplicated id - so the merge path (13.1) refuses the merge
before the Reviewer's `pr merge` completes, and the **merging Reviewer** resolves
it there as a document conflict, with no command picking the winner. The record
already reachable from the target branch keeps its id, because that id is already
in the target's history. The record arriving from the branch being merged is
**renumbered** to the next free `F-nnnn` at the merged tree, in one edit to its
`id` field and to the `feature: <old id>` field of every task on that branch that
carries it - `feature:` is a parsed and rendered field like `area` (13.2). The
arriving record loses only the id its lane printed: `statement`, `owner`,
`paths`, `depends-on`, `state` and `interface` are untouched, nothing is dropped
and nothing is refiled, and from the merge on its id is the one the target
carries - the finding names the record, both owners and the duplicated id, so the
leader, the `feature`-layer record (13.4) and every later `depends-on` use the
new one. The renumber happens **before** the record lands, which is exactly what
keeps 13.1's "never reused, never renumbered" true of every record that has
landed.

Rule 5 can be red with nothing open: a `done` record on the target and a
`proposed` record on the branch read `0 open feature(s), 1 problem(s)`, because
the rule reads every record while the red header's `<N>` counts the open set that
rules 1-4 compare. The finding names both records, so the count and the finding
agree.

### 13.4 The `feature` test layer

| Question | Answer (frozen) |
|---|---|
| Layer name | `feature` |
| Owner | `team-leader` |
| Records | **one per area**, area = the feature id (`F-0001`). The feature's isolation evidence grows on that one record through `tests run`; a second record for the same feature is a duplicate, which `tests add` already refuses |
| What it proves | that **the slice is independently shippable**: (a) `git diff --name-only <base>...<head>` is a subset of the record's `paths` - the claim is real, not aspirational; (b) the suite is green with every other open feature's branch reverted from the merge base - the slice stands alone; (c) `feature check` is green for the record at that revision; (d) the frozen `interface` still describes what the code does |
| What `unit` does not | a unit test is right about a function; it is silent about which files the branch touched, and a perfectly unit-tested change can still collide with a sibling |
| What `integration` does not | an integration test proves two modules compose in one process inside **this** tree; it cannot see that the tree only composes because a sibling's unmerged commit is merged in, which is exactly the dependency rule 6 forbids |
| What `acceptance` does not | acceptance proves the story works for a user; a story can pass while the slice cannot be merged on its own, and the merge - not the story - is what a second team waits on |
| Where the rule itself is tested | the Architect's `system` layer (13.1's contract, TS-0002 style): a `feature`-layer record proves *this feature* obeys the rule, a `system` record proves the *checker* implements this section. Two questions, one record each, no overlap |

The engine change T-0042 makes is mechanical and is part of this freeze:
`TEST_LAYERS` gains `feature`, and `LAYER_OWNER` / `LAYER_WHAT` / `LAYER_CELL`
gain the matching entries (`feature` -> `team-leader`, "feature isolation: the
slice's diff, its standalone build and its frozen interface"). `staffed_layers`
then requires the layer only where a `team-leader` instance exists, which its
existing rule already guarantees, so `tests plan` never reports a gap for work
nobody owns. `DEFAULT_REQUIRED_LAYERS` stays `unit, integration, acceptance`; a
team leader widens its own area with `tests require --area F-0001 --layers
unit,integration,acceptance,feature --reason <why>`.

### 13.5 The shared services: one Architect and one Project Manager for N teams

| Service | Instance | What it owns for every team | What prints once |
|---|---|---|---|
| Architect | one, peers on one queue | the frozen interface of every feature (`interface`), the path map (this section), the `system` layer, the ADRs | the interface freeze: one anchor or decision id per feature |
| Project Manager | one, peers on one queue | `Plan.md`, `Board.md`, `Features.md`, the dependency graph, duplicate-statement detection, the archive | the board render (rule 8: at the merge), the dependency view (`task check`), the review queue |

**Why N teams do not need N architects.** The Architect is on a feature's
critical path **once**: a feature cannot leave `proposed` without a frozen
interface, and after that the squad works from the frozen text. A freeze is one
small deliverable per feature, so the single lane serves N teams by claiming
`task next architect --capacity N` - the queue is the parallelism, and the
memory pen still keeps one writer on the role's memory. If M features wait on a
freeze, the answer is `instance add architect` (peers, one queue), not a second
architecture or a per-team copy. **M is measured, not asserted**: it is the `<k>`
`pulse` prints, the number of records whose `interface` is `-` (13.2), so the
capacity question is answered by the same number that describes the queue. The
same arithmetic holds for the Project Manager, with one extra constraint:
`Board.md` is written at the merge, and `Features.md` has **one authority per
field** (13.2), so neither is a document two lanes rewrite behind each other: a
second PM instance reads the same one `Features.md` set, a feature edit is made by
that record's field authority through the command, and two edits on two branches
meet as the document conflict of 13.1, which the merging Reviewer settles. The lock
(`Runtime/Locks/features.lock`) serialises writers inside one checkout; it is not
and is not claimed to be cross-worktree mutual exclusion.

**Neither shared service manages a lane.** Their charters say "manages: nobody":
they own *artifacts and decisions*, and a Team Leader that needs an interface
frozen files a task on the architect queue - it never directs the Architect, and
the Architect never dispatches a squad. That is what lets one instance serve
teams it does not manage, and it is why the shared service adds no reporting
edge to the tree: the reporting model is
`D-20261029-Architect-2` - the CTO is the single line manager of every Team
Leader, and the CEO+CTO+CFO board holds decision rights over a feature's scope,
standard and budget without a second line.

**Reproduced before implementation.** `.pi/Scratch/architect/probe_feature_split.py`
(gitignored scratch) runs this section's predicate against hand-written records:
17 cases, 0 mismatches - red on a deliberately shared file and on a shared
directory, green on a clean split, green on sibling names and on a closed feature
releasing its paths, red on a glob, on `.pi/` state, on a generated artifact, on
the records file, on a case-folded collision, on an in-flight dependency, on one
leader holding two open features, and on the three containment spellings
(absolute, drive prefix, `..`) while a path that does not exist yet but is inside
the repository stays green. The probe prints rule 4's five findings
**from the frozen strings of this section**, so the wording a `feature`-layer
record asserts is the wording the predicate emits. The evidence line is in
`D-20261029-Architect-3`, which also carries the corrected count.

## 14. Lessons and prefixed team skills (frozen)

Owner: Architect. This section freezes the **mistake-memory surface**: the `tw-`
prefix every team skill carries, the two skill kinds, the role-local lesson
record, and the `lesson`/`skill` CLI shapes T-0031 implements. The
constitution text (`SKILL.md`, `roles/`, `references/`) belongs to the CEO; what
is frozen here is the engine surface and the rules a Tester can assert on.

**Measured baseline at `0075c82`** - none of this is implemented yet, and the
section says so rather than describing an engine that does not exist:
`git ls-files .agents/skills` -> `ceo-audit-close/SKILL.md` and
`product-manager-records/SKILL.md`, i.e. two unprefixed skills;
`skill create --help` has no `--kind` and no `--from-lesson`;
`harness lint` -> `# problems found: 0`, so `PREFIX` does not exist yet;
no `Roles/*/Lessons.md` exists and `teamwork.py lesson` is not a subcommand.
Until T-0031 lands, `tw-` and `Lessons.md` are a rule, not a command.

Every team-created skill carries the fixed prefix `tw-`. The prefix is the
recognition contract: a directory under `.agents/skills/tw-*`, and a registry row
whose name starts `tw-`, is a Teamwork-authored local skill - never a host or
third-party skill. `skill create` refuses any other name, and `harness lint`
reports rule `PREFIX` for a directory that does not carry it. There is no legacy
exemption.

### 14.1 Skill kinds

| kind | created from | front matter | purpose |
|---|---|---|---|
| `workflow` (default) | a repeated task flow | `kind: workflow` | the one way to do a recurring job |
| `mistake` | a recorded lesson via `--from-lesson L-nnnn` | `kind: mistake` plus `prevents: L-nnnn` | the workflow fix that stops one recorded failure recurring |

The registry row in `Skills.md` carries `kind:` and `lesson:` next to the
existing fields (`name`, `status`, `owner_role`, `created_by`, `path`, `created`,
`updated`, `shared_with`, `description`). `skill create --from-lesson` requires
the lesson to exist, to belong to the same role as the skill and to be `open` or
`fixed` with no `skill` yet; a lesson already fixed by a skill is refused,
because the skill it names is its fix. On success the lesson becomes `fixed` with
the skill name and the actor recorded, and both records link to each other. That
makes both orders legal: skill-first fixes the lesson, lesson-first is closed by
the skill, and AC-M17-3's link holds either way. `skill create --kind mistake`
without `--from-lesson` is refused: a mistake skill names the record it fixes. A
skill file read without a `kind:` field is a `workflow` (backward compatible).

### 14.2 Lesson records (`Roles/<Role>/Lessons.md`)

Local working state, shared by every instance of a role, never committed (like
memory). One record per mistake:

```
## L-0001 - <one line: what went wrong>
- role: <role>
- status: open | fixed
- mistake: <the observable failure>
- cause: <why it happened>
- rule: <what the agent now does instead>
- evidence: <command @rev -> result>
- task: <T-id>            (optional)
- skill: <tw-name>        (set when a skill fixes it)
- by: <instance>
- created: YYYY-MM-DD
- updated: YYYY-MM-DD
```

Ids are globally unique across the team: `L-` plus four digits, allocated from
the maximum over every role's `Lessons.md`. Commands: `lesson add`,
`lesson list [--role ROLE] [--status open|fixed|all]`, `lesson show <L-id>`,
`lesson fix <L-id> --by <instance> [--rule TEXT] [--skill tw-name] [--evidence TEXT]`.
`lesson add` requires `--by`, `--mistake`, `--cause`, `--rule` and `--evidence`;
the role defaults to the actor's role.

`lesson list` defaults to `--status all` with `--role` unset (every role), sorted
by id, one line per lesson:

```
- L-0001 [open] <role>: <mistake> -> <rule> (skill: tw-name | no skill)
```

`lesson fix` requires a recorded `--evidence` (or keeps the existing one) and an
existing `--skill` when given; on an `open` lesson it moves it to `fixed` and
records `updated`. On an already `fixed` lesson it is allowed only when it
carries new `--evidence` (a re-proof of the fix) and keeps or updates `--skill`;
otherwise it is refused with
`lesson L-0001 is already fixed by <skill>; pass --evidence to re-prove the fix`
(the detail names the recorded skill, or `no skill` when the lesson was fixed
without one) and changes nothing. `load` prints that role's open lessons (first
10) and a count of fixed ones, so every instance sees its mistakes at startup. A
missing file is an empty lesson list, never an error.

### 14.3 CLI shapes (frozen, documented in `docs/guide/cli.md`)

```
teamwork lesson {add,list,show,fix} ...
teamwork lesson add --by BY --mistake TEXT --cause TEXT --rule TEXT --evidence TEXT [--role ROLE] [--task TASK]
teamwork lesson list [--role ROLE] [--status open|fixed|all]
teamwork lesson show L_ID
teamwork lesson fix L_ID --by BY [--rule RULE] [--skill SKILL] [--evidence EVIDENCE]
teamwork skill create --name tw-NAME --for TEXT --by BY [--role ROLE] [--kind workflow|mistake] [--from-lesson L_ID] [--body BODY] [--body-file FILE] [--force] [--allow-main]
```

`--force` replaces an existing `<name>/SKILL.md`; `--allow-main` overrides the
branch guard that refuses creation on `main`. Both keep their current meaning
(section 4 changes no existing flag); the only new flags are `--kind` and
`--from-lesson`.

`SKILL_PREFIX = "tw-"` and `SKILL_NAME_RE = ^tw-[a-z0-9]+(-[a-z0-9]+)*$` are the
single source of truth in `config.py`/`records.py`. `skill candidates` keeps its
repeated-area list and adds a mistake section: for each role, tasks whose
`review_fails` is greater than zero, with the count and the findings text, plus a
paste-ready `lesson add` line and `skill create --from-lesson` line. `skill list`
prints `kind` and, for a mistake skill, the lesson id. `skill share` tells peers
the kind and the lesson.

### 14.4 Invariants

- Renaming a skill moves the directory, the front-matter `name:`, the registry
  row and every live trigger in one reviewed change.
- The two skills that predate this section are renamed `tw-ceo-audit-close` and
  `tw-product-manager-records`; every live reference (SKILL.md, roles/, tests,
  Plan.md) moves with them. Records in `Archive.md` and `Decisions.md` are
  history and are not rewritten.
- A lesson never replaces a gate and a skill never weakens one: the normal
  branch, commit, PR, review and Reviewer-only merge apply to both.
- `harness lint` rule `PREFIX` (12.4): every `.agents/skills/<dir>/SKILL.md` must
  have `name:` and `<dir>` starting with `tw-`; one finding per file, detail
  naming the offending value.

## 15. Project knowledge: accumulation, ranking and supersession (frozen)

Owner: Architect. This section freezes the **knowledge-accumulation surface**: the
`K-` record, the `knowledge` command and the ranked `load` section T-0032
implements. Section 14 is the mistake half (`L-` lessons and `tw-` mistake
skills); this is the experience half - what the project has learned to do.

**Measured baseline at `62d7405`** - none of this is implemented yet, and the
section says so rather than describing an engine that does not exist:
`Get-ChildItem src/teamwork -Filter *.py | Select-String -Pattern Knowledge.md`
-> 0 matches; `python scripts/teamwork.py load architect` -> memory output only,
no `# project knowledge:` line; `python scripts/teamwork.py recall --help` ->
`--agent`/`--all`/`--global`/`--layer` only, no knowledge source;
`python scripts/teamwork.py --help` -> no `knowledge` subcommand;
`git ls-files Knowledge.md` -> empty; `python scripts/teamwork.py harness lint`
-> `# problems found: 0` in this lane's worktree with an isolated empty team
registry (`TEAMWORK_ROOT` under the worktree), and no rule covers the store (the
shared live root still reports 2 pre-existing `HELPER` findings for the S-0001 /
S-0002 `tw-` rows awaiting T-0031). Until T-0032 lands, `Knowledge.md` is a
rule, not a command.

Every agent accumulates durable project knowledge as `K-` records in
`Knowledge.md` at the team root. This is not a mistake log and not a task note:
one record is one fact, rule, gotcha or measured behaviour that makes the next
decision faster or better, with the evidence that established it. The store is
project-local working state (never committed), shared by every role, and written
only through the `knowledge` command, which allocates the id and rewrites the
file atomically under the team's file lock - so two lanes can append without a
prose conflict. A missing `Knowledge.md` is an empty store, never an error.

### 15.1 Record shape

```
## K-0001 - <topic>
- statement: <one durable fact, rule or gotcha about THIS project, <= 500 chars>
- evidence: <command @rev -> result | path:line | URL + access date>
- tags: <comma list, lower-case kebab>
- owner: <role that first recorded it>
- by: <instance>
- task: <T-id>              (optional provenance, set by --task)
- importance: 1-5
- uses: N
- status: active | superseded
- supersedes: K-0002        (optional)
- superseded_by: K-0004     (set on the old record)
- created: YYYY-MM-DD
- updated: YYYY-MM-DD
```

Ids are global, `K-` plus four digits, allocated from the maximum in the file -
a superseded record keeps its id, so the history stays readable. Every free-text
field is one line (`one_line()`), so a record cannot break the file's structure.
An empty tag list is stored as `- tags: -`, never an empty cell. The command owns
the id and the file; a hand edit is a defect, not a shortcut.

### 15.2 Commands (frozen, documented in `docs/guide/cli.md`)

```
teamwork knowledge {add,list,search,show,touch} ...
teamwork knowledge add --by BY --topic TEXT --statement TEXT --evidence TEXT [--tags TAGS] [--importance 1-5] [--supersedes K-ID] [--task T]
teamwork knowledge list [--tag TAG] [--role ROLE] [--status active|superseded|all] [--limit N]
teamwork knowledge search QUERY [--status active|superseded|all] [--limit N]
teamwork knowledge show K_ID
teamwork knowledge touch K_ID --by BY
```

- `add` requires `--by`, `--topic`, `--statement` and `--evidence`; `--topic` is
  at most 120 characters and `--statement` at most 500; `--importance` defaults
  to 3; `--tags` defaults to empty; `--supersedes` and `--task` default to unset.
  Tags are normalised to a lower-case kebab comma list. Ids are `K-0001` upward,
  allocated from the file maximum.
- Duplicates are **active-only**. The key is exact:
  `normalise(s) = " ".join(s.split()).casefold()`, applied to `topic` and to
  `statement`; two records are duplicates iff both normalised values are equal
  **and both are active**. No punctuation, accent or other folding applies.
  `add` applies this precedence:
  1. An exact **active** duplicate K-0003 returns the existing id and exits 0
     with `# K-0003 already records this: <topic>` and adds no second entry. If
     `--supersedes K-0002` is also given, K-0002 must be active: it is marked
     `superseded` with `superseded_by: K-0003` and updated, then that line is
     printed. A target that is the duplicate itself or is inactive exits 2.
  2. Otherwise, an active record with the same normalised topic but a different
     statement is refused, exit 2:
     `topic '<topic>' is already claimed by K-0002; pass --supersedes K-0002 to replace it`.
     Only the holder is an acceptable `--supersedes` target here.
  3. Otherwise the new record is created active.
  Re-adding a fact whose only matching record is **superseded** is not a
  duplicate. When no active record claims the topic it creates a new active
  record and the old fact stays history; when an active holder exists, rule 2
  applies and that holder must be superseded. `--supersedes K-old` may name the
  retired record only in the free-slot case and only when the new content
  matches it exactly - the **re-instatement** case. The retired record's
  `superseded_by` is not rewritten (it already names the record that retired
  it); the new record's `supersedes` names it. Naming any other inactive record
  exits 2.
- A topic is a claim slot: at most one **active** record carries a given
  normalised `topic`. A replacing fact uses `--supersedes` and retires the
  current holder; a different fact uses a different topic.
- On success `add` prints `# K-0001 recorded: <topic>` then
  `- path: <Knowledge.md>`.
- `--supersedes K-0002` sets the new record's `supersedes`, marks the old record
  `status: superseded` and `superseded_by: K-new`, and updates it; the new
  record's evidence is what justifies the replacement. A nonexistent target
  exits 2; the record itself exits 2; an already-superseded target exits 2,
  naming the active record at the end of its chain:
  `K-0002 is already superseded by K-0004`. Only the re-instatement case above
  may name an inactive record, and it rewrites no `superseded_by`. Therefore
  each record has at most one `superseded_by` edge, that edge always points to a
  later-created record, and an inactive record can never supersede another: a
  cycle would need an id lower than itself, so the directed graph is acyclic by
  construction and a re-instated fact always has an active record.
- `list` defaults to `--status active` and `--limit 20` (`0` means all) with no
  role or tag filter until asked; `--role` matches the `owner` field (provenance,
  not a permission or read filter) and `--tag` matches one tag in the record's
  list. Rows are ordered by `importance` descending, then `uses` descending, then
  `updated` descending, then id **ascending**, one line each:
  `- K-0001 [active] importance=3 uses=2 tags=build,ci: <topic> - <statement>`
  An empty tag list renders `tags=-`. The last line is exactly
  `# knowledge: N active, M superseded, T use(s)`, where `T` is the sum of
  `uses` over every record, active and superseded. `--status superseded|all`
  reads the history.
- `search QUERY` is a case-insensitive substring match over `topic`, `statement`
  and `tags`, read-only; it uses the same row and ranking as `list`, defaults to
  `--status active` and `--limit 20` (`0` means all), and accepts the same
  `--status superseded|all` history switch. An empty tag list renders `tags=-`.
  No match prints `# no knowledge matched "<query>"` and exits 0.
- `show K_ID` prints `## K-0001 - <topic>`, then every field in record order as
  `- field: value` (an unset optional field prints `-`, and an empty tag list
  prints `- tags: -`), then `- path: <Knowledge.md>`. A superseded record still
  prints `status: superseded` and its `superseded_by`: history is readable, not
  hidden. Unknown id exits 2.
- `touch K_ID --by BY` increments `uses`, sets `updated` and prints
  `# K-0001 uses=N`; unknown id exits 2. It is how the team records that a fact
  was actually used, which is what makes the ranking follow need rather than
  volume.
- Ledger events: `knowledge.add`, `knowledge.supersede` (when `--supersedes` is
  used), `knowledge.touch`.
- `load` prints the top 10 **active** records project-wide, one line each:
  `- [K-0001] <topic>: <statement> (uses=N, tags=...)`, where an empty tag list
  renders `tags=-`.
  then `# project knowledge: N active, M superseded; search: teamwork.py knowledge search "<topic>"`.
  The cap is fixed at 10 and the ranking is `list`'s order, so what every agent
  reads at startup is the most important and most used knowledge, not the newest
  ten.
- A record is never silently deleted: obsolete knowledge is **superseded**, so
  the team can see what changed, when and on whose evidence.

### 15.3 Evidence and privacy

- No knowledge without evidence: `add` requires a non-empty `--evidence`, and a
  statement whose evidence names no command, path or dated source is refused at
  review, not accepted as opinion. The evidence column is what separates
  accumulated knowledge from opinion.
- Never store a secret, credential, token or personal data. `Knowledge.md` is
  gitignored, but the red line applies to every store the team writes.
- Knowledge is not an argument: a decision cites the `K-` record **and its
  evidence**, never the record's authority.

### 15.4 Fluency

- The store is the project's accumulating experience: `list` reports active,
  superseded and total uses, so growth is measurable rather than asserted.
- `load` surfaces the top-ranked records, `knowledge search` answers a concrete
  question, and `touch` feeds the ranking - the loop that makes a later agent
  faster than the first one.
- The knowledge count is a milestone metric: a project whose agents never add or
  use a record is not accumulating experience, whatever its archives say.

## 16. Context tree: one navigable view of memory, lessons, knowledge and skills (frozen)

Owner: Architect. This section freezes the **context-tree surface**: the `ctx://`
view over the stores sections 14 and 15 created, the three computed levels, the
`context` command family and the `kind` field on knowledge. The design is adopted
from OpenViking; the dependency is not. Sources, the adopt/reject table and the
vendor-claim caveat are in [Research](Research.md) section 13, accessed
2026-11-03.

**Measured baseline at `a3d6edd`** - none of this is implemented yet, and the
section says so rather than describing an engine that does not exist:
`python scripts/teamwork.py --help` -> no `context` and no `knowledge`
subcommand; `python scripts/teamwork.py context --help` -> `invalid choice:
'context'`, exit 2; `git grep -n "ctx://" -- src tests` -> 0 matches;
`git ls-files .agents/skills` -> the two `tw-` skills; `python
scripts/teamwork.py harness lint` in this lane's worktree -> `# problems found:
0`. Section 15 is still a contract at this revision, so `kind` lands with it in
T-0032 and `context` follows in T-0033. Until then `ctx://` is a rule, not a
command.

Adopted from OpenViking: one filesystem-shaped view, stable URIs, L0/L1/L2
progressive loading, directory-scoped retrieval. Rejected: the server, the vector
index, the embedding/VLM dependency and generated sidecars. This skill is
stdlib-only, local and evidence-first; the tree adds no file, no index and no
migration. **The tree is a read-only view over the existing files, never a
second store.**

### 16.1 URI scheme

`ctx://` addresses the existing records and documents as one tree. A URI is a
view: it always resolves to an existing file or record, never to a copy. `<role>`
is the canonical role id (`developer`, `release-engineer`); `<name>` is a skill
directory name.

| URI | Resolves to | Levels |
|---|---|---|
| `ctx://` | the tree root: `project`, `role`, `global` | L0 count summary, L1 child list |
| `ctx://project/knowledge`, `ctx://project/knowledge/K-0001` | `Knowledge.md` records | L0/L1 record, L2 full |
| `ctx://project/skills`, `ctx://project/skills/tw-name` | `.agents/skills/<name>/SKILL.md` | L0 description, L1 headings, L2 file |
| `ctx://project/docs`, `ctx://project/docs/Team/Project.md` | committed `docs/**/*.md` | L0 title + first paragraph, L1 heading tree, L2 file |
| `ctx://role/<role>/lessons`, `.../L-0001` | `Roles/<Role>/Lessons.md` | L0/L1 record, L2 full |
| `ctx://role/<role>/tasks`, `.../T-0001` | `Roles/<Role>/TaskQueue.md` | L0 title, L1 fields, L2 body |
| `ctx://role/<role>/memory/short\|long\|archive`, `.../M-0001` | the role's memory files | L0 body, L1 fields, L2 entry |
| `ctx://global/memory`, `.../M-0001` | `Global/GlobalMemory.md` | L0 body, L1 fields, L2 entry |
| `ctx://project`, `ctx://role`, `ctx://global` | directory nodes | L0 count summary, L1 child list |

`role/<role>/memory/short`, `long` and `archive` resolve to
`Roles/<Role>/ShortTermMemory.md`, `LongTermMemory.md` and `ArchivedMemory.md`.
`project/skills` lists every `.agents/skills/<name>/SKILL.md`, `tw-` or not, so a
prefix lint finding stays visible instead of being hidden by the view.
`project/docs` lists every committed `docs/**/*.md`, addressed by its path after
`ctx://project/docs/`.

Unknown URI, unknown level or a URI outside the scheme exits 2 and names the
node. A segment that escapes its namespace (`..`, an absolute path, a backslash,
a drive prefix) is an unknown URI and exits 2: a node never resolves outside the
repository or the team root. A missing file reads as an empty store (the same
rule section 15 uses), never an error, except an unknown URI.

### 16.2 Levels (computed, never generated)

- **L0** is one line derived deterministically at read time: knowledge
  `[kind] topic: statement`; lesson `[status] mistake`; memory body; skill
  description; doc H1 + first paragraph collapsed to one line; task title.
- **L1** is the navigation layer: for a record, its fields as `- field: value`;
  for a doc, the heading tree (first 20 headings); for a directory, the child
  count plus each child's L0 (cap 20, then `... N more`).
- **L2** is the full record or file.

L0 and L1 are computed from the source at read time. There is no
`.abstract.md`/`.overview.md` sidecar: a generated summary is a second copy that
goes stale, and generating one needs a model. This is the one deliberate
departure from OpenViking's storage design and the section states it. Levels are
output formats, not files: nothing is cached and no level is written back.

### 16.3 Commands (frozen, documented in `docs/guide/cli.md`)

```
teamwork context {ls,tree,read,find,stats,digest} ...
teamwork context ls [URI] [--level 0|1] [--limit N]
teamwork context tree [URI] [-L N]
teamwork context read URI [--level 0|1|2]
teamwork context find QUERY [--scope URI] [--limit N]
teamwork context stats
teamwork context digest T_ID
```

- `ls` defaults to `ctx://`, level 0, limit 20; one line per child:
  `- <uri> [<type>] <L0>`, where `<type>` is one of `dir`, `doc`, `skill`,
  `knowledge`, `lesson`, `memory`, `task`. `--level 1` prints each child's L1
  instead of its L0. `--limit 0` means no cap; a missing store lists nothing and
  exits 0.
- `tree` defaults to `ctx://` and depth 2; indented two spaces per level,
  `- <name> <L0>`; the same 20-child cap and `... N more` marker. `-L N` sets
  that depth (`-L 1` prints the root and its children).
- `read` defaults to level 1; L2 prints the full record or file. It prints the
  computed level and nothing else.
- `find` defaults to scope `ctx://` and limit 10; read-only.
- `stats` prints one line per store (memory, lessons, knowledge, skills, docs,
  tasks), live counts only, read from the files at call time; a missing store is
  `0`, and knowledge reports active and superseded counts on its own line.
- `digest T_ID` is read-only and prints candidate record templates: a failed
  review or a task `findings` field produces a `lesson add` block (mistake from
  the title, cause from the finding, rule left as a clear placeholder, evidence
  from the review/branch), and a done task also produces a
  `knowledge add --kind experience` block (statement from the title/result,
  evidence from the branch/merge). It writes nothing and never claims a record;
  the agent decides. A task that is neither failed nor done, and has no findings,
  prints `# T-0007: nothing to digest` and exits 0; an unknown task exits 2.

Every `context` subcommand is read-only: none writes a file, a record, a cache or
a ledger event. `digest` in particular never claims the record it proposes.

### 16.4 Retrieval: deterministic, no embeddings

Tokenise the query on whitespace and casefold; the **normalised query** is those
tokens joined by one space. A node matches if any token occurs in its L0 or L1
text (casefolded substring). Score, highest first:

```
5 * (normalised query is a substring of L0)
+ 3 * (every token occurs in L0)
+ 2 * (token occurrences in L0)
+ 1 * (token occurrences in L1)
+ 1 * (a tag equals a query token)
```

An occurrence is a non-overlapping substring match in the casefolded text. Only
positive scores are returned; ties break by URI ascending. `--scope` is a URI
prefix (`ctx://role/developer`, `ctx://project/knowledge`), and a node outside
the scope is never returned; an unknown scope exits 2. `find` prints one hit per
line, `- <score> <uri> [<type>] <L0>`; no hit prints
`# no context node matched "<query>"` and exits 0. `find` never reads L2. No
model call, no network, no index: the same query over the same tree returns the
same list.

### 16.5 Knowledge kinds (the "experience" context type)

OpenViking separates experiences from facts; section 15's records gain a `kind`
field: `fact` (default), `experience`, `preference`, `gotcha`, `rule`.
`knowledge add --kind`, `knowledge list --kind` and `knowledge search --kind` use
it; `load` and the context L0 show it. A lesson remains the record of a mistake;
an `experience` is a reusable approach that worked. This is the smallest change
that gives the user's "experience" a first-class home without a second store.

The field is written after `statement` and before `evidence`; a record without
`kind:` reads as `fact`, so section 15's records need no migration. `add`
defaults to `fact`, an unknown kind exits 2 naming the five values, and
`list`/`search --kind` keep only that kind. `show` prints the field in record
order. `load` renders it after the id -
`- [K-0001] [experience] <topic>: <statement> (uses=N, tags=...)` - and the
context L0 begins `[experience]`.

### 16.6 Invariants

- The tree is a view: no new file, no duplicated content, no migration, no
  index. Every node resolves to a committed doc or a team-local record.
- `context` is read-only: no subcommand writes a file, a record, a cache or a
  ledger event, and `digest` never claims the record it proposes.
- No secret is surfaced: the docs are privacy-scanned, the records obey the red
  line, and `context` prints only what is already stored.
- The tree never replaces `load`, the gates, the review or the evidence rule; it
  is navigation and retrieval.
- `find` is deterministic and reproducible; no model, no network.
- **Section 5 gains no row.** Section 5 freezes files and workspace state, and
  the tree adds neither: there is no `Context.md`, no index file and no new
  directory, so a reader looking for a new path will not find one.
- A new store is added to the tree only by amending this section, never by a
  silent directory.
