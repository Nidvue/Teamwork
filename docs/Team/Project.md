# PROJECT - Teamwork

Owner: CEO. Single source of truth for *what done means*. No task closes without
mapping to an acceptance criterion here.

Related: [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md) · [AuditReport](AuditReport.md)

## Objective

Turn the private `teamwork` skill into a self-contained, reusable,
cross-platform open-source **skill for coding agents**: one directory cloned into
the host's skill location, with the stdlib-only engine bundled inside it and also
published as the optional `teamwork-agents` package, a full development → test →
build → verify → release pipeline, polished documentation aimed at adoption, and a
public GitHub repository at `Nidvue/Teamwork` that is safe to open (zero private
information). The skill is the product; the package is a convenience face on the
same engine.

"Finished" means: a stranger can clone the skill into the skills directory of any
agent host, or run the repo in place, on Linux, macOS or Windows, name the skill
in a request to bootstrap an autonomous multi-agent team workspace, and every claim in the README is backed by a CI run, a test, or a
released artifact — with no personal data anywhere in the tree or in git history.

## Definition of done

- [ ] AC-1 Installable package: `python -m build` produces an sdist and a wheel;
      the wheel contains the packaged skill bundle; a clean-venv
      `pip install <wheel>` then `teamwork --version` exits 0 - proof:
      `scripts/verify_release.py`
- [ ] AC-2 No-third-party-dependency runtime: from a git checkout,
      `python3 scripts/teamwork.py --help`, `python3 -m teamwork --help` and
      `teamwork --help` all exit 0 with only the standard library - proof:
      `tests/acceptance/test_entrypoints.py`
- [ ] AC-3 Test suite: `pytest tests/` passes with >= 60 collected tests spread
      over unit, integration and acceptance layers; every required layer for
      every area is recorded and passing in `teamwork.py tests plan` - proof:
      `pytest -q` and `teamwork.py tests plan`
- [ ] AC-4 CI matrix: `.github/workflows/ci.yml` runs lint, type-check, the test
      matrix on ubuntu/macos/windows x Python 3.9/3.11/3.13, a build job and a
      privacy scan; every job is green on the pushed revision - proof:
      `gh run list --json displayTitle,conclusion`
- [ ] AC-5 Privacy: `scripts/privacy_scan.py` exits 0 over the working tree and
      over full git history; no personal email, no API key or provider token, no
      absolute personal path (including mounted homes), no personal domain, no
      agent-host configuration (auth, settings, sessions, model stores) and no
      tracked local state (`.pi/`, virtualenvs, build output, caches, `Scratch/`)
      in any tracked file or commit - proof:
      `python3 scripts/privacy_scan.py --tree --staged --history`
- [ ] AC-6 Documentation: README plus a docs site (mkdocs) plus CONTRIBUTING,
      SECURITY, CODE_OF_CONDUCT, CHANGELOG, CITATION; `teamwork.py links`
      reports zero broken links - proof: `teamwork.py links`
- [ ] AC-7 Release: tag `v1.0.0` publishes a GitHub Release with wheel, sdist,
      `SHA256SUMS` and an SPDX+CycloneDX SBOM, all attested - proof:
      `gh release view v1.0.0 --json assets`
- [ ] AC-8 Discoverability: repository description, homepage, topics, license and
      a social-preview asset are set; README opens with a pitch, badges, a demo
      and a comparison table - proof: `gh repo view --json description,repositoryTopics`
- [ ] AC-9 Cross-platform: no POSIX-only call in the runtime path
      (`fcntl`, `termios`, `pwd`, `grp`, `os.fork`, `shell=True`); lock and path
      handling is portable and has an explicit Windows-mode test; the Windows CI
      job is green - proof: `tests/unit/test_portability.py` + CI
- [ ] AC-10 End-to-end acceptance: from the *installed wheel* in a clean temp
      directory, `teamwork init` → `criteria add` → `task add` → `selfcheck` →
      `review` → `loop` runs and `loop` reports STOP - proof:
      `tests/acceptance/test_full_loop.py`
- [ ] AC-11 Team self-audit: `teamwork.py loop` reports STOP for this repository
      and `teamwork.py audit` reports zero problems - proof: `teamwork.py loop`,
      `teamwork.py audit`
- [ ] AC-12 Licensing and provenance: `LICENSE` (AGPL-3.0) is present and
      referenced from README and `pyproject.toml`; CHANGELOG and CITATION
      present; every release artifact carries a checksum - proof:
      `ls LICENSE CHANGELOG.md CITATION.cff`
- [ ] AC-13 Image generation owned by the Designer: `roles/designer.md` carries
      the vector-first medium choice, the offline `imaging probe` with a ranked
      model table and a fallback ladder, the generate-review-**improve** loop with
      a 3-round cap and the privacy/licence red lines; `docs/Team/Design.md`
      records each asset with a review log and an improvement log; there is no
      separate `Imaging.md` - proof: `tests/unit/test_imaging.py`
- [ ] AC-14 The updated skill is installed and runnable: `teamwork imaging probe`
      exits 0 from the repo and from an installed skill directory, and `init`
      creates `Design.md` (and no `Imaging.md`) whose template carries the
      visual-asset sections - proof:
      `python3 <skill-dir>/scripts/teamwork.py imaging probe`
- [ ] AC-15 Staged, review-gated push: `roles/release-engineer.md` and
      `references/Engineering.md` require the Release Engineer to push per
      reviewed + merged milestone only after the Reviewer passes with no open
      finding, with the build/tests/privacy/link gates green on that revision and
      CI green on the pushed SHA, routing a red run to the owning role - proof:
      `tests/unit/test_skill_contracts.py`
- [ ] AC-16 Local **and** CI certification by the Tester: `roles/tester.md` and
      `references/Testing.md` require both signals on the pushed revision,
      treat divergence as a defect, route failures to the owning agent, and forbid
      reporting a suite green while the matching CI run is red - proof:
      `tests/unit/test_skill_contracts.py`
- [ ] AC-17 CI triggers are path-filtered: a documentation or image-only change
      never runs the code matrix, while every shipping path (src, scripts, tests,
      roles, references, templates, packaging, workflows) always does; the
      ignored prose/media paths run a cheap docs check (links, privacy,
      `mkdocs --strict`) so a documentation leak is still caught - proof:
      `tests/unit/test_skill_contracts.py`, `docs/Team/Release.md`

- [ ] AC-18 Skill-first presentation and public namespace: every adoption surface
      (README, `docs/index.md`, `docs/guide/install.md`, `docs/guide/quickstart.md`,
      `docs/guide/architecture.md`, `assets/demo.svg`, mkdocs nav) installs Teamwork
      by cloning the skill into the host (plain files, nested `.git` dropped) and
      invokes it by naming the skill - `use the teamwork skill: <prompt>`, or
      `/teamwork <prompt>` where the host maps skills to commands; the Python
      package appears only as an optional engine; repository URLs use
      `Nidvue/Teamwork` in every tracked file except the historical audit records -
      proof: `tests/unit/test_skill_contracts.py`, `python3 scripts/teamwork.py links`

## Traceability - AC to task to test

Owner: Product Manager. Re-measured every records pass from the tree and from a
live run; no cell below is quoted from an older revision. Reproduce with
`.pi/Teamwork/Teams/Teamwork/Agents/ProductManager/Scratch/trace-matrix.sh`
(forward matrix `ac-matrix.py`, reverse map `record-ac.py`); the run that produced
this section is bound to the ledger as test record TS-0016 and to
`Agents/ProductManager/Artifacts/trace-matrix.txt`.

Measured at `49cc390` on `productmanager/t-0001-...` (base `main`), 2026-10-19.

### How the three layers are wired today

| layer | where it lives | who writes it | how an AC is named |
|---|---|---|---|
| acceptance criterion | this file, `## Definition of done` | CEO | `AC-<n>` bullet |
| delivering task | `docs/Team/Archive.md` section per closed task; open work in `Roles/<Role>/TaskQueue.md` | the owning role | free text in `self-check` / evidence |
| test record | `.pi/Teamwork/Teams/Teamwork/Tests.md` via `teamwork.py tests add/run` | the role that ran it | **not at all** - keyed by layer/area only |

The link between an AC and its test is therefore **documentary**: an AC names a
proof command, and a test record reproduces that command in its evidence line.
No record carries an AC id, and `teamwork.py trace AC-<n>` walks the ledger for the
literal string, so it resolves only for `AC-1` - and that one hit is a *different*
criterion (see gap G-1).

### Forward map: AC -> proof -> delivering commit -> task -> record -> measured

| AC | proof target | delivering commit | archived task(s) | test record | measured here | state |
|---|---|---|---|---|---|---|
| AC-1 | `scripts/verify_release.py` | `4d8ff35` | developer T-0001, ceo T-0017 | TS-0018 | `verify_release: OK - release verified` (sdist+wheel, clean-venv install, `--version`, `selftest`, `init`, installed-wheel loop -> STOP, `SHA256SUMS`) | green |
| AC-2 | `tests/acceptance/test_entrypoints.py` | `4d8ff35` | ceo T-0017, T-0023, T-0026, T-0027 | none | 7 passed, 1 skipped (console script not installed; covered by AC-1) | green |
| AC-3 | `pytest -q`, `teamwork.py tests plan` | command only | 20 archived tasks | TS-0001, TS-0005, TS-0008, TS-0011, TS-0014, TS-0018, TS-0022, TS-0024 | 430 collected, 429 passed 1 skipped; **`tests plan` rc 1 with 14 gaps** | **red** (second half) |
| AC-4 | `gh run list --json displayTitle,conclusion` | `.github/workflows/ci.yml` @ `4d8ff35` | release-engineer T-0001 | none | green at `6cfebad` (17/17 jobs); the two commits after it touch `docs/` only, so `e8da9ce` carries a Docs run and Dependabot runs, not the matrix | green by path filter |
| AC-5 | `python3 scripts/privacy_scan.py --tree --staged --history` | `4d8ff35` | security-auditor T-0001 | none | FAIL 18 findings; with `.github/privacy-allow.txt` still FAIL 5 (all `home-path` at `docs/Team/Archive.md:492`) | **red** (G-2) |
| AC-6 | `teamwork.py links` | command only | 10 archived tasks | TS-0013, TS-0024 | `# issues: 6` - 5 broken `compare/` links + 1 bare URL, all in `docs/Team/Archive.md` | **red** (G-3) |
| AC-7 | `gh release view v1.0.0 --json assets` | `.github/workflows/release.yml` @ `4d8ff35` | none | none | 5 assets: wheel, sdist, `SHA256SUMS`, `sbom.spdx.json`, `sbom.cyclonedx.json` | green (but the AC pins `v1.0.0`; latest is `v1.0.2` - G-5) |
| AC-8 | `gh repo view --json description,repositoryTopics` | repo metadata | none | none | description + homepage + AGPL-3.0 + 14 topics set | green |
| AC-9 | `tests/unit/test_portability.py` | `4d8ff35` | architect T-0001, ceo T-0016 | none | 20 passed; Windows jobs green in CI `391808644` | green |
| AC-10 | `tests/acceptance/test_full_loop.py` | `4d8ff35` | none | none | 2 passed; the installed-wheel variant also passes inside `verify_release.py` | green |
| AC-11 | `teamwork.py loop`, `teamwork.py audit` | command only | ceo T-0015, T-0023, T-0026, T-0027 | none | `loop` -> CONTINUE (1 failing layer, 14 missing, 12 open tasks, 4 disputes); `audit` -> 46 problems | **red** (G-4) |
| AC-12 | `ls LICENSE CHANGELOG.md CITATION.cff` | `4d8ff35` | none | none | all three present; `pyproject.toml:10` references the licence file | green |
| AC-13 | `tests/unit/test_imaging.py` | `b8f5548` (tests), `c8fb469` (`src/teamwork/imaging.py`) | designer T-0001 | none | 21 passed | green |
| AC-14 | `python3 <skill-dir>/scripts/teamwork.py imaging probe` | command only | none | none | `# imaging probe (offline: environment + PATH only)` rc 0, ranked `qwen-image-2.1 > sdxl > sd3.5-large` | green |
| AC-15 | `tests/unit/test_skill_contracts.py` | `31607cf` | designer T-0001, ceo T-0031 | none | 73 passed (contract tests named by behaviour, not by AC id) | green |
| AC-16 | `tests/unit/test_skill_contracts.py` | `31607cf` | designer T-0001, ceo T-0031 | none | 73 passed | green |
| AC-17 | `tests/unit/test_skill_contracts.py`, `docs/Team/Release.md` | `31607cf`, `4d8ff35` | designer T-0001, ceo T-0031 | none | 73 passed; `docs/Team/Release.md` present | green |
| AC-18 | `tests/unit/test_skill_contracts.py`, `python3 scripts/teamwork.py links` | command + `31607cf` | 7 archived tasks | TS-0013 | 73 passed; **`links` -> 6 issues** | **red** (same cause as AC-6) |

Totals: **13 of 18 green**, 4 red on an external gate (AC-5, AC-6/AC-18, AC-11),
1 red on the coverage plan (AC-3), 1 green only by path-filter inference (AC-4).
`4d8ff35` is the single bootstrap commit that added most proofs, so "delivering
commit" is coarse: the per-lane work is recorded in the Archive sections, not in
separate commits, for the M1-M4 lanes.

### Reverse map: test record -> AC

15 of the 25 test records name no proof that any AC claims; they are layer/area
records (engine, audit, context-economy, evidence, packaging, pr) whose AC link is
implicit. Records that do map: TS-0001/0005/0008/0011/0014/0018/0022/0024 -> AC-3,
TS-0018 -> AC-1, TS-0013/TS-0024 -> AC-6 and AC-18, TS-0015 -> AC-9.

**ACs with no covering test record** (16 of 18): AC-2, AC-3, AC-4, AC-5, AC-7,
AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18. Only
AC-1 and AC-6/AC-18 have one, and even those match by command text, not by id.

**Test record with no AC**: TS-0020 `[acceptance/context-economy]` is `failing`
(Reviewer-2: `pr merge` prints the archive entry but leaves `pending` and the tree
dirty, so the next merge dies switching branches). No AC owns it - the
context-economy contract has no acceptance criterion here.

### Gaps and owners

| id | gap | measured | owner |
|---|---|---|---|
| G-1 | The machine criterion store holds exactly one criterion, `AC-1 [verified]` (owner CEO, verified by Reviewer-1 2026-10-18 with `make ci` -> 333 passed, ledger #0019/#0020). Its text is the *old audit-fixes* criterion, not this file's AC-1. `teamwork.py criteria list` and `trace AC-1` therefore report the wrong artifact for the id. | `criteria list` -> 1 item; `trace AC-1` -> that item; `trace AC-2..AC-18` -> "nothing references" | CEO (re-key the store with `criteria add/verify` per AC, or prefix the historical one) |
| G-2 | AC-5 is red in the tree: 5 `home-path` findings at `docs/Team/Archive.md:492` added by `80a8ed5` (T-0031). Without the allowlist there are 18 findings (also `agent-config` at `tests/unit/test_privacy_scan.py:464`, `archive.md:480`, `references/Adapters.md:41` - those are blessed by `.github/privacy-allow.txt`, the home path is not). | `privacy_scan --tree --history --allow .github/privacy-allow.txt` -> FAIL 5 | CEO T-0031 / T-0028 |
| G-3 | AC-6 and AC-18 are red: 6 link issues in `docs/Team/Archive.md` (5 `compare/v1.0.2...*` targets that do not exist, 1 bare URL). | `teamwork.py links` -> `# issues: 6` | CEO T-0032 (branch at `ad8b6fc`, unmerged) |
| G-4 | AC-11 is red because it is downstream of G-2, G-3 and the open tasks: `loop` -> CONTINUE, `audit` -> 46 problems. It cannot go green before the others. | `loop` rc 1 / `audit` rc 1 | CEO |
| G-5 | AC-7 pins `v1.0.0` while `v1.0.2` is the released tag; AC-4 and AC-9 are phrased against "the pushed revision", which is ambiguous while local merges are ahead of `origin/main`. | `gh release list` -> v1.0.2 latest | CEO (re-word the AC, not re-do the release) |
| G-6 | 14 required test layers are missing or failing, so AC-3's `tests plan` clause cannot pass: `concurrency/{unit,integration,acceptance}`, `merge/{unit,integration,acceptance}`, `pr/integration`, `privacy/{unit,security}`, `security/security`, `task-graph/{unit,integration,acceptance}`, `context-economy/acceptance` (failing). | `tests plan` -> 14 GAP lines, rc 1 | the owning role per area; PM tracks it |
| G-7 | No AC owns the context-economy contract, so its failing acceptance record (TS-0020) has no requirement to escalate against. | see the reverse map above | CEO + ProductManager |

### Requirements-layer contract for this area

The traceability area requires exactly one test layer, `requirements`, and it is
satisfied: `teamwork.py tests plan` reports `traceability  goal· req+ ...` and role
coverage `product-manager  req  records=1 passing=1`. TS-0016 is that record; it is
re-run and re-bound to the new revision, evidence and artifact on every records
pass, and this section is its deliverable.

## Scope

- In: packaging (`pyproject.toml`, `src/teamwork/`), a thin `scripts/teamwork.py`
  compatibility shim, the bundled skill bundle (`SKILL.md`, `roles/`,
  `references/`, `templates/`), tests (unit/integration/acceptance), CI/release
  workflows, docs site, community files, privacy scanner, release artefacts,
  GitHub repository metadata, and the published `v1.0.0` release.
- Out (not doing): rewriting the engine's behaviour; new team features; a hosted
  service; a web UI; PyPI publication (prepared via trusted publishing but not
  enabled without the owner's token); paid promotion; bot-driven star farming
  (stars cannot be bought or guaranteed - see Risks).
- Constraints (time / budget / technical): Python >= 3.9, standard library only
  at runtime; no secrets in the repo; must install by cloning one directory into
  the agent host's skill location (`SKILL.md` at the repository root), with the
  pip package kept as an optional engine over the same code.
- Invariants that must not break: the existing CLI surface and on-disk team
  workspace format (`.pi/Teamwork/Teams/<Team>/`) stay backward compatible;
  the ledger hash chain stays intact; no user-visible command is removed.

## Metrics

| Metric | Target | How measured |
|---|---|---|
| Test count | >= 60 | `pytest --collect-only -q` |
| CI matrix jobs green | 100% | `gh run list` |
| Runtime third-party deps | 0 | wheel `METADATA` |
| Privacy findings | 0 | `scripts/privacy_scan.py --history` |
| Broken doc links | 0 | `teamwork.py links` |
| Bootstrap time (empty dir) | < 5 s | acceptance test timing |
| Wheel install-to-first-command | < 60 s | `scripts/verify_release.py` |
| Repository hygiene files | 12+ | repo listing |

## Assumptions and open questions

| # | Item | Owner | Status | Resolution |
|---|---|---|---|---|
| 1 | Owner authorises force-push over the single `Initial commit` to erase the personal email in git history | CEO | resolved | User asked to publish without leaking private data; history is one commit containing only `LICENSE` |
| 2 | The previous identity domain is treated as private and is replaced by the configurable default `agents.nidvue.com` (`TEAMWORK_IDENTITY_DOMAIN`) | SecurityAuditor | resolved | The domain must not appear in the published tree or history |
| 3 | Package name on PyPI is `teamwork-agents` (the name `teamwork` is taken); import name is `teamwork` | ReleaseEngineer | resolved | Checked against the PyPI JSON API during research |
| 4 | PyPI publishing is prepared but not executed without an owner token | ReleaseEngineer | resolved | No token available; GitHub Release is the distribution channel |
| 5 | Stars cannot be guaranteed; the project optimises the *conversion* inputs (README, topics, demo, license, releases) | ProductManager | resolved | Documented in Risks.md |
| 6 | GitHub Actions is available for this repository | ReleaseEngineer | open | Verified on the first push |

## Sources

- [The /teamwork skill](https://github.com/Nidvue/Teamwork/blob/main/SKILL.md) - accessed 2026-10-17
- [GitHub Actions matrix builds](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs) - accessed 2026-10-17
- [PyPA: packaging a Python project](https://packaging.python.org/en/latest/tutorials/packaging-projects/) - accessed 2026-10-17
