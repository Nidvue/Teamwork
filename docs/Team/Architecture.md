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

## 11. Release consistency contract

One file, `scripts/check_release_consistency.py`, compared against one committed
record, `release-exceptions.json`. Its job: prove that every *published* fact
(git tag, npm version, GitHub Release, PyPI project, committed prose) agrees with
the *local* fact (`src/teamwork/version.py`, the tree at that commit, the tag
list). It is the release gate of [Release](Release.md); it is read-only (it
never tags, publishes, pushes or writes), it runs offline by default, and a
missing or unreadable input is an error, never a pass.

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
payload_digest(root: Path, rev: Optional[str]) -> str  # 11.3; rev None = working tree
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
| `2` | at least one input could not be read: malformed or missing exceptions file, not a git repository, or `--online` with a failed registry/API call |

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
anonymous read is enough for all three endpoints); a non-200 response, a
non-JSON body, a URL error or a timeout is the "failed API call" of exit `2`.

### 11.2 The nine rules

The **local** column is always readable offline from `--repo-root`. A rule whose
published half needs a network is `SKIP` under `--offline` and says so; it never
invents an `ok`.

| Rule | Published fact | Local fact | DRIFT when | Offline |
|---|---|---|---|---|
| R1 | every git tag `vX.Y.Z` | `src/teamwork/version.py` **at that tag's commit** | the file is missing there, has no `__version__`, or its value is not `X.Y.Z` | evaluates |
| R2 | `version.py` at HEAD | every tag's version | the HEAD version is not **strictly greater** than some tag's version | evaluates |
| R3 | every npm-published version | a git tag whose bundled-payload digest (11.3) equals that tarball's payload digest, or an entry in 11.4 | neither exists | `SKIP` |
| R4 | every GitHub Release | `git tag -l` | no tag has the release's name | `SKIP` |
| R5 | every git tag | the GitHub Release list | no release carries the tag's name | `SKIP` |
| R6 | committed markdown that prints a version | `version.py` at HEAD | a printed literal version is **older** than HEAD's and its line/block is not illustrative-marked | evaluates |
| R7 | `CHANGELOG.md` | every tagged version | a tagged version has no `## [X.Y.Z]` section, or more than one | evaluates |
| R8 | committed markdown that advertises an install channel | the shipped name/entry point, and (online) PyPI | the channel names a package or executable the repository does not ship, or `--online` finds the channel does not resolve and the text does not mark it unavailable | partial (see 11.2.4) |
| R9 | committed markdown that names a tag | `git tag -l` | a `vX.Y.Z` token names a tag that does not exist | evaluates |

#### 11.2.1 R1 detail

* Tag set: `git tag -l` filtered by `^v\d+\.\d+\.\d+$`; any other tag name is
  ignored (not a version claim).
* Tag content is read with `git show <tag>:src/teamwork/version.py` - the tag, not
  HEAD, and the tag object's commit for an annotated tag.
* `__version__\s*=\s*["']([^"']+)["']` is the parse; a non-semver value is drift.

#### 11.2.2 R2 detail

Versions compare as integer tuples `(major, minor, patch)`. Consequence to keep
in mind: the moment a tag is created on the commit that carries that same
version, R2
requires the next commit on `main` to bump `version.py` - tag first, bump
immediately after, never leave HEAD equal to a tag.

#### 11.2.3 R3 detail

Two comparisons, both on the same digest definition (11.3):

1. **npm side.** Read `https://registry.npmjs.org/@nidvue%2Fteamwork` (the
   published name is `@nidvue/teamwork`, `scripts/build_pi_package.py:23`), take
   every version key, and for each download `dist.tarball`; unpack the `.tgz`
   into a temporary directory (`tarfile`, `tempfile`, never into the repo), keep
   the `skills/teamwork/` subtree (the published skill root, [Pi-Packaging](Pi-Packaging.md)
   section 4), and compute the payload digest on the same relative paths.
2. **local side.** The tag whose version equals the npm version, at that tag's
   commit; its digest must equal the tarball's.

An npm version is satisfied by (a) such a tag or (b) a 11.4 entry. Note what (a)
implicitly forbids: a tag at a commit whose payload differs from the tarball,
which is exactly the npm `1.1.0` case of 11.5.

**`scripts/build_pi_package.py` is excluded from both sides of every digest.**
It is the build-time generator that *assembles* the tarball; it is not shipped
payload, so a change in it does not change what a user receives, and including
it would report a drift for a repository-side edit (11.5, third example). The
exclusion is part of the definition, applied uniformly, not per-version.

Every exception prints a visible line: `R3 ok 1.1.1 admitted by exception (<reason>)`
for an admitted version, and the DRIFT line names the version, both digests and
the tag that was tried.

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
`pip install teamwork-agents` (and the `python -m`, `python3 -m`, `py -m`
variants), `pipx install teamwork-agents`, `uvx --from teamwork-agents`. Each
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
the file and line, and the 404) while marked ones stay `ok`.

**R9.** The token regex is R6's without the project-context condition: any
`vX.Y.Z` token not inside a URL and not illustrative-marked must appear in
`git tag -l`. It is the rule that catches a pin (`--branch <tag>`) to a tag that
was never created (11.5) and a rollback paragraph that quotes a deleted tag.

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
  as strings, one trailing newline, hashed **once**. Symlinks are resolved; a
  file that cannot be read is drift, not a skip.
* `payload_digest(root, rev)`: with a `rev` the tree is materialised with
  `git archive <rev>` into a temporary directory (never `git checkout`), with
  `rev=None` the working tree is read in place. The npm side uses the unpacked
  tarball subtree as `root` (11.2.3).
* The first 16 hex characters are the published comparison form (`b1ba21e39436bf09`,
  64 bits) - long enough that a collision is not a realistic accidental pass.

### 11.4 `release-exceptions.json` (frozen)

A JSON **array** at the repository root, committed, sorted by `version`; an empty
array is valid and is the initial state. Every entry has exactly these four keys
and no others:

```json
[
  {
    "version": "1.1.1",
    "reason": "published from a workspace whose commit was never pushed",
    "evidence": "digest 0786a4ff3c2f84ba matches no commit in git rev-list --all",
    "recorded": "2026-10-20"
  }
]
```

| Key | Contract |
|---|---|
| `version` | `X.Y.Z`, matching the npm version it admits; duplicate versions are an input error (exit `2`) |
| `reason` | one sentence a reviewer can judge; empty is an input error |
| `evidence` | the measurement, not a restatement: a digest, a command with its result, a URL |
| `recorded` | `YYYY-MM-DD`, the ISO date the entry was written |

It is read **before** any rule runs. Missing file, invalid JSON, a non-array, a
non-object entry, a missing/extra key, a version that is not `X.Y.Z`, or a date
that is not `YYYY-MM-DD` is an input error: exit `2`, with the offending path and
problem in the `detail` of the `SKIP` that R3 prints.

An exception is a **recorded, reviewable admission**, never a silent pass: it is
committed, it goes through the two-stage gate like any other artifact, and R3
prints a line for it on every run. It admits one version's missing or
mismatching tag - it does not suppress any other rule, and it cannot silence a
DRIFT that R3 found for a *different* version.

### 11.5 Worked examples - three measured facts

Measured by the CEO on the repository, not re-derived here; the checker must
reproduce them and the implementer must not contradict them.

| # | Measurement | What the contract makes of it |
|---|---|---|
| 1 | npm `1.1.2` payload digest `b1ba21e39436bf09` equals the bundled-payload digest of commit `3f4981d` | `v1.1.2` must be tagged **at `3f4981d`**; then R1, R3, R5 hold for it and R2 forces the next `version.py` bump <!-- release-consistency: illustrative --> |
| 2 | npm `1.1.1` payload digest `0786a4ff3c2f84ba` matches **no** commit in `git rev-list --all`; its `version.py` sha256 `545fc1605b3997460a1cf348562c43fed5a8315c83ac8291f9cbf4078703d36d` appears in no commit | `1.1.1` is the 11.4 exception entry, never a tag: there is no commit to tag, so a tag would be a lie the digest can prove <!-- release-consistency: illustrative --> |
| 3 | npm `1.1.0` differs from tag `v1.1.0` **only** in `scripts/build_pi_package.py` | the payload comparison must exclude that file (11.2.3), or a green release reads as drift |

Example 1 also fixes the release order: tag the payload commit, then let CI's
`release.yml` build from the tag - never retag a later doc-only commit, whose
payload digest no longer matches the tarball.

The checker's own unit tests live in `tests/unit/` (section 8) and use fixture
trees through `--repo-root`; they are not a second contract.
