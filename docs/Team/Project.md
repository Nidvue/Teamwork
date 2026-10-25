# PROJECT - Teamwork

Owner: CEO. Single source of truth for *what done means*. No task closes without
mapping to an acceptance criterion here.

Related: [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md) · [AuditReport](AuditReport.md) · [M9Acceptance](M9Acceptance.md)

## Objective

Turn the private `teamwork` skill into a self-contained, reusable,
cross-platform open-source **skill for coding agents**: one directory cloned into
the host's skill location, with the stdlib-only engine bundled inside it and also
distributable as the optional `teamwork-agents` package (built and released as a
GitHub-release wheel; not yet published to PyPI), a full development → test →
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
      `python3 scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt`
      **Green as measured on the merged revision** (`PASS - 0 finding(s)` over
      tree and full history). `--history` walks every ref, so an unmerged branch
      that quotes a private path turns it red until that branch is fixed or
      discarded: that is why the gate is read on the merged revision and not on a
      working branch. The earlier red note is kept in the gaps table (G-2, G-8),
      not in this criterion.
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
- [ ] AC-19 Tree hygiene: no unreferenced, duplicate or superseded file is left in
      the tree; every census hit is either deleted in a recorded task or justified
      in the Archive, and the hygiene guards stay green - proof:
      `python3 -m pytest -q tests/unit/test_hygiene.py` plus `teamwork.py audit`
- [ ] AC-20 Docs truth: every state claim in `docs/Team/` and the README (red /
      green / done / version / tag) matches a command re-run on the merged
      revision, and no contradiction is left inside one document - proof:
      `python3 scripts/check_release_consistency.py` plus `teamwork.py links`
- [ ] AC-21 Test-suite portability: the suite is green on a Windows host with
      Developer Mode off and no GNU make, because each such test works there or
      skips with a stated reason, and a regression test pins each guard - proof:
      `python3 -m pytest -q`

## M11 - Solid review pass (this engagement)

Objective restated from the user brief: review code, logic, workflow, documents
and files systematically; make each of them solid for its purpose; remove
unnecessary files; update stale ones. Non-goals: new engine features, a roster
redesign, PyPI publication.

Exit condition: AC-3, AC-5, AC-6, AC-11, AC-19, AC-20, AC-21 verified by a role
other than the author on the merged revision.

Baseline measured before any lane started (`7db810a`, win32, py3.13, `.venv`):
`pytest -q` -> 11 failed / 1217 passed / 28 skipped; `ruff check` and
`ruff format --check` clean; `links` 0 issues; `privacy_scan --tree --history`
PASS; `check_release_consistency` 0 problems; `audit` 0 problems on a fresh team
tree. The failures reproduce a single class: tests that need a privilege or tool
the host does not have, plus one real engine defect (`resources.self_invocation()`
returns a command `shlex.split` mangles on Windows).

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

## Traceability - AC to task to test

Owner: Product Manager. This section is a *method*, not a snapshot: it states which
AC each row closes, which task archived it, which test record proves it, and the
command that re-reads its state. It quotes no revision and no census count - the
commit that writes such a number changes it. Re-read a row with its proof command.

### How the three layers are wired today

| layer | where it lives | who writes it | how an AC is named |
|---|---|---|---|
| acceptance criterion | this file, `## Definition of done` | CEO | `AC-<n>` bullet |
| delivering task | `docs/Team/Archive.md` section per closed task; open work in `Roles/<Role>/TaskQueue.md` | the owning role | free text in `self-check` / evidence |
| test record | `.pi/Teamwork/Teams/Teamwork/Tests.md` via `teamwork.py tests add/run` | the role that ran it | keyed by layer/area, cited here as `<record id> (<layer>/<area>)` |

An AC carries no test-record id of its own, so the link is **documentary**: a row
names a record whose evidence line reproduces the row's proof command. That is why
every cell below carries the layer/area it claims - the guard
`tests/unit/test_traceability_matrix.py` re-resolves every cited record against
`Tests.md` and fails when a record is missing, not `passing`, or filed under a
different layer/area than the row claims.

### State rule

`state` is the conclusion of a run of that row's `proof command`, and it is only
credible because the column is checked against a second statement of the same
fact - the gaps table:

- `green` - every clause of the proof command exits 0, and no gap row blames this
  AC as failing;
- `red (G-n)` - at least one clause exits non-zero, and at least one named gap row
  names this AC together with a failure word.

Two guards hold the column, and they fail differently on purpose:

- `test_a_green_row_is_not_blamed_by_a_gap_and_a_red_row_is` reads the gaps table
  and refuses a contradiction between the two columns - cheap, and it catches an
  inconsistent edit;
- `test_every_deterministic_state_matches_a_real_run` **executes** the proof
  command of every row whose result is a pure function of the tree, and fails when
  the exit code disagrees with the claimed state.

The second one is the load-bearing guard, and it exists because editing prose can
satisfy any check that is inferable from prose: six review rounds proved that. Each
round the guard was widened around one observed hole, and each time the hole moved
one indirection out - first `state` was checked only for spelling, then the gap
cross-check could be defeated by editing both columns together, then the row to
re-run was read from a hand-kept list, so deleting an entry disabled the check for
that row. The version here therefore takes its commands from **this table's own
proof column** and nothing else: there is no list of protected rows to shorten, and
a mutant that edits a row has to make the row's real command agree with it.

Its bound is stated, not hidden. A row is re-run unless it appears in `EXEMPT` in
the guard, and every exemption names one of four reasons: the proof is this pytest
run (so a red suite already fails here), the proof reads the forge and a CI job
without credentials cannot re-read it (`AC-4`, `AC-7`, `AC-8`), a clause reads
the gitignored team tree, which drifts between runs, or - and this one was earned
in review round 9 - the proof asks the live board a question whose answer is only
true on a merged revision (`AC-11` runs `loop` and `audit`; while this
deliverable itself is under review, that board necessarily still lists it, so the
command exits 1 mid-review and 0 after the merge). `AC-3` is exempt as the first
reason: its proof cell opens with the `pytest -q` run and only its second clause
reads the team tree, so the drift reason is declared for that shape but no row
currently needs it. An exemption is not
a bare dict entry: it is a claim about what its row reads, and **this table has to
carry the evidence for it**. The guard holds one evidence pattern per reason -
`pytest` in the cell for `self`, `gh` / `verify_release.py` / a CI workflow for
`forge`, `tests plan` / `TEAMWORK_ROOT` / the team tree for `drift`, and
`teamwork.py loop` / `teamwork.py audit` for `inflight` - and fails an
exemption whose row's proof cell carries none of it, naming the AC and the reason.
So exempting `AC-12` as `drift` while its cell reads `ls LICENSE CHANGELOG.md
CITATION.cff` is a contradiction, not a silent skip. An exemption naming an
unknown reason, or a row the table no longer defines, fails the guard too; so does
a non-exempt row whose proof cell parses into no command.

The floor is relative for the same reason: the guard requires the number of rows
re-run to equal **rows minus exemptions**. An absolute floor let exempting a row
lower the bar without tripping it; the arithmetic now makes every exemption pay
for itself, so the residual limit is the four reasons above - each one readable,
and each one checked against the row that claims it - not an unchecked count.

Measured while this revision was written, all three on an extracted archive of the
committed tree: with `CHANGELOG.md` deleted and `AC-12` added to `EXEMPT` as
`drift`, the guard fails naming `AC-12` and the reason; dropping an exemption from
the dict while its row is skipped fails the relative floor; the unchanged tree
passes. A green row flipped to a red state that names a closed gap, and `AC-11`
flipped to green with its gap rewritten, each still fail the re-run guard on their
own with no other test edited.

`AC-4`, `AC-7`, `AC-8` are phrased against the forge (`gh run list`,
`gh release view`, `gh repo view`). They were read and are green, but a CI job
without credentials cannot re-read them, so they carry no gap and their proof is
the recorded command, not the guard.

### Forward map: AC -> proof -> task -> record -> state

| AC | proof target | archived task(s) | test record | proof command (read the run) | state |
|---|---|---|---|---|---|
| AC-1 | `scripts/verify_release.py` | developer T-0001, ceo T-0017 | TS-0018 (release/release) | `PYTHONPATH=src python scripts/verify_release.py` | green |
| AC-2 | `tests/acceptance/test_entrypoints.py` | ceo T-0017, T-0023, T-0026, T-0027 | none | `python -m pytest -q tests/acceptance/test_entrypoints.py` | green |
| AC-3 | `pytest -q`, `teamwork.py tests plan` | every closed task, per `docs/Team/Archive.md` | TS-0001 (goal/audit), TS-0005 (unit/engine), TS-0008 (acceptance/evidence), TS-0011 (goal/hygiene), TS-0014 (security/decisions), TS-0018 (release/release), TS-0022 (goal/pr), TS-0024 (integration/context-economy) | `PYTHONPATH=src python -m pytest -q` and `python scripts/teamwork.py tests plan` | green |
| AC-4 | `.github/workflows/ci.yml` | release-engineer T-0001 | none | `gh run list --json displayTitle,conclusion` | green |
| AC-5 | `scripts/privacy_scan.py` | security-auditor T-0001, ceo T-0003 | none | `python scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` | **green** - the shipped gate exits 0 over the tree and the full history after the authorized rewrite of the unpublished local history: the commit whose author a forge squash merge stamped from the signed-in operator account is no longer in this history, the archive blobs that quoted the address were rewritten to name the rule instead, and the one commit message that quoted a 40-hex object id now names the object by its role. The published side was never affected. The count is not pinned: every commit that documents a count raises it (D-20261019-CEO-15). |
| AC-6 | `teamwork.py links` | every closed task, per `docs/Team/Archive.md` | TS-0013 (goal/decisions), TS-0024 (integration/context-economy) | `python scripts/teamwork.py links` -> read the `# issues:` line | green |
| AC-7 | `.github/workflows/release.yml` | none | none | `gh release view v1.0.0 --json assets` | green (the AC pins `v1.0.0`, which exists; a newer tag does not break it - G-5) |
| AC-8 | repo metadata | none | none | `gh repo view --json description,repositoryTopics` | green |
| AC-9 | `tests/unit/test_portability.py` | architect T-0001, ceo T-0016 | none | `python -m pytest -q tests/unit/test_portability.py` | green |
| AC-10 | `tests/acceptance/test_full_loop.py` | none | none | `python -m pytest -q tests/acceptance/test_full_loop.py` | green |
| AC-11 | `teamwork.py loop`, `teamwork.py audit` | ceo T-0015, T-0023, T-0026, T-0027 | none | `python scripts/teamwork.py loop` and `python scripts/teamwork.py audit` | green (read on a merged revision - G-4) |
| AC-12 | `LICENSE`, `CHANGELOG.md`, `CITATION.cff` | none | none | `ls LICENSE CHANGELOG.md CITATION.cff` | green |
| AC-13 | `tests/unit/test_imaging.py` | designer T-0001 | none | `python -m pytest -q tests/unit/test_imaging.py` | green |
| AC-14 | `scripts/teamwork.py imaging probe` | none | none | `python scripts/teamwork.py imaging probe` | green |
| AC-15 | `tests/unit/test_skill_contracts.py` | designer T-0001, ceo T-0031 | none | `python -m pytest -q tests/unit/test_skill_contracts.py` | green |
| AC-16 | `tests/unit/test_skill_contracts.py` | designer T-0001, ceo T-0031 | none | `python -m pytest -q tests/unit/test_skill_contracts.py` | green |
| AC-17 | `tests/unit/test_skill_contracts.py`, `docs/Team/Release.md` | designer T-0001, ceo T-0031 | none | the same pytest plus `ls docs/Team/Release.md` | green |
| AC-18 | `tests/unit/test_skill_contracts.py`, `teamwork.py links` | every closed task, per `docs/Team/Archive.md` | TS-0013 (goal/decisions) | the same pytest plus `python scripts/teamwork.py links` | green |

The per-lane work of the M1-M4 lanes lives in the Archive sections rather than in
one commit per lane, so an AC's proof is usually a file in the tree.

### Reverse map: test record -> AC (derived, never hand-edited)

This block is the forward table read backwards: the guard recomputes it from the
rows above and fails if the two disagree, so it cannot drift into a second,
contradicting statement of the same facts.

```
TS-0001: AC-3
TS-0005: AC-3
TS-0008: AC-3
TS-0011: AC-3
TS-0013: AC-6, AC-18
TS-0014: AC-3
TS-0018: AC-1, AC-3
TS-0022: AC-3
TS-0024: AC-3, AC-6
no AC: TS-0016, TS-0020
```

`TS-0016` (`requirements/traceability`) is this section's own record. `TS-0020`
(`acceptance/context-economy`) passes, but no acceptance criterion owns the
context-economy contract it proves - that is gap G-7, not a green row.

### Gaps and owners

| id | gap | how to read it | owner |
|---|---|---|---|
| G-1 | The machine criterion store holds one criterion, `AC-1`, whose text is the *old audit-fixes* criterion, not this file's AC-1. `criteria list` and `trace AC-1` therefore report the wrong artifact for the id. | `python scripts/teamwork.py criteria list` then `trace AC-1` and `trace AC-2` (the latter resolves nothing) | CEO (re-key the store with `criteria add/verify` per AC, or prefix the historical one) |
| G-2 | AC-5 was red: `privacy_scan` reported `home-path` and `agent-config` findings in `docs/Team/Archive.md` that `.github/privacy-allow.txt` did not bless. **Closed** by the three fully escaped literals in that allowlist plus the quoted-evidence scope in the scanner; the row stays listed because it explained a red state for several revisions. | `python scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` -> `PASS - 0 finding(s)` | CEO T-0031, T-0034, T-0048 (closed) |
| G-3 | AC-6 and AC-18 link health: the four `compare/v1.0.2...*` strings in `docs/Team/Archive.md` are quoted evidence of a past review finding and are deliberately not link-checked, so `links` reports no issue. This gap is closed; it stays listed because the earlier red state cited it. | `python scripts/teamwork.py links` -> `# issues: 0` | CEO T-0032 (closed) |
| G-4 | AC-11 was red because it was downstream of G-2 and the then-open tasks: `loop` returned CONTINUE and `audit` reported problems. **Closed** once every task, dispute and gate override cleared, so `loop` prints STOP and `audit` finds zero problems; the row stays listed because it explained a red state for many revisions. **This proof only reads true on a merged revision**: while any deliverable is still open the board it reads necessarily contains that deliverable, so the row is exempt from the re-run guard with the reason `inflight` instead of being re-executed mid-review. | `python scripts/teamwork.py loop` -> STOP, `python scripts/teamwork.py audit` -> `# problems found: 0` (measured at `8b4585b`, a merged revision) | CEO (closed) |
| G-5 | AC-7 pins `v1.0.0` while newer tags are released; AC-4 and AC-9 are phrased against "the pushed revision", which is ambiguous while local merges are ahead of `origin/main`. | `gh release list --limit 5`; `git log --oneline origin/main..main` | CEO (re-word the AC, not re-do the release) |
| G-6 | AC-3 was red because required test layers were missing, so its `tests plan` clause exited non-zero. **Closed**: every staffed role has designed and run a record of its own layer. | `python scripts/teamwork.py tests plan` -> no `# GAP` line, rc 0 | the owning role per area; PM tracks it (closed) |
| G-8 | AC-5 was red at this revision, and honestly so: the shipped gate failed on commit metadata - the author email a forge squash merge stamped from the signed-in operator account, one high-entropy false positive in a commit message, and the pre-redaction blobs of `docs/Team/Archive.md`. **Closed** by the authorized rewrite of the unpublished local history: the chain was rebased onto the published tip, the archive blobs were redacted, the one commit message that quoted a 40-hex object id was re-worded to name the object by its role, and the cited revisions were re-pointed at the rewritten commits. The published side was clean throughout and is unchanged. What the rewrite cannot undo: the author identity of the retained object is already disclosed to anyone who requests its SHA (D-20261021-Reviewer-1) - the rewrite protects the published history, it cannot un-disclose. | `python scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` -> `PASS - 0 finding(s)` | CEO T-0003 (closed by the authorized rewrite; the exemption rule is D-20261019-CEO-15) |
| G-7 | No AC owns the context-economy contract, so the acceptance record that proves it (`TS-0020`, passing) has no requirement to escalate against or regress behind. | the reverse map above, then `tests plan` | CEO + Product Manager |

### Requirements-layer contract for this area

The traceability area requires exactly one test layer, `requirements`, and `TS-0016`
satisfies it: `teamwork.py tests plan` reports the `traceability` row with `req+`
marked and role coverage for `product-manager` under `req`. `TS-0016` is re-run and
re-bound to the new revision, evidence and artifact on every records pass, and this
section is its deliverable.
