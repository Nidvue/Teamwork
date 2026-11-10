# Changelog

Owner: Technical Writer.

Related: [Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md) · [Project](docs/Team/Project.md)

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/Nidvue/Teamwork/compare/v1.0.2...HEAD)

## [1.1.0](https://github.com/Nidvue/Teamwork/releases/tag/v1.1.0) - 2026-10-20

### Added

- **Roster tiers, and a slim roster by default**: `init --roster slim|standard|full`
  replaces a 15-role hand-written list with a recipe, and `slim` (ceo, architect,
  developer, tester, reviewer-1, reviewer-2) is now the default - 213 kB of startup
  charters summed over the instances, against 552 kB at `full`. A trimmed role leaves a lane, not a gate:
  `tests plan` only requires layers of staffed roles, and `required_tribunal` never
  falls below two signers, with the Reviewer as the neutral seat. Two holes this
  exposed are closed: a tribunal of one used to let the CEO sign and resolve their
  own dispute, and `init` now prints the folded lanes and warns when a
  gate-critical role is missing.

- **`pi-teamwork` package**: the skill now ships as a pi package (`pi.skills` +
  `pi.prompts`, host packages as `peerDependencies` only). A pi session installs it
  with `pi install npm:pi-teamwork` and gets two skills: `/skill:teamwork` (the
  protocol) and `/skill:teamwork-pi` (the pi tool mapping: `subagent` fan-out,
  `schedule.create` pulse, `subagent_supervisor` replies, `subagent stop`), plus
  the `teamwork-pulse` and `teamwork-review` prompt templates. The tarball is
  assembled by `make package` from one source tree, so the pip package and the npm
  package never drift.

- **Per-queue PR resolution**: `pr open` used to match a task id across the whole
  `Reviews.md`, so a second role owning the same id reopened and rewrote the first
  role's PR (measured: the security lane's `T-0001` re-opened the merged developer
  `P-0020`). `find_pr`/`find_pr_exact` now accept the task's branch and a task-id
  match only resolves inside that branch.

- **Parallel review lanes**: `pulse` hands each unclaimed deliverable awaiting review
  to a different idle Reviewer lane, and `review --claim` / `--release` record the
  holder on the task with a lease, a takeover after it lapses, and a verdict that
  clears it.

- **Evidence packets**: `tests run`, `selfcheck` and `review` accept
  `--baseline`, `--artifact` (repeatable) and `--replay`, so the author and the
  Reviewer record the same five-part packet. Artifacts must exist in
  the repository, are hashed (`path:sha256:bytes`) and the digest is appended to
  the hash-chained ledger, so evidence is a replayable packet instead of a
  sentence.
- **Verifiable closing manifest**: `ledger export` stops pinning the append-only
  `docs/Team/Archive.md` (its entry lands at review time, so a committed digest was
  stale by construction) and says why in `how_to_verify`; the other artifacts and
  the ledger head still verify with `sha256sum -c`.
- **Repro-first gate**: `tests repro <T-id> --pre-rev ... --post-rev ...` records
  a fail -> pass transition on the defect task and refuses a single revision, a
  pre-run that does not read as failing, or a pre-revision that is not an
  ancestor of the post-revision.
  `task add --bug` marks a defect fix, whose self-check is refused until that
  record exists; `audit` reports a closed bug task without one.
- **README "For agents"**: host detection, the clone, `selftest` verification, the
  startup routine and the hard rules, written for the agent that installs and
  drives the skill itself.
- **README "Common ways to use it"**: eight trimmed real transcripts - new project,
  feature in an existing repository, red CI, manual steering, pulse/parallel,
  resume, ledger proof, model routing.
- Tests assert the skill-first surfaces, the demo's line order and the new
  namespace, so the framing and the URLs cannot silently regress.
- **Commit identity audit**: `teamwork identity --audit --range <base>..HEAD`
  fails when a commit was not authored and committed by the acting role, and CI
  runs it on every pull request and push. The engineering policy now states that
  the role that does the work commits it, that the CEO commits only CEO-owned
  documents and the bootstrap, and that the product identity is never valid.

### Changed

- **A passing review merges the PR at once**: `review --result pass` is now the
  merge trigger. The Reviewer that verified the revision lands it on the base
  branch and deletes the branch in the same command, so an approved deliverable
  never waits in a second queue for a different lane to merge it. Independence is
  enforced against the **author** - nobody reviews or merges their own work - not
  against a second Reviewer; `--keep-branch` keeps the branch and `--no-merge`
  separates the landing step again. A pass that cannot land (a conflict, a dirty
  tree) keeps the recorded verdict and prints the exact `pr merge` to finish,
  saying plainly that the work is not in the base yet.
- **GitHub Actions bumps**: `anchore/sbom-action` 0.24.3,
  `actions/attest-build-provenance` `4d101475`, and
  `softprops/action-gh-release` `efb35369` landed as one reviewed commit; every
  action stays pinned to a full commit SHA, never a moving tag.
- **Repository moved to `Nidvue/Teamwork`**: badges, clone commands, `pyproject`
  URLs, `mkdocs.yml`, `CITATION.cff` and every documentation link now use the new
  namespace. Only the historical audit records keep the former handle, because
  rewriting a quoted command would falsify evidence.
- **Teamwork is presented as a skill, not a standalone app**: the README, docs
  home, install guide, quickstart and the animated demo all start from one clone
  into the agent host and a request that names the skill; the Python package is
  documented as an optional engine over the same code.

- **One generic protocol, no host-specific instructions**: the README, docs home,
  install guide, quickstart, CLI reference and the animated demo install the skill
  into the project or user skills directory and start it by naming the skill.
  On the adoption surfaces, concrete host tools live only in
  `references/Adapters.md`, the optional adapter
  reference, so the same text serves every agent.

### Security

- **The privacy scan now covers local and agent-host leakage**: tracked paths that
  are private host state (`.pi/agent/` auth, settings, sessions, model stores),
  credential files (`auth.json`, `.env`, `.netrc`, `.npmrc`, `.pypirc`, SSH keys,
  `.aws/credentials`, `.kube/config`, `.docker/config.json`), key material and
  local working state (`.pi/`, virtualenvs, build output, caches, `Scratch/`) fail
  the gate; so do JSON config objects with a live credential, provider tokens
  (`gsk_`, `xai-`, `pplx-`, `glpat-`, `npm_`, `hf_`, `sk_live_`, SendGrid) and
  WSL/mounted home paths. Quoting `.pi/Teamwork/...` in a document is not host
  configuration, but a **tracked** file under the workspace fails; legitimate
  project paths (`.agents/skills/`, `.claude/skills/`, `.env.example`, `auth.py`)
  stay clean.

- **`.gitignore` completed**: Python, packaging, test, doc-build, editor and OS
  noise are ignored; credentials are denied by name (`auth.json`, `.env*`,
  `*.pem`, SSH keys, `.netrc`, `.npmrc`, `.pypirc`); local agent-host state
  (a host's `settings.local.json`, session/transcript directories, aider history)
  is ignored while a committed skill bundle under `.agents/skills/` or
  `.claude/skills/` stays tracked. A `.gitignore` deny entry is not treated as a
  leak by the privacy scan.

- **Packaging metadata**: the `pyproject` keyword `pi` became `agent-skills`, so the
  package is not advertised as one host's add-on.

- **Forge merge refs**: the synthetic `Merge <sha> into <sha>` commit a forge
  creates for a pull request carries the PR author's account identity. The history
  scan skips that identity (message and blobs are still scanned) so a clean branch
  is not failed by the forge account; squash-only merges keep such a commit out of
  `main`.

### Fixed

- **`pr merge` built the merge commit but never advanced the base branch**: a PR
  record whose `base` held a revision instead of a branch name (as P-0022 did)
  made `git checkout <base>` detach HEAD, so the merge commit was created
  off-branch: the merge was reported as done and recorded everywhere, while
  `main` still pointed at the pre-merge tip and the merge commit was reachable
  only by fast-forwarding the base by hand. The base is now resolved to the
  local branch pointing at the recorded revision (preferring `main`, accepting a
  unique match) and a revision no branch points at is refused with exit `2`
  before anything is merged; the merge also runs in the work tree that has the
  base checked out, so starting it from an instance worktree no longer fails on
  `git checkout` or advances the wrong checkout
  (`tests/unit/test_pr_merge_base_advance.py`).
- **the archive entry never reached the base branch**: the entry is written by
  the review pass, in whichever work tree that pass ran in - in the per-instance
  layout a lane work tree - so after the merge the base had no archived record of
  the shipped work. Entries are now written where the task's base branch is
  checked out, and `pr merge` appends a missing entry on the base before it
  commits the records, so the entry rides along in the same `chore(records)`
  commit and is repointed at the merge revision in that same commit.
- **`pr merge` left the archive rewrite uncommitted**: the `branch / merge`
  field of `docs/Team/Archive.md` was rewritten in the work tree after the merge
  commit, so the base branch kept `pending`, the tree stayed dirty, and the next
  merge in the same repository died on `git checkout` ("your local changes would
  be overwritten"). The rewrite now lands as its own `chore(records)` commit on
  the base branch (Reviewer identity, one `pr.merge.archive` ledger record), so
  the committed archive names the real merge revision
  (`tests/unit/test_context_economy.py`).
- **archive rewrite could erase an earlier merge**: a task reworked after a
  merge reuses its branch name, so `docs/Team/Archive.md` held two entries naming
  the same branch. The rewrite repointed every match, overwriting the first merge
  revision with the second. Only the newest entry still saying `pending` is
  repointed now, and a branch with nothing pending is reported as unchanged.
- **`pr merge --pr <task>` could select an already-merged PR**: a task reworked
  after a merge keeps the old PR record, so matching on the task id alone could
  return the branch already in the base. `find_pr` and `find_pr_exact` take an
  optional branch and every PR lookup in the merge path passes the task's current
  branch, so the live record is the one that merges.
- **`ensure_gitignore` bootstrap**: a repository whose `.gitignore` already
  covered a rule with a glob (`.env.*` covers `.env.local`) gained a dangling
  section header and redundant lines on every `init`/`repo`. Coverage is now
  pattern-aware, a header is only appended together with a missing entry it
  introduces, and an empty file no longer starts with a blank line
  (`tests/unit/test_gitignore_bootstrap.py`).
- **Gate-forging metadata injection**: a task/memory body line that looked like
  `- review_status: passed`, or a newline in `--evidence`/`--note`/`--text`, could
  forge lifecycle state. Metadata parsing now stops at the body boundary, scalar
  values are collapsed to one line, and record headers inside a body are escaped.
- **`ledger repair` self-deadlock**: the repair path held `ledger.lock` and then
  called `ledger_append`, which took the same non-reentrant lock. Repair now uses
  a reentrant-safe append and a torn tail is trimmed before the next record.
- **Path traversal**: agent, role and provider names became raw path components;
  `init --agents ../../x` and `slot --provider ../../x` could write outside the
  workspace. Every path component now goes through `safe_component()`.
- **Cross-role work**: a task could be claimed by another role, and a self-check
  by a foreign role could claim unclaimed work. Claims and self-checks now stay
  on the owning role's queue.
- **Review/PR races**: `pr open`/`pr merge` wrote `TaskQueue.md` and `Reviews.md`
  outside the role/reviews locks, and could lose a concurrent verdict or claim.
  The write order is now merge -> role -> reviews, with a re-read before writing.
- **Stale claims**: a midnight-based age was compared to a 90-minute TTL, so a
  task claimed earlier the same day looked abandoned. Staleness now uses whole
  days and ignores a live slot lease.
- **Decision ids**: two decisions by the same role on the same day shared one id;
  a `-2`, `-3` suffix now keeps them distinct.
- **Model routing**: `model set product-manager` was stored as an agent override
  because the name contains a hyphen; the target is now resolved against the
  actual instances first.
- **Audit manifest anchor**: a re-created workspace was reported as a truncated
  ledger because the committed manifest came from the previous tree. The manifest
  is now scoped by a per-workspace `TeamId`.
- **Privacy report context**: the masked report could republish a neighbouring
  secret from the same line; `context` is no longer emitted. History scanning also
  follows reflogs, UTF-16 text is decoded, URLs/paths/digits are not credentials,
  and non-blob git objects no longer desynchronise the batch reader.
- **Repo-local role identity**: `init`/`repo` now writes the CEO role mailbox to
  the repository's local `user.name`/`user.email` when no local email exists, so
  a plain `git commit` cannot inherit the operator's personal identity. An
  existing local identity is never overwritten.
- **CLI exit-code contract**: the reference and architecture now state the codes
  the binary actually returns - `2` for usage and the gates that opt into it,
  `1` for a generic error / role refusal / `loop` CONTINUE, `3` for nothing to
  dispatch, `4` for a lock timeout.
- **Modular engine**: the 9.6k-line `engine.py` is now a thin command layer over
  typed `config`, `io`, `names`, `layout`, `records`, `gitutil` and `imaging`
  modules. Behaviour is unchanged; the suite and coverage floor guard the split.
- **Release verification**: `verify_release.py` now checks the artefact version,
  inspects the sdist, drops every ambient `TEAMWORK_*` variable in the smoke test,
  and writes `SHA256SUMS` only after every check passes.
- **CI integrity**: actions are pinned to full commit SHAs, the identity audit
  covers the pushed range and skips external contributors by default, the release
  workflow tests and verifies the tagged revision, SBOMs describe `dist/`, and the
  docs site excludes the internal `docs/Team/` working documents.

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
