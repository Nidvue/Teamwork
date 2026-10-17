# PROJECT - Teamwork

Owner: CEO. Single source of truth for *what done means*. No task closes without
mapping to an acceptance criterion here.

Related: [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md) · [AuditReport](AuditReport.md)

## Objective

Turn the private `teamwork` Pi skill (a 7,416-line stdlib-only `teamwork.py`
engine plus role charters, references and templates) into a self-contained,
reusable, cross-platform open-source project: an installable Python package that
ships the skill bundle, a full development → test → build → verify → release
pipeline, polished documentation aimed at adoption, and a public GitHub
repository that is safe to open (zero private information).

"Finished" means: a stranger can `pip install teamwork-agents` (or run the repo
in place) on Linux, macOS or Windows, bootstrap an autonomous multi-agent team
workspace in any project, and every claim in the README is backed by a CI run, a
test, or a released artifact — with no personal data anywhere in the tree or in
git history.

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
      over full git history; no personal email, no API key, no absolute personal
      path, no personal domain in any tracked file or commit - proof:
      `python3 scripts/privacy_scan.py --history`
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
      exits 0 from the repo and from `~/.pi/agent/skills/teamwork`, and `init`
      creates `Design.md` (and no `Imaging.md`) whose template carries the
      visual-asset sections - proof:
      `python3 ~/.pi/agent/skills/teamwork/scripts/teamwork.py imaging probe`
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
  at runtime; no secrets in the repo; must keep working as a Pi skill
  (`SKILL.md` at the repository root) *and* as a pip package.
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

- [The /teamwork skill](https://github.com/VisionPZ/Teamwork/blob/main/SKILL.md) - accessed 2026-10-17
- [GitHub Actions matrix builds](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs) - accessed 2026-10-17
- [PyPA: packaging a Python project](https://packaging.python.org/en/latest/tutorials/packaging-projects/) - accessed 2026-10-17
