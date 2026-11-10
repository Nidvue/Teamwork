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
the original 7,416-line `teamwork.py` monolith. It is now a thin command layer
over typed modules; the move was behaviour-preserving and is covered by the same
suite.

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
| developer-1 | `src/teamwork/**`, `scripts/teamwork.py` |
| developer-2 | `tests/unit/**`, `tests/integration/**`, `tests/conftest.py` |
| tester-1 | `tests/acceptance/**` |
| developer-3 | `pyproject.toml`, `Makefile`, `scripts/verify_release.py`, `.editorconfig` |
| release-engineer | `.github/**`, `docs/Team/Release.md` |
| technical-writer | `docs/index.md`, `docs/guide/**`, `mkdocs.yml`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `CITATION.cff` |
| designer-1 | `README.md`, `assets/**`, `templates/Docs/**`, `docs/Team/Design.md` |
| security-auditor | `scripts/privacy_scan.py`, `docs/Team/AuditReport.md` |
| architect | `docs/Team/Architecture.md`, `docs/Team/Decisions.md` (technical entries), `tests/unit/test_portability.py`, `tests/unit/test_cli_contract.py` |
| product-manager | `docs/Team/Research.md` |
| project-manager | `docs/Team/Plan.md`, `docs/Team/Board.md` |
| coo | `docs/Team/Risks.md` |
| cfo | `docs/Team/Costs.md` |
| ceo | `SKILL.md`, `roles/**`, `references/**`, `templates/AGENTS.md`, `templates/TeamMap.md`, `templates/pi-package/**`, `.agents/skills/**`, `scripts/build_pi_package.py`, `scripts/sync_skill.py`, `docs/Team/Project.md`, `docs/Team/Pi-Packaging.md`, `docs/Team/Archive.md`, `docs/Team/AuditManifest.*`, `docs/Team/Decisions.md` (governance entries) |

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

| Code | Meaning | Sites measured at v1.1.0 |
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

* `ci.yml`: `lint` (ruff check + format --check + commit-identity audit),
  `typecheck` (mypy, non-blocking report), `test` matrix
  `{ubuntu,macos,windows} x {3.9,3.11,3.13}` plus ubuntu `3.10`/`3.12`,
  `build` (sdist+wheel+verify_release), `privacy`
  (`privacy_scan.py --tree --history --allow .github/privacy-allow.txt`: personal
  data, credentials, agent-host config and tracked local state),
  `docs` (mkdocs build --strict). On `push` the prose and media paths are
  `paths-ignore`d so a docs-only change does not burn the 3x3 matrix; every
  `pull_request` runs the full set, because a path-filtered skip reports no
  check at all and a required check that is never reported blocks the merge.
* `release.yml`: on `v*` tags - build, checksums (`SHA256SUMS`), SBOM
  (CycloneDX JSON + SPDX), attestation, GitHub Release with all assets.
* `docs.yml`: build and deploy the site to GitHub Pages on `main`.
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

## 11. Harness surface and hook contract (frozen)

Owner: Architect. The frozen interface for the `harness`, `hooks` and `hook`
lanes; decided in D-20261020-Architect to D-20261020-Architect-9, with the hook
directory and the layer tests fixed by ruling D-0001 R1-R6
(`D-20261020-Architect-8`). No removal, no rename and no extra flag lands
without a new entry in [Decisions](Decisions.md) and a notice to the affected
lane.

### 11.1 The two command groups

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

### 11.2 The surface registry (C1..C8)

`harness list` prints exactly **eight** rows, one per Harness^2 component, in
component order, with four whitespace-separated columns and no header line:

```text
<class>  <bytes>  <path>  <role>
```

- `class` is one of `always-on`, `on-demand`, `in-loop` (11.3).
- `bytes` is the total size in bytes of the files the `path` spec selects **at
  run time**; `-` only for C5, which has no file. `0` is a measurement and
  therefore only allowed when the spec was resolved and the files it names
  genuinely do not exist. A spec that can select nothing **by its spelling** is
  a defect in the row, never a zero: the row must name a path the command can
  actually reach, or the number it prints describes the spelling, not the tree.
- `path` is the spec exactly as tabulated below, `/` separators: repository-
  relative for C1..C7, and for C8 the resolver call its files are found through
  (§11.6), printed as the template `hook_dir(root)/{pre-commit,pre-push}`. C8 is
  a template and not a repository-relative path because the hooks live in the
  git directory git reports, which differs per repository, per worktree and per
  `core.hooksPath`; the absolute directory that was actually probed is printed
  by `hooks status` (§11.6), never guessed here.
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

### 11.3 Activation classes

| Class | Meaning | Consequence |
|---|---|---|
| `always-on` | in context on every call, before the task is known | paid by every run; the only class the budget caps |
| `on-demand` | loaded by a tool call only when it is invoked | paid once per invocation a task actually needs |
| `in-loop` | executed inside the tool loop instead of being reasoned about | costs latency and process, not context |
| `n/a` | an inference context, not a file (C5) | not measured; the lane packet is not an artifact |

C5 is `n/a` rather than a path: a subagent is a second context, not a file, and
the engine has no artifact for it. Inventing one would make the registry lie.

### 11.4 `harness lint`

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

### 11.5 `harness budget`

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

### 11.6 The hook shim contract

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

### 11.7 Hook rules

Exit 0 for a pass; exit 1 for a refusal (git aborts the operation on any
non-zero).

| Id | Stage | Rule | Override |
|---|---|---|---|
| R1 | pre-commit | refuse the commit whose HEAD is `config.DEFAULT_BASE`, resolved with `git symbolic-ref --short HEAD` (it answers on an unborn branch) | `TEAMWORK_ALLOW_MAIN=1` |
| R2 | pre-commit | refuse a staged file larger than `config.LFS_MAX_BYTES` (1048576) that no `.gitattributes` LFS pattern covers | add the pattern; no env override |
| R3 | pre-commit | warn on stderr when the commit identity is not a role mailbox (`<role>@IDENTITY_DOMAIN`), and exit **0** | - |
| P1 | pre-push | refuse a non-fast-forward update of `refs/heads/<DEFAULT_BASE>` | `TEAMWORK_ALLOW_FORCE=1` |
| P2 | pre-push | refuse deleting `refs/heads/<DEFAULT_BASE>` (zero local sha) | none |

Reuse is part of the contract: R1 and P1-P2 read `config.DEFAULT_BASE` (one
constant, no literal); R2 calls `gitutil.lfs_tracked` and compares against
`config.LFS_MAX_BYTES`, the same pair `commit --check-lfs` uses; P1 asks
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

### 11.8 Exit codes for the new surface

The codes in section 4 are unchanged and no new code is introduced:

| Code | Sites |
|---|---|
| `0` | `harness list`, a clean `harness lint`, an `ok` `harness budget`, every `hooks` subcommand on success, every hook rule that passes or only warns (R3) |
| `1` | any `harness lint` finding, an `OVER` budget line, a hook refusal (R1, R2, P1, P2), no workspace, not a git repository, a `hooks` misuse |
| `2` | argparse usage error only, including an ambiguous abbreviation of `hook`/`hooks` |

### 11.9 The layer test

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
