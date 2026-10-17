# Changelog

Owner: Technical Writer.

Related: [Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md) · [Project](docs/Team/Project.md)

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/Nidvue/Teamwork/compare/v1.0.0...HEAD)

### Changed

- **Repository moved to `Nidvue/Teamwork`**: badges, clone commands, `pyproject`
  URLs, `mkdocs.yml`, `CITATION.cff` and every documentation link now use the new
  namespace. Only the historical audit records keep the former handle, because
  rewriting a quoted command would falsify evidence.
- **Teamwork is presented as a skill, not a standalone app**: the README, docs
  home, install guide, quickstart and the animated demo all start from one clone
  into the agent host and a `/teamwork` prompt; the Python package is documented
  as an optional engine over the same code.

- **One generic protocol, no host-specific instructions**: the README, docs home,
  install guide, quickstart, CLI reference and the animated demo install the skill
  into the project or user skills directory and start it by naming the skill.
  Concrete host tools live only in `references/Adapters.md`, the optional adapter
  reference, so the same text serves every agent.

### Security

- **The privacy scan now covers local and agent-host leakage**: tracked paths that
  are private host state (`.pi/agent/` auth, settings, sessions, model stores),
  credential files (`auth.json`, `.env`, `.netrc`, `.npmrc`, `.pypirc`, SSH keys,
  `.aws/credentials`, `.kube/config`, `.docker/config.json`), key material and
  local working state (`.pi/`, virtualenvs, build output, caches, `Scratch/`) fail
  the gate; so do JSON config objects with a live credential, provider tokens
  (`gsk_`, `xai-`, `pplx-`, `glpat-`, `npm_`, `hf_`, `sk_live_`, SendGrid) and
  WSL/mounted home paths. Legitimate project paths (`.pi/Teamwork/`, `.env.example`,
  `auth.py`) stay clean.

### Added

- **README "For agents"**: host detection, the clone, `selftest` verification, the
  startup routine and the hard rules, written for the agent that installs and
  drives the skill itself.
- **README "Common ways to use it"**: eight trimmed real transcripts - new project,
  feature in an existing repository, red CI, manual steering, pulse/parallel,
  resume, ledger proof, model routing.
- Tests assert the skill-first surfaces, the demo's line order and the new
  namespace, so the framing and the URLs cannot silently regress.

## [1.0.2](https://github.com/Nidvue/Teamwork/releases/tag/v1.0.2) - 2026-10-17

### Added

- **Automatic model routing** from the runtime environment: `teamwork model auto`
  detects the agent host (pi, claude, opencode, codex, cursor, gemini), routes the
  strongest available model to the decision lanes and the economy model to the
  mechanical lanes, and never invents a model id (`--apply`, `--json`).
- `TEAMWORK_AGENT_HOST` to pin host detection deterministically.
- The site is served from the custom domain **teamwork.nidvue.com**.

### Changed

- Positioning: Nidvue Teamwork is published as a **skill for any coding agent**;
  the stdlib-only engine is the tool the skill calls and the package is optional.
- Branding: the master brand **Nidvue** precedes the product name in the README,
  the site, the docs, the package metadata and the file headers; the Nidvue mark
  from nidvue.com is bundled and used in the README and the site (with a trademark
  note in NOTICE).

### Fixed

- The release workflow fails when the tag and the package version disagree.

## [1.0.1](https://github.com/Nidvue/Teamwork/releases/tag/v1.0.1) - 2026-10-17

### Added

- Run on **any agent host**: `references/Adapters.md` maps the six host operations
  to Pi, Claude Code, opencode, Codex, Cursor and a generic shell, with installation
  paths and degraded modes.
- Run against **any git host**: `references/Remotes.md` states the repository and CI
  integrity policy (protected default branch, no force-push, required checks on the
  exact revision, non-author approval, squash-only merges, protected `v*` tags,
  least-privilege CI, drift checks) and maps it to GitHub, GitLab, Bitbucket,
  Gitea/Forgejo and Azure DevOps.
- A canonical **lint / format / type toolchain per language**, enforced in CI.
- **Warnings are errors**: `pytest filterwarnings = ["error"]`, and every workflow
  action moved off the Node-20-deprecated majors.
- A **naming policy** (PascalCase team directories, ecosystem-correct file names)
  and **commit rebase/squash hygiene** (one commit per task).
- Several **Reviewers run in parallel** from one shared queue.
- Imaging is owned by the Designer, raster and vector, with a
  generate-review-improve loop.

### Fixed

- The privacy scan allows GitHub service mailboxes (`support@github.com`), and no
  longer reads a dotted identifier as a credential.
- `ledger export` writes `AuditManifest.md` instead of overwriting the Security
  Auditor's `AuditReport.md`, and never embeds the absolute checkout path.
- The engine pins `newline="\n"` on every text write without using the Python
  3.10-only `write_text(newline=...)`, so 3.9 stays supported.

### Security

- The initial commit's personal author identity was purged; the repository was
  recreated so no unreachable object or pull ref carries it.
- The team mailbox domain is `agents.nidvue.com`; every commit uses a role mailbox.

## [1.0.0](https://github.com/Nidvue/Teamwork/releases/tag/v1.0.0) - 2026-10-17

### Added

- Installable `teamwork-agents` package exposing the `teamwork` console script
  and `python -m teamwork`.
- The skill bundle (`SKILL.md`, `roles/`, `references/`, `templates/`) is
  force-included into the wheel at `teamwork/data/`.
- Documentation site (MkDocs Material) with installation, quickstart, CLI
  reference, architecture and CI guides.
- Community files: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`,
  `CITATION.cff` and this changelog.
- Offline `teamwork selftest` smoke check and `--version` reporting.
- Hash-chained ledger with `ledger verify`, `ledger export` and `trace`.
- CI pipeline: lint, type-check, the test matrix on Linux/macOS/Windows and
  Python 3.9/3.11/3.13, build + wheel verification, privacy scan and strict docs
  build.

### Changed

- Extracted the 7,416-line `teamwork.py` monolith into `src/teamwork/`, keeping
  `scripts/teamwork.py` as a thin compatibility shim.
- Resource discovery now resolves the skill bundle from a checkout and from an
  installed wheel.
- The runtime has no third-party dependencies; file output is UTF-8 with `\n`
  newlines for byte-identical results across platforms.

### Security

- Added a privacy scanner that runs over the working tree and the full git
  history; no personal data, credentials or keys are published.
- Commit identity defaults to the configurable `agents.nidvue.com` domain.
- Private vulnerability disclosure is handled exclusively through GitHub Security
  Advisories.
