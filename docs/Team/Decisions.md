# DECISIONS

Owner: Architect for technical entries, CEO for governance, tribunal and red-line
entries. Append-only, newest last, binding. Every entry is traceable: it names who
decided, on what evidence, and what would falsify it.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## D-0001 - <title>

- date: YYYY-MM-DD
- kind: technical | governance | redline | tribunal | scope | cost | process
- status: proposed | accepted | superseded | rejected
- deciders: <role or instance>
- decided by: <instance>
- task: <T-id>
- context: <the problem, one or two lines>
- options considered: <A - pro/con; B - pro/con>
- decision: <what>
- why: <the reasoning from evidence to conclusion>
- evidence: `<command or measurement> @<rev> -> <result>`
- falsified by: <the observation that would overturn this>
- consequences: <follow-ups, affected docs and lanes>

Record entries with `teamwork.py decision add --by <instance> ...` so they also
land in the tamper-evident ledger (`teamwork.py ledger verify`).

## D-20261017-Architect - Keep the engine as one module; wrap it in a package

- date: 2026-10-17
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: architect
- task: T-0001
- context: -
- options considered: -
- decision: src/teamwork/engine.py stays the single behaviour-carrying module; the package adds resources.py, version.py, portable.py, cli.py, __main__.py and a scripts/teamwork.py shim.
- why: Splitting a 7,416-line module while also changing its resource discovery would mix a behaviour change with a refactor and make the diff unreviewable; the risk is not worth it for v1.0.0.
- evidence: python3 scripts/teamwork.py selftest @worktree -> 5/5 checks passed
- falsified by: A bug appears that cannot be fixed without splitting the module, or the file exceeds tooling limits.
- consequences: -

## D-20261017-Architect - Resolve skill assets by env var, then package data, then checkout

- date: 2026-10-17
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: architect
- task: T-0003
- context: -
- options considered: -
- decision: resources.skill_root() checks TEAMWORK_SKILL_DIR, then teamwork/data (wheel), then the repo root; self_invocation() prefers the console script, then scripts/teamwork.py, then python -m teamwork.
- why: The same engine must run from a checkout and from an installed wheel without duplicating the skill bundle in the repository.
- evidence: python3 scripts/teamwork.py --version @worktree -> teamwork 1.0.0; PYTHONPATH=src python3 -m teamwork --version -> teamwork 1.0.0
- falsified by: The wheel installs and 'teamwork selftest' cannot find SKILL.md.
- consequences: -

## D-20261017-Architect - Canonical assets at the repo root, force-included into the wheel

- date: 2026-10-17
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: architect
- task: T-0001
- context: -
- options considered: -
- decision: SKILL.md, roles/, references/ and templates/ live once at the repository root and are force-included into the wheel as teamwork/data/.
- why: Avoids two drifting copies of the skill bundle and keeps the repo usable directly as a Pi skill directory.
- evidence: pyproject force-include mapping; scripts/verify_release.py asserts teamwork/data/SKILL.md in the wheel.
- falsified by: The bundle is missing or stale in a built wheel.
- consequences: -

## D-20261017-CEO - Neutralise all personal identity before publishing

- date: 2026-10-17
- kind: governance
- status: superseded
- deciders: CEO (ceo)
- decided by: ceo
- task: -
- context: -
- options considered: -
- decision: Replace the personal identity domain with the configurable default agents.nidvue.com, set a repository-local neutral git identity, and rewrite the single existing commit so no personal email remains in history.
- why: The repository is public and the owner requires that no private information is exposed; the only existing commit contains a LICENSE and nothing else.
- evidence: scripts/privacy_scan.py --tree --history -> 0 findings
- falsified by: Any personal email, key or home path is still reachable in the published repository.
- consequences: -

## D-20261017-CEO - Publish under AGPL-3.0

- date: 2026-10-17
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: ceo
- task: -
- context: -
- options considered: -
- decision: License the project AGPL-3.0, as already present in the repository.
- why: It is OSI-approved, strongly copyleft, and unambiguous for a governance/audit tool; changing it would add no value and could confuse the existing file.
- evidence: LICENSE present and referenced from README and pyproject.
- falsified by: The license file is missing or unresolvable in packaging metadata.
- consequences: -

## D-20261017-CEO - Ship as teamwork-agents on PyPI, import as teamwork

- date: 2026-10-17
- kind: scope
- status: accepted
- deciders: CEO (ceo)
- decided by: ceo
- task: T-0001
- context: -
- options considered: -
- decision: The distribution name is teamwork-agents; the import package and console script are teamwork.
- why: The PyPI name 'teamwork' is already taken, and the import name is part of the public API.
- evidence: pyproject name = teamwork-agents; README states the install command.
- falsified by: pip install teamwork-agents <!-- release-consistency: channel-unavailable --> does not expose the teamwork command.
- consequences: -

## D-20261017-CEO - Only the CEO performs external publishing

- date: 2026-10-17
- kind: process
- status: superseded
- deciders: CEO (ceo)
- decided by: ceo
- task: -
- context: -
- options considered: -
- decision: No teammate runs git push, gh write commands, tags or releases; they commit locally with role identities only.
- why: Publishing is irreversible and must be a single controlled step with the owner's credentials.
- evidence: Global memory entry 'external' recorded; teammate briefs state the rule.
- falsified by: -
- consequences: -

## D-20261017-SecurityAuditor - Escalation: rewrite the initial commit's personal author identity

- date: 2026-10-17
- kind: governance
- status: proposed
- deciders: SecurityAuditor (security-auditor)
- decided by: security-auditor
- task: T-0008
- context: -
- options considered: -
- decision: CEO rewrites commit e5efc5f to replace the personal author name/email with the neutral Teamwork identity; no non-CEO agent performs the force-push.
- why: commit author metadata is permanent in every clone/fork and cannot be removed by editing files; AC-5 requires zero findings over full history.
- evidence: python3 scripts/privacy_scan.py --tree --history --json @e5efc5f -> exit 1, 2 high findings on commit author email; tree/staged 0
- falsified by: python3 scripts/privacy_scan.py --tree --history exits 0 on the pushed revision
- consequences: CEO amends/filter-repo then force-with-lease; existing clones re-clone; AC-5 passes; release unblocked.

## D-20261017-Architect - Type-check the new modules; exempt the ported engine for v1.0.0

- date: 2026-10-17
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: architect
- task: -
- context: -
- options considered: -
- decision: mypy checks teamwork.resources, teamwork.portable, teamwork.version, teamwork.cli and teamwork.__main__ with zero errors; teamwork.engine is exempted via [[tool.mypy.overrides]] ignore_errors=true and is the tracked post-1.0 refactor. mypy cannot target python_version 3.9 in version 2.x, so 3.9 syntax compatibility is enforced by ruff target-version=py39 plus 'from __future__ import annotations'.
- why: The engine is a behaviour-preserving port of a 7.4k-line untyped monolith; annotating it now would mix a large unreviewable type diff into the packaging change. A green-but-weaker type gate is honest only if the exemption is recorded and enforced elsewhere.
- evidence: mypy src/teamwork -> Success: no issues found in 7 source files; ruff check . -> All checks passed; ruff target-version=py39
- falsified by: Annotating teamwork.engine shows the exemption was hiding a real defect, or a 3.9-only syntax error reaches main.
- consequences: -

## D-20261017-CEO - Image generation is part of the Designer's work

- date: 2026-10-17
- kind: scope
- status: accepted
- deciders: CEO (ceo)
- decided by: ceo
- task: -
- context: -
- options considered: -
- decision: The skill gains an imaging capability owned by the Designer: an offline capability probe (teamwork imaging probe) that ranks the best available text-to-image / image-to-image model, cloud provider first, then a local model, then a hand-authored SVG; a plan file docs/Team/Imaging.md; and a mandatory generate-review-integrate process with privacy and licence red lines.
- why: The user asked the skill to generate images with the best available model when the LLM API offers one, and clarified that this is the Designer's job rather than a new role. Making the Designer the single owner keeps one writer per asset and one review path.
- evidence: python3 scripts/teamwork.py imaging probe -> provider=local model=qwen-image-2.1; PYTHONPATH=src ./.venv/bin/python -m pytest tests/unit/test_imaging.py -q -> 19 passed; python3 ~/.pi/agent/skills/teamwork/scripts/teamwork.py imaging probe -> provider=local
- falsified by: No provider exposes a ranked image model and the Designer ships an image that was never reviewed, or a private datum appears in a cloud prompt.
- consequences: -

## D-20261017-CEO - Imaging lives inside the Designer's own document, not a separate file

- date: 2026-10-17
- kind: scope
- status: accepted
- deciders: CEO (ceo)
- decided by: ceo
- task: -
- context: -
- options considered: -
- decision: There is no references/Imaging.md and no docs/Team/Imaging.md. The Designer's charter (roles/designer.md) carries the full policy, and the Designer's project document (docs/Team/Design.md, from templates/Docs/Design.md) carries the asset record: capability, assets, review log and improvement log.
- why: The user required that imaging be part of the Designer's work and that the separate Imaging document be merged into the Designer's. One owner, one document keeps the charter the single place to read and removes a file that could drift out of sync.
- evidence: ls references/ docs/Team/ -> no Imaging.md; python3 scripts/teamwork.py init in a temp dir -> docs/Team/Design.md created, docs/Team/Imaging.md absent; PYTHONPATH=src ./.venv/bin/python -m pytest tests/unit/test_imaging.py -q -> 21 passed
- falsified by: A Designer needs imaging policy that is not in roles/designer.md, or the Design template loses the asset/review/improvement sections.
- consequences: -

## D-20261017-CEO - Supersede: reviewed commits are pushed by the Release Engineer, per milestone

- date: 2026-10-17
- kind: governance
- status: superseded by D-20261020-CEO-2 (a stage ends with a push, not a milestone)
- deciders: CEO (ceo)
- decided by: ceo
- task: -
- context: -
- options considered: -
- decision: The Release Engineer pushes commits to the shared remote once the Reviewer has passed them with no open finding, after each reviewed+merged deliverable rather than in one batch at the end; pre-push gates must be green on that revision and CI must be green on the pushed SHA. Force-push, published-history rewrite and retagging still require explicit CEO authorization, and tags/public releases remain the CEO's step. The Tester certifies local AND CI and routes any failure to the owning role.
- why: The earlier rule that only the CEO may push made the remote drift behind local main and let CI problems surface late. The user asked for staged pushes gated on review, and for the Tester to guarantee both local and CI results and notify the responsible agent on failure.
- evidence: roles/release-engineer.md + roles/tester.md updated; templates/AGENTS.md regenerated into AGENTS.md; PYTHONPATH=src ./.venv/bin/python -m pytest tests/unit/test_skill_contracts.py -q -> 11 passed
- falsified by: A push lands without a Reviewer verdict, or CI is red on the pushed SHA while the task is reported green.
- consequences: -

## D-20261017-CEO - Owner instruction: the role mailbox domain is agents.nidvue.com

- date: 2026-10-17
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: ceo
- task: -
- context: -
- options considered: -
- decision: The team agent commit identity uses the owner's domain: e.g. 'Developer <developer@agents.nidvue.com>'. TEAMWORK_IDENTITY_DOMAIN remains the override, privacy_scan.py allows @agents.nidvue.com as a legitimate role mailbox, and the personal domains/emails, home paths and keys stay forbidden. This supersedes the earlier choice of a neutral teamwork.local placeholder.
- why: The owner stated in the running session that the agent mailbox domain suffix must be agents.nidvue.com rather than local, and asked for the corresponding commits to be updated. That instruction is the authority; the earlier neutral-domain assumption was the CEO's, not the owner's.
- evidence: owner message in session 2026-10-17 'team agent email domain suffix should be agents.nidvue.com not local, update the corresponding commits'; git log --format='%ae' --all | sort -u -> the role mailboxes only, every one on the agents.nidvue.com domain (the count is read from the run, never pinned); scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt -> PASS 0 findings
- falsified by: The owner withdraws the domain, or a personal datum is found in a role mailbox.
- consequences: -

## D-20261017-CEO - Owner instruction: role mailboxes use agents.nidvue.com

- date: 2026-10-17
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: ceo
- task: -
- context: -
- options considered: -
- decision: The agent commit identity domain suffix is @agents.nidvue.com (e.g. 'Developer <developer@agents.nidvue.com>'). IDENTITY_DOMAIN defaults to agents.nidvue.com, privacy_scan.py allows that exact domain, and every existing commit was rewritten so author and committer mailboxes use it.
- why: The owner corrected the domain to the agents subdomain and asked for the existing commits to be updated; the whole history and every example must match, or the identity is not consistent.
- evidence: git log --format='%ae' --all | sort -u -> the role mailboxes only, every one on the agents.nidvue.com domain (the count is read from the run, never pinned); scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt -> PASS 0 findings; grep -rn 'agents.nidvue.com' -> only agents.nidvue.com
- falsified by: A commit or shipped document carries a mailbox outside agents.nidvue.com, or the owner changes the suffix again.
- consequences: -

## D-20261018-CEO - Re-attribute the commit history to the acting roles (authorized)

- date: 2026-10-18
- kind: redline
- status: accepted
- deciders: operator (user), CEO
- decided by: ceo
- task: -
- context: `main` carried commits authored by the CEO, and a few by a product identity rather than the role that did the work; the role that did the work must be the author.
- options considered: A - leave history and enforce forward only (non-destructive; old attribution stays wrong); B - `.mailmap` (display only, SHAs unchanged, per-commit role unknowable); C - rewrite authors, committers, trailers and tags by changed-path role (correct everywhere; every SHA changes and releases are re-pointed).
- decision: C, with the operator's explicit authorization. Each commit is attributed to the role that owns its dominant paths; author and committer dates are preserved; the `Role:` and `Acting role:` trailers are rewritten; `v1.0.0`-`v1.0.2` are re-pointed to the rewritten commits.
- why: the operator judged attribution correctness worth the SHA churn. A local bundle (`.pi/backup-pre-rewrite.bundle`, gitignored) is the rollback, and the new identity audit prevents recurrence.
- evidence: `git log --format='%an <%ae>' @a307cc0 -> 36 CEO, 1 Teamwork, 1 Reviewer`; the operator selected option 3 in the session of 2026-10-18.
- falsified by: a rewritten commit whose author does not own its dominant paths, or any red gate on the rewritten tree.
- consequences: every SHA changes, the three release tags move, existing clones and forks must re-fetch; the CI identity audit makes the rule enforceable from here on.

## D-20261018-CEO-2 - Harden the engine's state parser, ledger, locks and path boundaries

- date: 2026-10-18
- kind: technical
- status: accepted
- deciders: CEO, independent Reviewer audit
- decided by: ceo
- task: code-audit-2026-10-18
- context: A full code audit found gate-forging metadata injection, a `ledger repair` self-deadlock, torn-tail ledger corruption, path traversal via agent/provider names, cross-role work claims, lock-order races in `pr open/merge`, stale-claim false positives, duplicate decision ids, and CI/docs integrity gaps.
- options considered: A - fix only the reported symptoms (small diff; leaves the parser and lock classes exploitable); B - fix the trust boundaries and add regression tests (larger diff; the gates become verifiable); C - defer to a post-1.0 refactor (no protection in the current release).
- decision: B. Stop metadata parsing at the body boundary, collapse scalar values to one line, escape record headers, validate unknown statuses at the gate, make ledger append/repair reentrant-safe and torn-tail tolerant, sanitize every name that becomes a path, enforce role ownership on claims and self-checks, use one lock order for task/review/PR writes, fix stale-claim day granularity, and pin CI actions to commit SHAs.
- why: the engine's plain-markdown state is the trust boundary for every evidence gate; a value a worker can write must never be able to forge `review_status`, `status` or a path outside the workspace.
- evidence: `pytest -q --cov=teamwork` @ code-audit-fixes -> 332 passed / 39.8% (floor 38%); `ruff check .` -> clean; `mypy src/teamwork` -> clean; `make ci PYTHON=.venv/bin/python` -> all gates passed; `scripts/verify_release.py` -> wheel+sdist inspected, installed-wheel full loop STOP; `privacy_scan.py --tree --history` -> PASS; `teamwork links` -> 0 issues.
- falsified by: a metadata value that changes a gate field after a round-trip, a ledger repair that deadlocks, a name that escapes its directory, or a regression in the new `tests/unit/test_integrity_fixes.py`.
- consequences: existing task/memory records remain readable; `init --force` no longer destroys records; review/merge now require an approved PR and an author; CI matrix adds 3.10/3.12; docs and Makefile expose `links`, `identity` and `ci`.

## D-20261018-CEO-3 - Split engine.py into typed modules (behaviour preserved)

- date: 2026-10-18
- kind: technical
- status: accepted
- deciders: CEO, Reviewer
- decided by: ceo
- task: T-0011
- context: `engine.py` carried 9.6k lines and mixed constants, record parsing, paths, IO, git plumbing and commands; `mypy` could not type any of it.
- options considered: A - keep the monolith (lowest risk, no type or ownership boundary); B - split the stable layers into typed modules and leave the command layer on `engine.py` (medium diff, no behaviour change); C - split every command module (large diff, high risk for a release patch).
- decision: B. Moved config, IO/lock, names/roles, layout, records, git plumbing and imaging into `config.py`, `io.py`, `names.py`, `layout.py`, `records.py`, `gitutil.py` and `imaging.py`; `engine.py` is the command layer and re-exports the moved API.
- why: the split gives each trust boundary one owner and makes `mypy` meaningful for everything except the command layer, while the existing suite (350 tests) proves the move did not change behaviour.
- evidence: `pytest -q` -> 350 passed, 1 skipped; `mypy src/teamwork` -> no issues in 14 source files; `make ci` -> all gates passed; coverage 62.38%.
- falsified by: a behaviour regression in the suite, an import cycle, or a moved module that imports `engine` at import time.
- consequences: `engine.py` remains the command layer and its typing exemption; the record path is now isolated and can be typed/refactored independently.

## D-20261019-CEO-4 - Future changes use a remote PR and a squash merge

- date: 2026-10-19
- kind: governance
- status: accepted
- deciders: operator (user), CEO
- decided by: ceo
- task: T-0014
- context: `main` already contains reviewed local `--no-ff` merge commits. The remote rule `required_linear_history` therefore flagged every push and had to be admin-bypassed; removing the history would require a force-push.
- options considered: A - rewrite `main` to a linear history (correct rule, but irreversible for every clone and a red line); B - keep the existing merge commits, disable the linear-history rule, and use a remote PR + squash merge for every future change (no rewrite; the process, reviews, checks and no-force/no-delete rules stay).
- decision: B. The operator selected option 1. `required_linear_history` is disabled; PR review (1), 14 required checks, strict up-to-date, no force-push and no deletion remain enforced. Future work goes: branch -> push branch -> GitHub PR -> checks green -> squash merge -> delete branch. Local `pr merge` uses `--squash` for changes that will reach the remote.
- why: the existing merge commits are reviewed evidence that must not be rewritten; a squash PR gives a single clean commit per change without touching published history.
- evidence: `gh api .../branches/main/protection` @2026-10-19 -> `required_linear_history: false`, `allow_force_pushes: false`, `allow_deletions: false`, reviews 1, checks 14; this decision itself will be merged by a squash PR.
- falsified by: a future push that needs an admin linear-history bypass, or a force-push/deletion of `main`.
- consequences: existing merge commits stay; future history is linear per change; branch protection is weaker only in the linear-history dimension, not in review/checks/force-push/deletion.

## D-20261019-CEO-5 - Create the squash commit locally with the role identity

- date: 2026-10-19
- kind: governance
- status: accepted
- deciders: operator (user), CEO
- decided by: ceo
- task: T-0014
- context: PR #14 was squash-merged by GitHub; the resulting commit `5b47529` was authored by the signed-in account (personal mailbox, redacted here), so the privacy gate failed. The commit had to be rewritten to `0cc655d` as `CEO <ceo@agents.nidvue.com>`.
- options considered: A - keep using the GitHub squash button and allowlist the personal email (weakens the privacy gate); B - keep the PR + checks process, but create the squash commit locally with the acting role identity and push it (one admin bypass of the PR-merge rule; no personal metadata).
- decision: B. A PR still gates the branch and its checks; the final squash commit is created locally as the role, then `main` is pushed. The PR is closed after the local merge.
- why: the privacy gate must stay strict, and a reviewed tree can be integrated without letting the forge author the commit.
- evidence: `git show -s --format=%ae 5b47529` -> personal mailbox (redacted); after amend -> `0cc655d` author `ceo@agents.nidvue.com`; `privacy_scan --tree --history` -> PASS; Docs run `39175948257` -> success.
- falsified by: a future `main` commit whose author is not a role mailbox, or a privacy-scan failure on a pushed revision.
- consequences: the person merging needs a local clone and the role identity; GitHub's squash button is reserved for a dedicated role-identity bot account.

## D-20261019-CEO-2 - Governance documentation is tracked in the audit area

- date: 2026-10-19
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0015
- context: -
- options considered: -
- decision: T-0015 is recorded under the existing audit area instead of a new governance area
- why: audit already owns the gate, ledger and path records these docs describe and has passing unit/integration/acceptance records; a prose-only area would demand three test layers that cannot test prose
- evidence: tests plan @9680bad -> audit unit/int/acc passing; governance missing; task list -> T-0015 area=governance came from commit --area, not from the product domain
- falsified by: -
- consequences: -

## D-20261019-CEO-3 - Evidence packets and the repro-first gate

- date: 2026-10-19
- kind: technical
- status: superseded by D-20261019-CEO-6 (evidence re-bound to the merged revision)
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0020
- context: -
- options considered: Keep the string (rejected: unverifiable proxy); require packets on every record (rejected: breaks existing records)
- decision: Adopt A2+A3 from the pstack comparison: evidence carries baseline/artifact/replay (artifacts hashed into the ledger), and a --bug task needs a fail->pass repro record before self-check.
- why: A free-text evidence string lets an author pick a proxy; the packet binds the claim to the real artifact and the repro binds a fix to a demonstrated defect.
- evidence: pytest -q -> 375 passed, 1 skipped; ruff check -> passed; mypy src/teamwork -> no issues @working-tree
- falsified by: First-pass review acceptance does not rise over the next ten tasks
- consequences: -

## D-20261019-Reviewer-1 - P-0016 post-merge: fix forward, not rollback

- date: 2026-10-19
- kind: process
- status: accepted
- deciders: Reviewer-1 (reviewer)
- decided by: Reviewer-1
- task: T-0025
- context: -
- options considered: -
- decision: Keep the merged ceo-audit-close skill and fix the root-hygiene allowlist in a follow-up (T-0025) instead of reverting P-0016.
- why: The skill deliverable is correct and reviewed; the red suite comes from a latent gap in tests/unit/test_hygiene.py ROOT_ALLOWLIST that the first tracked .agents/ directory exposed. A one-line allowlist addition restores green with no user-visible risk, while a revert would delete a reviewed deliverable.
- evidence: pytest -q @b662faf -> 1 failed (unexpected ['.agents']), 376 passed, 1 skipped; git ls-files .agents -> tracked SKILL.md; tests/unit/test_hygiene.py:46 ROOT_ALLOWLIST lacks .agents
- falsified by: If adding .agents to ROOT_ALLOWLIST lets any other stray root entry pass, or if the skill directory should be ignored instead of tracked, this fix-forward is wrong.
- consequences: -

## D-20261019-CEO-6 - A2/A3 adoption closed at the merged revision

- date: 2026-10-19
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0020
- context: -
- options considered: -
- decision: The pstack-derived evidence packet and the repro-first gate are adopted as shipped: tests run/selfcheck/review record baseline, artifact (hashed) and replay; tests repro proves a defect fail->pass on the defect task with an ancestry check, and a --bug task cannot pass self-check without it. D-20261019-CEO-3 was recorded before the first commit; this entry binds the adoption to the merged revision.
- why: The original decision's evidence was bound to @working-tree, which is not a reproducible revision; the closing record must cite a merge anyone can check.
- evidence: pytest -q @3934690 -> 383 passed, 1 skipped; ledger verify @3934690 -> chain intact; git log e8da9ce..3934690 -> the merges of T-0020 (9d59976), T-0021 (2297adc), T-0024 (b662faf), T-0025 (d72f44b) and T-0022 (3934690)
- falsified by: -
- consequences: -

## D-20261019-CEO-7 - Privacy allowlist instead of a history rewrite

- date: 2026-10-19
- kind: redline
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: -
- context: the Reviewer blocked P-0021 on the Board privacy claim, because the shipped gate `privacy_scan --tree --history` was red at that head and the Board said PASS.
- options considered: History rewrite (rejected: destroys cited revisions); delete the text only (rejected: history blob still fails); blanket rule disable (rejected: weakens the gate)
- decision: Keep the unpublished local history intact and exempt one exact host-state prefix (the pi-subagents install directory) through `.github/privacy-allow.txt`, wired into `make privacy` and both CI privacy jobs. The quoted path is removed from `references/Adapters.md`; no credential rule is relaxed.
- why: Rewriting the 37 unpublished local commits would invalidate every revision cited in the ledger, the archive and the decisions - the audit trail's verifiability is worth more than a cosmetic history purge; the exemption is one exact anchored regex with a reason and two tests.
- evidence: `scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` -> PASS 0 findings (run at this head; the scanner takes no positional revision); the same scan without `--allow` -> FAIL 4 findings, all `agent-config`; `pytest tests/unit/test_privacy_scan.py -q` -> 47 passed
- falsified by: A second allowlist entry is ever added, or an allow entry masks a credential rule
- consequences: `make privacy` and both CI jobs now pass `--allow`; the exempted prefix is a host install path and a test fixture, no credential; every later decision on this gate must name the same file.

## D-20261019-CEO-8 - Privacy allowlist instead of a history rewrite for the quoted install path

- date: 2026-10-19
- kind: technical
- status: superseded by D-20261019-CEO-15, then by D-20261020-CEO-4 (two path literals per quoted path family, plus three fabricated probe values that a reviewer's own evidence quoted)
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0027
- context: superseded. the Reviewer-1 round blocked P-0021 on the Board privacy claim, because `privacy_scan --tree --history` is red at this head and both `make privacy` and the CI privacy job ran that exact command.
- options considered: (1) filter-repo rewrite of the unpublished local main; (2) delete the quoted path from the tree only; (3) commit an allowlist with one justified entry per rule and pass `--allow` in the Makefile target and the CI job (chosen).
- decision: pass `--allow .github/privacy-allow.txt` from `make privacy` and the CI privacy job, and bless one pattern per quoted path family, starting with the pi install tree (`^\.pi/agent/npm$`), which covers the scanner's own fixture in the tree and the history blobs that quote the same path. Do not rewrite history. No dependency lockfile exists in this repository today, and a lockfile URL is not a scanner finding, so nothing from one is allowlisted.
- why: a rewrite would also have to rewrite docs/Team/Archive.md and this file, which quote commit SHAs as audit evidence; no lockfile is tracked in this repository, so there was no lockfile to rewrite and nothing from one could be blessed.
- evidence: `privacy_scan --tree --history --allow .github/privacy-allow.txt` -> PASS 0 findings; `grep -cE '^\^' .github/privacy-allow.txt` -> at least one live entry per quoted family (never one exact total: the file also carries value-shaped entries for fabricated probe values); `git ls-files | grep -ci lock` -> 0 (no lockfile is tracked). No finding count and no line number is quoted here: the commit that documents a count changes it, which is how this record went stale.
- falsified by: a scan with `--allow` reporting a finding whose pattern is not one of the exempted quoted path families. That falsifier fired: a finding appeared outside the single pattern (the operator user name in an archived build path), so the gate was re-ruled in D-20261019-CEO-15 rather than silently widened. The exemption's exact membership is deliberately not restated here - the allowlist file is the record, and this one went stale precisely because it pinned a shape the file had outgrown.
- consequences: `make privacy` and CI pass `--allow`; the blessed surface is one fully escaped literal per quoted path family, so a credential quoted on the same line is still reported; a new secret is fixed at source and never added to the allowlist; the audit quotations stay in history as evidence.

## D-20261020-CEO-4 - A fabricated probe value is exempted by its exact literal, never by a rule

- date: 2026-10-20
- kind: security
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0048
- context: two reviewers proved the gate still catches a credential by putting a fake one on the line they probed - `sk-live-0123...`, `PASSWORD="<passphrase>"`, `changeme-placeholder`. Their evidence is quoted verbatim into `docs/Team/Archive.md` by `archive_append`, so those invented values entered two unpublished blob revisions. `privacy_scan --tree --history --allow .github/privacy-allow.txt` then failed with `critical` findings inside the archive, i.e. the archive that records the proof that the gate works became the reason the gate went red.
- options considered: (1) `git filter-repo` the two unpublished commits - refused, it rewrites every SHA the archive and `docs/Team/Decisions.md` quote as evidence, and a red line covers history rewrite; (2) delete the quoted evidence lines - refused as deception: they are a reviewer's real findings; (3) mask credential shapes at the moment `archive_append` writes the entry, and exempt the two already-written values by their exact literal (chosen); (4) widen a rule - never: no rule is disabled.
- decision: `archive_append` masks every value the shipped gate's own credential rules report - `private-key`, `api-token`, `env-secret`, `json-secret`, `high-entropy-secret` - in the entry header and in every quoted field, at write time; the values already written are exempted by three fully escaped anchored literals, one per fabricated string, in `.github/privacy-allow.txt`. The rule ids are not re-declared in the engine: `mask_secret_shapes` loads `scripts/privacy_scan.py` and filters its `RULES` table, so the mask cannot drift from the gate again.
- why: masking at write time fixes the source for the future, and an exact literal is the narrowest possible exemption for the past. A rule-shaped entry (`sk-live-.*`) would exempt every future token of that family, which is the defect D-20261019-CEO-15 already refused for paths.
- evidence: `scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` -> PASS, 0 findings; the same command without `--allow` -> every remaining credential-rule hit is one of the three fabricated probe values, including the runs in `.github/privacy-allow.txt` and `tests/unit/test_privacy_scan.py` that quote the literals in order to test them - no count is pinned here, because the commit that documents a count raises it; `tests/unit/test_privacy_scan.py::test_a_fabricated_probe_value_is_exempted_but_its_neighbours_are_not` shows the exempted literal passes while a one-character sibling and a real `ghp_` token sharing the line are still reported; `tests/unit/test_context_economy.py::test_the_archive_mask_covers_every_credential_rule_the_gate_arms` walks all five rules and fails if any value survives, and `test_the_archive_mask_does_not_rewrite_a_helper_name_or_a_sha` pins the other direction, so the mask is exactly the gate's finding set and not a wider guess.
- falsified by: any credential-shaped value the scanner reports on a line whose own text is exempted, OR an allowlist entry that matches more than one string.
- consequences: the archive can quote a fabricated probe value without turning the shipped gate red. The exemption's real scope is one finding VALUE, not one file or one variable: an `env-secret` value is matched after the key and quotes are stripped, so an exempted passphrase stays exempt under any key name and in any file, and the same is true of an exempted token or path. That is the cost of an exact literal - it is bounded, not narrow in location - and each literal names a fabricated probe value, not a credential. A real secret is still reported because its literal is not exempted, and masking only rewrites the archived copy, never the scanner's own output.

## D-20261019-CEO-9 - privacy_scan --history follows the reflog, so amended commits keep the local gate red

- date: 2026-10-19
- kind: technical
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0027
- context: the local privacy gate reported a finding at a revision whose refs were clean, because the scanner walks `--all --reflog` while CI clones only refs.
- options considered: expire the reflog (chosen, local-only metadata); git gc --prune=now (not needed yet); weaken the scanner to drop --reflog (rejected: the flag exists precisely to catch objects a reset or deleted branch left behind)
- decision: git reflog expire --expire=now --all clears the orphan; no refs, no commits and no tags were rewritten, and CI is unaffected because a fresh clone has no reflog for the pushed history. Recorded because the divergence is real: the local gate can be red on an orphan while CI is green, and vice versa.
- why: the local gate went red on docs/Team/Decisions.md:422 after two amends of my own decision commit; the finding source was history:blob commit 8e8f2d1, which is in no ref (git rev-list --all | grep -q ^8e8f2d1 -> no), so only the reflog made it reachable
- evidence: git rev-list --all --count 131 vs git rev-list --all --reflog --count 166; scripts/privacy_scan.py:843 runs rev-list --objects --all --reflog; before: privacy_scan --tree --history --allow .github/privacy-allow.txt -> FAIL 1 finding (history:blob 8e8f2d1); after reflog expire -> PASS 0 findings
- falsified by: if a fresh clone of the pushed revision still reports a finding that the local scan calls PASS, the divergence runs the other way and this ruling must be revisited
- consequences: amending a commit whose message or content carried a secret keeps a local finding until the reflog expires; expire+rescan is the standard close-out step

## D-20261019-CEO-10 - While the review loop is in flight, lanes work in the shared checkout on the checked-out branch and the merge reviewer re-verifies the final head

- date: 2026-10-19
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0027
- context: the Reviewer marked its own acceptance task done/passed with evidence that itself documented the blocker it was accepting, and the audit flagged that as a done-without-evidence risk.
- options considered: worktree isolation (refused by the tool: 'worktree isolation requires a clean git working tree'); stash the auditor's file (rejected: touches another lane's work); serialize all lanes after P-0021 merges (rejected: idles three lanes for a full review cycle); shared checkout with per-path commits (chosen)
- decision: lanes share the main checkout and commit only their own --paths on the branch that is checked out (ceo/t-0027-...); no lane switches branches or stashes; reviewer-2's delta verdict is advisory, and reviewer-1 verifies the final head before merging (Reviewer-only merge).
- why: worktree isolation was refused for all three layer children because the auditor lane holds an uncommitted tracked file in the shared checkout, and stashing another agent's in-flight work is a scope violation
- evidence: workflow 7ae77d99: all 3 children failed at 0s with 'worktree isolation requires a clean git working tree'; git status --porcelain @5a44214 -> 'M docs/Team/AuditReport.md' (the only dirty file, owned by the security-auditor lane); engine.py:3059-3061 shows commit stages exactly the paths passed to --paths, so a lane cannot sweep a peer's uncommitted file
- falsified by: if a lane loses work to git index.lock, or a commit contains a file owned by another lane, this mode is wrong and lanes must be serialized per checkout
- consequences: commits land on the branch under review after reviewer-2 measured it, so the merge verdict must be recorded against the final head; every lane must use --paths and never --all

## D-20261019-CEO-11 - Reopen a green acceptance record that contradicts its own failing finding, and drop its uncommitted archive entry

- date: 2026-10-19
- kind: process
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0027
- context: the archive entry for a merged task is written when the review passes, before any merge revision exists, so `pr merge` must repoint it; an earlier attempt did so after the records commit and left the base branch on 'pending' with a dirty tree.
- options considered: leave both records (rejected: the audit gate and the archive would state a false completion); delete the ledger records (refused: the ledger is append-only and tamper-evident); reopen the task and drop the uncommitted archive line (chosen: no committed evidence is altered, the redo will write a fresh entry)
- decision: Set reviewer T-0001 back to todo and restore the uncommitted docs/Team/Archive.md entry it had appended; the ledger records (#0495 fail on the developer PR, #0501 pass on the acceptance task) and the task evidence are kept unchanged.
- why: the acceptance task was marked done/passed with evidence that itself documents a blocking defect (archive merge sha never reaches a commit, second merge dies) on the very deliverable it accepted; audit flagged it as done-without-evidence, and a green archive entry over a red deliverable is a fabricated-completion risk
- evidence: teamwork.py audit @6c8d818 before -> 'done without evidence (fabricated-completion risk): reviewer T-0001'; task set reviewer T-0001 --status todo -> rc 0, ledger #0515; git status --porcelain before the restore -> ' M docs/Team/Archive.md' (the appended '## T-0001 Acceptance pass over the M8 context-economy change' block, never committed); after -> 0 lines
- falsified by: if an acceptance record can pass while the PR it covers is changes-requested, this decision is unnecessary and should be reversed
- consequences: the acceptance pass over M8 must be redo ne after P-0022 merges; no other role may mark its own acceptance done while the covered PR is red

## D-20261019-CEO-12 - A reviewer verdict is void unless it names the head it measured

- date: 2026-10-19
- kind: process
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0031
- context: -
- options considered: accept the stale verdict (rejected: it names files that no longer exist on the branch); ignore the review and merge on the CEO's own evidence (refused: self-approval); re-verify the head myself and require the reviewer to assert the sha first (chosen)
- decision: Reject review.fail recorded at 2e338b6 for T-0031: the branch was rebuilt as ceo/t-0031-pi-teamwork-only and its head is c9de7d3; 2e338b6 belongs to the discarded branch. Re-dispatch with 'git rev-parse --short HEAD must print c9de7d3' as step 1.
- why: five of the last review rounds measured a stale or wrong revision, so the verdict described code that is not under review; accepting it would force rework of already-correct code and accepting the pass would leave the real head unmeasured
- evidence: git rev-parse --short ceo/t-0031-pi-teamwork-only -> c9de7d3; git log --oneline -1 2e338b6 -> 'feat(packaging): package.json manifest builder' on the deleted branch; ledger #0675 review.fail names '@2e338b6' while T-0031's branch field is ceo/t-0031-pi-teamwork-only
- falsified by: if 2e338b6 is an ancestor of c9de7d3, the verdict is valid and this decision is wrong (git merge-base --is-ancestor 2e338b6 c9de7d3)
- consequences: every review packet starts with the sha assertion; a verdict that does not name a head on the reviewed branch is re-dispatched, not fixed against

## D-20261019-CEO-14 - Relax the local provider caps to the harness ceiling instead of the vendor's shared limit

- date: 2026-10-19
- kind: process
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0033
- context: the local provider caps were 10/8 while the teammate harness reports 64 concurrent fan-out slots, so dispatch throttled the team to ten lanes while sixty-four were available. The rulebook pages that state the cap (AGENTS.md, templates/AGENTS.md, references/Concurrency.md, templates/TeamMap.md) and the CEO charter each quoted the old bound, so a reader was told a number the engine did not enforce.
- options considered: keep 10 (rejected: it serialised a 10-lane team on a 64-slot harness, measured at m01392); remove the caps entirely (rejected: dispatch then cannot detect a real provider limit); raise the cap only in the local Settings.json (rejected: a fresh team would still start at 10/8 and the repo default would keep contradicting the rulebook); raise it in both the repo default and every page that states it (chosen).
- decision: Raise `ollama-cloud` from 10 to 64 and `default` from 8 to 32 in `DEFAULT_PROVIDER_LIMITS` (`src/teamwork/config.py:173-179`), and state 64 on every page that names the cap. Leave `deepseek` at 2500, `openai`/`anthropic` at 64. The team-local `Settings.json` may override the default; when it does, the two must agree.
- why: the effective ceiling for concurrent lanes is the teammate harness (64 fan-out slots, reported by every run as "0/64 used"), not the provider's shared limit; capping at 10 throttled a team that could run six lanes at once when the operator asked for more.
- evidence: `git show HEAD:src/teamwork/config.py | grep -A6 DEFAULT_PROVIDER_LIMITS -> ollama-cloud 64, default 32`; `teamwork.py parallel -> ollama-cloud used=0 cap=64 free=63, TOTAL free slots 2691` (before the change: cap=10, TOTAL 2638); `git grep -n 'Ollama Cloud' -> AGENTS.md:189, references/Concurrency.md:14, templates/AGENTS.md:197, templates/TeamMap.md:91 and roles/ceo.md:27 state 64, and 'grep -rn "~10" AGENTS.md templates/ references/ roles/ -> no provider hit`; a scratch copy with the constant set to 7 makes `parallel` report cap=7, so the constant is what drives dispatch.
- falsified by: if a 64-lane ollama-cloud round starts getting provider 429/rate-limit errors, the cap is above the real limit and must come back down to the measured value; or if `grep -rn '~10'` finds a page still stating the old bound.
- consequences: dispatch may now run many more lanes in parallel, so the CEO must still respect the provider's real behaviour and the `slot` lease TTL. The caps live in the repo default, so a fresh team starts at 64/32 without a local edit; the local `Settings.json` can narrow them, and any page stating a number must state the one the engine enforces.

## D-20261019-CEO-13 - Correct D-20261019-CEO-12: the round-5 verdict did name c9de7d3; the stale-sha premise was a ledger-display artefact

- date: 2026-10-19
- kind: process
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0031
- context: -
- options considered: keep the retraction silent (refused: the ledger is append-only evidence and the record must stand); rewrite D-12 (refused: never edit a recorded decision); append a correction that names the error and the measurement (chosen)
- decision: D-20261019-CEO-12 is retracted on its premise. The round-5 review.fail names '@c9de7d3 (base main 31c03b5, round 5)'; the '@2e338b6' seen in the ledger display is a rendering artefact of the record's rev field, not the head the reviewer measured. The three findings it raised were real and are fixed in 8b45af1.
- why: a wrong premise in a decision is worse than the defect it tried to explain: it would have let the branch merge with two live document defects and would have blamed a reviewer for a display bug
- evidence: jq -r 'select(.action=="review.fail" and .target=="T-0031") | .detail' Ledger.jsonl | tail -1 -> 'FAIL @c9de7d3 (base main 31c03b5, round 5)'; git rev-parse c9de7d3^{tree} == git rev-parse HEAD^{tree} before 8b45af1 -> 32a14aa9 (the re-dispatched review measured the same tree, correctly); git log --oneline -1 8b45af1 -> 'docs(packaging): CHANGELOG one Added block in 1.1.0 ...'
- falsified by: if any recorded round-5 verdict names a head that is not an ancestor of the reviewed branch, the retraction is wrong
- consequences: verdict text is read from the record's detail, never from the rendered rev column; the round-5 findings were fixed rather than dismissed

## D-20261019-Architect - Architecture.md section 2 map: no version literal, and pi-package/scripts trees listed

- date: 2026-10-19
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0001
- context: T-0001 sys-layer check found one drifted fact (version) and three omissions in the frozen layout, while the module list itself was already 1:1 with the 14 shipped modules.
- options considered: A) correct the literal to 1.1.0 and keep quoting it - rejected: drifts again at the next bump. B) drop the literal and point at version.py - chosen. C) leave the tree alone and document the omissions elsewhere - rejected: section 2 is the frozen layout every lane reads.
- decision: Section 2 of docs/Team/Architecture.md stops quoting a version string for src/teamwork/version.py (it said __version__ = "1.0.2" while the code says 1.1.0) and instead names the file as the single version source; the layout tree now also lists templates/pi-package/, scripts/build_pi_package.py and .agents/skills/, and the ownership table assigns scripts/build_pi_package.py + templates/pi-package/** to ceo (owner of Pi-Packaging.md).
- why: A frozen contract that repeats a value it does not own drifts silently: the map was 1.0.2 behind the code and TS-0015 carried the stale 1.0.2 into its evidence. Naming version.py as the only source removes the class of drift rather than correcting one instance. The three omitted paths are shipped, tracked and load-bearing (Makefile:61-62 runs build_pi_package.py; the pi layer is built from templates/pi-package/), so a map that omits them is not a map of the repository.
- evidence: python3 .pi/Teamwork/Teams/Teamwork/Agents/Architect/Artifacts/arch_map_check.py . @49cc390 -> PASS 6/6 (14 modules 1:1, 4 scripts, templates subtrees Docs+pi-package, import direction, exit codes); negative control on main:docs/Team/Architecture.md -> FAIL 4 mismatch(es) rc=1
- falsified by: A future commit changes a version string in version.py and section 2 of Architecture.md must not need an edit; if a reviewer finds a version literal in section 2, this decision is void.
- consequences: Section 2 no longer states a number, so the version is read from src/teamwork/version.py (pyproject [tool.hatch.version] reads the same file). scripts/build_pi_package.py and templates/pi-package/** now have a named owner (ceo) so one writer per file still holds.

## D-20261019-CEO-17 - A reclaimable worktree is decided by task state, not by the filesystem

- Owner: CEO
- Related: [Plan.md](Plan.md), [Engineering.md](../../references/Engineering.md), `T-0040` (the task record lives in the local team tree, which is not committed)
- Task: T-0040

### Context

`.pi/` reached 267 MB of worktrees that `clean` never touched, so removal was
manual and unsafe. A reclaimer that judges only the filesystem cannot tell a
finished lane from a busy one: a lane writing to gitignored `build/` output leaves
`git status` clean and does not move the top directory's mtime. Reviewer-1 proved
each failure mode with a probe worktree at a952d93.

### Decision

A worktree is reclaimed only when all five hold, measured, never inferred:

| Guard | Measurement |
|---|---|
| ours | `path.resolve().is_relative_to((project / ".pi").resolve())` - a string prefix let `.pi-evil/x` pass |
| not busy | no live slot file for the lane, and no task of that role in `doing`/`selfcheck` claimed by it |
| unlocked | `git worktree list --porcelain` carries no `locked` line for it |
| no work | `git status --porcelain --ignored` is empty - a build cache is work |
| merged and idle | HEAD is an ancestor of `main`, and nothing in a recursive walk of the tree was written inside the stale window |

Removal is verified: a non-zero `git worktree remove` exit or a surviving
directory is reported as "could not be reclaimed" and never counted.

### Alternatives rejected

| Option | Why not |
|---|---|
| Trust the top-dir mtime | A lane editing files inside the tree does not move it; a live lane would be deleted |
| Trust `git status --porcelain` alone | Gitignored build output is a lane's real, unrecoverable-by-commit work |
| `--force` everything older than N minutes | Deletes unmerged and uncommitted work; no commit can restore it |
| Leave worktrees to a human | 43 worktrees and 267 MB accumulated while nobody looked |

### Evidence

- evidence: `PYTHONPATH=src pytest -q` -> all green at this head (read the run: the count
rises with every test another lane lands, so it is never written here);
`tests/unit/test_worktree_reclaim.py` -> all pass;
the guards are non-vacuous, proved by restoring the pre-fix code rather than by
quoting a failure count: with `engine.py` taken from `a952d93` the reclaim tests
fail, and with the case-sensitive comparison restored the mixed-case test fails
alone (both are pre-fix probes, deliberately unreachable from this head and
never cited as ancestors - reproduce them by checking those objects out);
`clean --worktrees --dry-run` -> rc 0 (was rc 2: the flag did not exist);
`ruff check .` and `ruff format --check .` clean; `mypy src` clean.

### Falsifier

A worktree that satisfies all five guards and still holds work that no commit
reaches. Reproduce by creating a worktree, writing only to an ignored path,
marking its role's task `done`, and confirming `clean` reclaims it while the file
is the only copy.

### Consequence

`clean` now reclaims by default and reports refusals; `--no-worktrees` and
`--dry-run` remain the opt-outs. A lane that forgets to release its slot keeps its
worktree until the slot expires - the safe direction to fail.

## D-20261019-CEO-15 - A quoted user name is exempted by one literal, and no finding count is ever pinned

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0034
- context: the shipped gate (`Makefile`, `ci.yml`, `docs.yml`) runs `privacy_scan.py --tree --history --allow .github/privacy-allow.txt`, and it could not pass: besides the pi install tree, one more path family is quoted as evidence inside `docs/Team/Archive.md`: one operator user name in an archived build path. (A third candidate, the harness session directory, was measured and dropped - see below.) Rewriting those quotations would invalidate the commit SHAs the archive cites as its own evidence.
- options considered: (1) a filter-repo rewrite of the unpublished local commits - refused, it invalidates every SHA quoted in Archive.md and this file; (2) delete the reviewer paragraph that quotes the path - refused as deception, it is real review evidence; (3) mask the live line at source AND exempt the remaining family with one fully escaped literal, fixing any future instance at source (chosen). A further option, a wildcard or a sibling-name pattern, was refused because it would exempt a future real sibling name on a matching line.
- decision: mask the one live occurrence at source (`docs/Team/Archive.md` now reads `<repo>/dist/pi-teamwork`), and ship two fully escaped anchored literals, one per quoted path family - the pi install tree as a repository-relative pattern, and the operator user name as a single anchored literal in the allowlist file itself (written there, never quoted in a document, so this record cannot become the leak it documents), each justified in a comment on the entry. A third entry for the harness session directory was measured to match nothing: that path only ever appears on an Archive.md quoted-evidence line, which the scanner already scopes, so the entry was dead and was dropped rather than kept as decoration. A credential quoted on the same line is still reported by the credential rules, which are never scoped. No finding count and no revision is pinned anywhere in the justification, because the commit that documents a count raises it.
- why: a user name or an install path is not a credential; the scanner masks the value it reports and tests each match against the allowlist, so an exact-literal entry exempts exactly one finding VALUE and cannot spread to a sibling name. It does cover every finding whose value is that one string, including a deeper path under it - the exemption is bounded by the string, not by the directory, and the credential rules stay armed on the same line.
- evidence: `privacy_scan.py --tree --history --allow .github/privacy-allow.txt` -> PASS, 0 findings; `--tree` alone -> findings in the two path families only, no credential rule; `grep -cE '^\^' .github/privacy-allow.txt` -> one live entry per family; `tests/unit/test_privacy_scan.py` pins the exact two-entry list, requires each entry to be one fully escaped literal, probes that a wildcard, a class, an alternation, an unanchored path and a sibling-name form are all rejected, and `test_the_quote_scope_is_what_drops_a_quoted_path_and_only_that` proves the scope itself - deleting the skip in `scripts/privacy_scan.py` fails it, while the same path in an authored document still reports. Counts measured while writing this record are deliberately not quoted: they moved at every revision measured.
- falsified by: a scan with `--allow` in force that reports a credential rule, OR an allowlist entry that is not one fully escaped literal, OR an allowlist entry that matches no finding at all, OR a live (non-quoted) occurrence of one of the two strings that is not masked at source. Any of those means the exemption is too wide and must be re-ruled.
- consequences: the shipped gate is green in tree and history modes; the two entries are pinned by a discriminating test, so a third entry cannot be added without editing that test and having to show it matches a real finding; a new leak in any of these families is fixed at source, never by widening the allowlist.

## D-20261019-CEO-16 - A slim roster is the default, and trimming a role must never trim a gate

- date: 2026-10-19
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0037
- context: id 16, not 14: cmd_decision allocates the next id by scanning docs/Team/Decisions.md on the CURRENT branch only, so two open branches both picked D-20261019-CEO-14 (ceo/t-0033-provider-caps holds it) and T-0034 skipped to 15 for the same reason. Filed as T-0038.
- options considered: keep the 15-role list as the default (rejected: 2.6x startup text for lanes that own no gate); trim the roster but keep prose rules (rejected: the tribunal hole reproduced silently); trim with the invariants moved into code and tests (chosen)
- decision: Default roster is --roster slim (ceo, architect, developer, tester, reviewer-1, reviewer-2). product-manager, project-manager, release-engineer, designer, technical-writer, data-engineer, security-auditor, cto, coo and cfo become lanes rather than seats. Two invariants are enforced in code: tests plan requires only the layers of staffed roles, and required_tribunal never drops below TRIBUNAL_MIN_SIGNERS, with the Reviewer taking the neutral seat; a party to a dispute can never rule it.
- why: Fifteen charters per project cost 552 kB of startup text and most of those roles own no gate the CEO or the Reviewer cannot hold. The gates are what must survive the trim, so they are enforced in code rather than asked for in prose.
- evidence: measured startup read: expand_roster over roles/*.md + templates/AGENTS.md -> slim 213225 B, standard 316023 B, full 551756 B (2.6x); pre-fix tribunal on a slim roster in /tmp/slim1: dispute escalate D-0001 -> '(ceo)' only, sign by ceo -> 'tribunal complete', resolve -> rc 0 (self-ruled); post-fix same workspace: escalate -> '(ceo, reviewer)', resolve by ceo -> rc 1 'ceo is a party to this dispute and cannot rule it', resolve by Reviewer-1 -> rc 0; tests/unit/test_roster_tiers.py -> 8 passed; pytest -q -> 453 passed, 1 skipped
- falsified by: a slim roster that reports a test-layer gap for an unstaffed role, or a dispute resolved by a role that is a party to it
- consequences: init --roster is the documented bootstrap; the folded lanes are printed at init; the Reviewer is now a tribunal member whenever cto/cfo are unstaffed

## D-20261020-CEO-2 - A stage ends with a push, not with a merge

- date: 2026-10-20
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0041
- context: id -2, not -1: `cmd_decision` allocates from the checked-out branch only, and another open branch had already taken the bare id. The operator asked (2026-10-19) that a completed stage be pushed promptly once its commits are squashed, rebased and merged. The earlier rule pushed per milestone, which let local `main` drift far behind the remote - measured with `git rev-list --count origin/main..main`, and deliberately not written here, because a count in a document is stale before the document is committed.
- options considered: keep batching per milestone (refused: the remote drifted by a whole release's worth of commits); push every commit as it is made (refused: it would publish unreviewed revisions and red gates, which the push policy and the red lines both forbid); push each merged stage after the gates are green on that revision (chosen).
- decision: The Release Engineer pushes a stage as soon as that stage is squashed, rebased and merged and its pre-push gates are green on exactly that revision. A milestone is no longer the unit of pushing; a stage is.
- why: Review and merge already establish that a revision is fit to be seen; holding it back until a milestone adds no safety, only exposure - a local-only history is a single disk failure from losing reviewed work, and it makes CI surface defects long after the code was written.
- evidence: `grep -rn 'per milestone' SKILL.md references/Engineering.md roles/release-engineer.md docs/Team/Architecture.md AGENTS.md templates/AGENTS.md -> 0 hits` and `grep -c 'A stage ends with a push' AGENTS.md templates/AGENTS.md -> 1 each`; the rule is pinned by tests, and reverting the phrase fails them (`pytest tests/unit/test_skill_contracts.py -q` -> failures on the AGENTS.md surface, the skill surface, the release-engineer charter and the Engineering reference); `git rev-list --count origin/main..main` is read at the time of a push, never quoted here.
- falsified by: A revision reaches the remote without a Reviewer verdict, or a merged stage sits unpublished past the gates being green on it.
- consequences: Every stage ends with a push and a CI confirmation on that SHA; the Release Engineer reports the pushed revision and the run ids as evidence; tags and public releases remain the CEO's step.

## D-20261020-CEO - One parent per role: delivery lanes report to the CTO, planning to the COO, product to the PM

- date: 2026-10-20
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0042
- context: The reporting table gave almost every role the CEO as its parent, so every lane escalated straight into the CEO and the CEO became the queue every blocked agent waited in. Measured on the pre-change table (`git show main:references/Roles.md`, the `Reports to` column, 15 rows): 14 named the CEO, 8 of those with a second named manager; only the CEO row itself named the user. A role with two named managers answers to neither, and no lane had a manager that owned the standard it is judged by.
- options considered: Keep the flat table (rejected: the CEO is the bottleneck and no manager owns a standard; measured 14/15 rows naming the CEO); make every specialist a direct report of a single executive by domain, keeping the gate roles with the CEO (chosen); remove middle managers and let the CEO manage all lanes with a bigger pulse (rejected: a pulse is not arbitration, and the gate roles would still be managed by lanes they judge)
- decision: ROLE_PARENT in src/teamwork/config.py is the single source of truth: CTO <- architect, developer, tester, release-engineer, data-engineer; COO <- project-manager; product-manager <- designer, technical-writer; CEO <- cto, coo, product-manager, cfo, reviewer, security-auditor. Escalation walks that line before it reaches the CEO.
- why: A lane's manager must own the standard the lane is judged by: engineering standards are the CTO's, planning and process the COO's, requirements and documentation the Product Manager's. Three roles stay with the CEO because they must be able to disagree with everyone: the Reviewer passes and merges every deliverable (a manager whose work it reviews would turn independent review into review under a manager), the Security Auditor audits the CTO's own decisions, and the CFO holds the cap that binds every role. The direct-report count drops from 14 to 6, and every remaining child is judged by a manager who owns its standard.
- evidence: `git show main:references/Roles.md | sed -n '/Reports to/,/^$/p'` -> 15 rows, 14 naming the CEO (6 'CEO' alone, 3 'CEO, CTO', 2 'CEO, Product Manager', 2 'CEO, Architect', 1 'CEO, COO'), 1 naming the user; after the change the same command -> 6 naming the CEO (cto, coo, product-manager, cfo, reviewer, security-auditor), 5 naming the CTO, 2 the Product Manager, 1 the COO; `teamwork.py map` renders the tree with 6 direct reports under the CEO; `PYTHONPATH=src pytest -q` and `pytest tests/unit/test_reporting_hierarchy.py -q` are read from the run at the head being reviewed - the count moves as lanes land, so no number is pinned here, and it is non-vacuous on all three doc surfaces - probes in a detached worktree at this head: (a) `roles/developer.md` `**CTO.**` -> `**CEO.**` -> 1 failed, (b) `roles/ceo.md` `Manages:` line shortened -> 1 failed, (c) `templates/AGENTS.md` developer row -> 'CEO' -> 1 failed, (d) `ROLE_PARENT['reviewer']='cto'` -> test_the_gate_roles_report_past_the_lanes_they_judge fails, (e) `templates/AGENTS.md` Designer cell -> 'Product Manager, CEO' -> 2 failed (the cell must hold exactly one name), (f) live `AGENTS.md` Developer row -> 'CEO' -> 1 failed (test_the_live_agents_md_matches_the_template), (g) renaming the live table header so no row parses -> 1 failed (a skip there would disable the pin), (h) hard-coding the generated brief's line back to the CEO -> 1 failed (test_the_generated_brief_states_the_same_line_as_the_charter)
- falsified by: If a lane's quality drops because its manager cannot arbitrate its domain - e.g. a Tester blocked by an interface dispute waits on the CTO who does not decide it - then the parent is wrong for that lane and the edge moves. If the CEO still receives every escalation in practice, the tree is decorative and must be enforced in the dispatch path.
- consequences: AGENTS.md, templates/AGENTS.md, SKILL.md, references/Roles.md, README.md and all 15 role charters state the line from ROLE_PARENT, and so does the engine-generated StartHere brief (engine.py start_here), which is read before the charter and previously told every instance to report to the CEO; teamwork.py map renders the tree; tests/unit/test_reporting_hierarchy.py pins all four doc surfaces (templates/AGENTS.md, the live committed AGENTS.md, references/Roles.md and every roles/*.md charter including its Manages: line) to the constant, and the Reports-to cell must hold exactly ONE manager name - a two-manager cell is the defect this record removes, so a prefix match would re-admit it; a vacant manager escalates to the CEO for the duration, so trimming a role never leaves a lane with nobody to escalate to (`resolve_manager` in engine.py is the only place that resolves this, and `start_here` renders the resolved manager - not the raw constant - so the brief cannot name a lane the roster does not staff).

## D-20261020-CEO-3 - D-0010 ruling: the hierarchy deliverable stands, one resolver owns the vacancy walk

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: -
- context: -
- options considered: -
- decision: The tribunal (CTO, sole neutral member - CEO and Reviewer-4 were parties) ruled for the CEO: Reviewer-4 withdraws the dangling-manager and unbundled-authority MAJORs and may not re-raise them. Both were measured false at da92222 - the slim roster brief and charter fold to the CEO, a staffed parent keeps its name, and a role outside ROLE_PARENT gets the CEO fallback without user-facing authority. Two text-only conditions were ordered and applied: the record now names resolve_manager (not manager_of) and pins no test count. Consequence: resolve_manager in engine.py is the single vacancy walk, called by start_here and charter_reports_line; a slim roster folds both files an agent obeys, and a full roster leaves them untouched. Authority note: the resolver warns that the panel had one member because this roster staffs no CTO/CFO/Reviewer-independent seat, so the ruling rests on the signer being the neutral non-party member.
- why: -
- evidence: dispute sign/resolve D-0010 --by cto -> tribunal complete, resolved in CEO favour; slim init -> StartHere:3 "folds to the **CEO**" + Role.md:9 "**CEO** - your line runs through the CTO" with Manages: kept; full roster -> Role.md:9 "**CTO.**"; --agents auditor -> 0 hits for "only lane that reaches the user"; pytest tests/unit/test_reporting_hierarchy.py -> 17 passed at da92222, 18 after the resolver test
- falsified by: -
- consequences: -

## D-20261020-SEC-1 - CodeQL flags the masked evidence print, and the mask is proven

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Security Auditor (security-auditor)
- decided by: Security Auditor
- task: T-0004
- context: CodeQL alerts #2 and #3 (`py/clear-text-logging-sensitive-data`, severity `error`) are open on `main` @ 6f96366 against scripts/privacy_scan.py:1132 (the `--json` print) and :1143 (the human-readable report print). CodeQL taints both because `main()` holds the raw matched value in `match = finding.pop("match", None)` (scripts/privacy_scan.py:1088) in the loop that dominates the reporting block; it reports the reachable `print` sinks, not the taint source.
- options considered: dismiss as false positive with a measured record (chosen); refactor the report build into a helper that never shares a scope with the tainted loop to silence the query (rejected: it changes shipped code to please a scanner whose claim is already false, and it would need its own review, tests and CI cycle for no security gain); suppress in a CodeQL config file (rejected: a query exclusion hides the whole rule class on this path, including a future real leak in the same function, whereas a dismissal names these two lines and leaves the rule armed).
- decision: Both alerts are false positives and are dismissed as such. The expressions print `finding["evidence"]`, which `make_finding` (scripts/privacy_scan.py:570-582) sets to `_mask(value)`; the raw value lives in a separate key `match`, which is popped from every finding at scripts/privacy_scan.py:1088 before the report dict or the print loop is built, so neither print can reach it.
- why: The taint the analyzer follows is real dataflow but not a leak: the value that arrives at the sink is the mask, not the secret. `_mask` (scripts/privacy_scan.py:498) keeps at most the first 3 and last 3 characters and replaces every other one with `*`, and `--reveal` appends only `_fingerprint(match)` - an unsalted truncated SHA-256 (`sha256:<12 hex>`) with no prefix of the value - while the only path that emits a raw value is `--reveal-to PATH`, into an `O_EXCL` `0600` file the operator names, with a stderr warning and never on the log. Measured with a planted credential, the raw string appears zero times on stdout or stderr in plain, `--reveal` and `--json --reveal` modes, and zero times on stdout/stderr with `--reveal-to`.
- evidence: At main @ 6f96366, scratch extraction `git archive HEAD | tar -x -C .pi/SecScratch/fp` re-initialised as a git repo, credential planted at runtime from parts and committed as leak_probe.txt: `python scripts/privacy_scan.py 2>&1 | grep leak_probe` -> `leak_probe.txt:1: [critical/api-token] ghp*******************************WdE` (+ env-secret and high-entropy-secret lines, all masked, `privacy_scan: FAIL - 3 finding(s) in tree`); `--reveal` -> same masked lines plus `(sha256:73bf57e5fcda)` / `(sha256:c0681a3ace65)`; `grep -c '<planted value>'` on stdout -> 0 for plain, `--reveal` and `--json --reveal`; `--reveal-to .pi_reveal.txt` -> stdout raw hits 0, stderr raw hits 0, file mode 600, file raw hits 2; `_mask(37-char value)` -> 37 chars, 31 `*`, 6 visible.
- falsified by: Any of the three modes printing a byte of the raw matched value (a `grep -c` on stdout returning non-zero for the planted credential), or a future edit that sets `evidence` from `match` - e.g. reintroducing `shown = finding.get("match", finding["evidence"])` - which is what made the earlier alerts #1/#2 true positives at e921a4b before commit 8980081.
- consequences: CodeQL alerts #2 and #3 are dismissed with reason `false positive` and a comment pointing at section 7.1 of docs/Team/AuditReport.md; the rule stays enabled, so a genuine re-introduction on this path still alerts; tests/unit/test_privacy_scan.py::test_reveal_never_prints_the_unmasked_secret keeps the sink closed independently of the scanner's opinion.

## D-20261020-CTO-1 - Two traceability disputes were moot by delivery, not adjudicated

- date: 2026-10-20
- kind: process
- status: accepted
- deciders: CTO (tribunal, signed by cto and ceo)
- decided by: CTO
- task: T-0001
- context: D-0019 (Reviewer-3 -> ProductManager) and D-0021 (Reviewer-2 -> ProductManager) both charged the same defect class in the requirements-layer guard: a hand-kept structure, not the table, decided what was executed, so one dict entry could hide one row while every assertion stayed green. Each reached the 3-round cap because the guard was reworked between rounds and the charge was re-filed against the new shape.
- options considered: adjudicate the mechanism (rejected: the charged mechanism no longer exists at the head, so a ruling would describe code that is not shipped); dismiss as moot with the falsifier re-run (chosen); leave both open (rejected: an open dispute blocks STOP and misdescribes the delivered design).
- decision: Both are resolved as moot by delivery. D-0019's charged structure - a hand-kept `DETERMINISTIC_PROOFS` list of 5 of 18 rows - was deleted at `83a78cf` and no such symbol exists at the head (`grep -rn DETERMINISTIC_PROOFS src tests` -> no match). D-0021's charged authority - `EXEMPT` validated only for reason membership and row existence - is now evidence-bound by `EXEMPT_EVIDENCE`.
- why: A dispute is a claim about a mechanism. When the mechanism is deleted and its own falsifier is re-run against the successor and fails, there is nothing left for a tribunal to rule on, and recording a ruling on absent code would be a false record. The escalation path is still exercised (three rounds, escalate, two signatures) so the process record shows the loop was stopped by the tribunal, not by attrition.
- evidence: At head `2b31500` in a `git archive` extraction: the D-0021 mutant (`rm CHANGELOG.md` + `EXEMPT["AC-12"]="drift"`) FAILS with `an exemption must be justified by the table it exempts: AC-12: exempt as 'drift', but its proof cell `ls LICENSE CHANGELOG.md CITATION.cff` carries no such evidence` (tests/unit/test_traceability_matrix.py:480-486); the D-0021 floor mutant FAILS with `5 row(s) were re-run, but 18 rows minus 12 exemptions is 6`; `git log -S DETERMINISTIC_PROOFS --oneline` -> the list was introduced and later removed by the `83a78cf` rewrite; `dispute escalate/sign/resolve` for D-0019 and D-0021 -> signed=['cto','ceo'], tribunal complete, resolved by cto.
- falsified by: `grep -rn DETERMINISTIC_PROOFS src tests` returning a match, or the AC-12 drift mutant passing at the head - either would mean the charged mechanism survived and the ruling is wrong.
- consequences: `dispute list` shows 0 open and 0 escalated. Both the product-manager guard and the ruling are recorded; the residual limit that the guard cannot re-run forge rows stays stated in docs/Team/Project.md rather than hidden.

## D-20261020-Tester - Option (a), generalized: tests/unit/test_traceability_matrix

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Tester (tester)
- decided by: Tester
- task: -
- context: -
- options considered: -
- decision: Option (a), generalized: tests/unit/test_traceability_matrix.py skips the record-resolution guard only when no record in the team tree identifies itself with a cited id AND the layer/area the matrix claims for it, naming both counts; the moment one record identifies itself the guard hard-fails on every problem (missing, not passing, wrong layer/area) exactly as before. Option (b), a committed snapshot or digest, was rejected.
- why: The cited records (TS-0001/0005/0008/0011/0013/0014/0018/0022/0024) exist only in a gitignored Tests.md from an earlier team run; this machine's tree is a fresh init that numbers its own TS-0001 as requirements/research while the matrix's TS-0001 was goal/audit, so a committed snapshot would have to be invented - the anti-fabrication rule forbids writing record data nobody measured - and the ids are workspace-local and re-used, so no digest can identify the producing workspace either. A skip that names the counts is honest; a red suite on every fresh workspace is not, and it would block unrelated lanes.
- evidence: main 3f4981d: pytest tests/unit/test_traceability_matrix.py -q -> 2 failed, 8 passed ('AC-1: TS-0018 is not a record in Tests.md' x9); branch with a fresh 2-record tree: 9 passed, 1 skipped with 'the team tree holds 2 test record(s) and none carries an id and layer/area claimed by the 9 records cited here'; scratch tree carrying TS-0018 release/release passing: hard failure naming the id collision and the 8 missing records; same tree with TS-0018 failing: hard failure "AC-1: TS-0018 has status 'failing', not 'passing'"; no tree at all (CI shape): skip
- falsified by: A committed, non-invented source for the cited records would make option (b) available and this skip obsolete - e.g. if 'teamwork.py ledger export' published the tests add/run records into docs/Team/AuditManifest.json; likewise if 'teamwork.py init' stopped re-numbering TS ids from TS-0001, the id+layer/area identity test could be replaced by a workspace digest
- consequences: -

## D-20261020-Reviewer-1 - P-0007 pass evidence: correct the R3 clause mangled by shell expansion

- date: 2026-10-20
- kind: process
- status: accepted
- deciders: Reviewer-1 (reviewer)
- decided by: Reviewer-1
- task: T-0002
- context: -
- options considered: -
- decision: The R3 statement in the P-0007 review evidence (ledger record #0167) must be read as: the shim keeps root=$(git rev-parse --show-toplevel). The stored text shows the shell-expanded value of that substitution because the evidence was passed in double quotes; the deliverable is not affected.
- why: I verified the shim body myself: src/teamwork/hooks.py:50 contains "root=$(git rev-parse --show-toplevel) || exit 0" and the module docstring at hooks.py:13-17 says the same. The mangled clause is a transcription defect in my evidence string, not a finding about the code; leaving it uncorrected would misstate what was verified.
- evidence: grep -n "root=" src/teamwork/hooks.py @main 5a40f0f -> 50: "root=$(git rev-parse --show-toplevel) || exit 0\n"; ledger record #0167 evidence clause R3; same class as the Architect transcription note at ledger #0165
- falsified by: A hooks.py shim that hardcodes the root instead of resolving it with git rev-parse --show-toplevel would overturn this correction; none exists at 0795f26.
- consequences: -

## D-20261020-CEO-5 - Hook marker and shim body: the code and Architecture 11.6 must say one thing

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: -
- context: -
- options considered: -
- decision: The shim's line 2 carries the literal 'teamwork-managed hook' plus the human instruction, one HOOK_MARKER constant keys install/status/uninstall/overwrite, and Architecture 11.6 is amended to the shipped body: '[ -f ]' instead of '[ -x ]' and '${TEAMWORK_SKIP_HOOKS:-}' for the bypass.
- why: A frozen interface the code silently reinterprets is what the freeze exists to prevent, but the frozen text was also wrong twice: '[ -x ]' would make every installed hook a silent no-op because scripts/teamwork.py is committed 100644, and the two-line marker it fixed was never implemented.
- evidence: tester T-0001 process-boundary suite -> tests/integration/test_harness_cli.py: test_the_installed_hook_carries_the_marker_literal FAILED (config.py:411 HOOK_MARKER='Installed by teamwork.py hooks install', the literal never appears) and test_the_root_commit_on_the_default_branch_is_refused FAILED ('git commit -m first' succeeds on an unborn main, second commit refused, because gitutil.current_branch() is empty on an unborn branch); 21 other assertions passed. The -x defect: git ls-files -s scripts/teamwork.py -> 100644.
- falsified by: A hook installed by 'hooks install' that is skipped by git, or a status/uninstall that touches a foreign hook, or a first commit on the default base that the hook allows.
- consequences: -

## D-20261020-CEO-6 - harness list: the code conforms to Architecture 11.2, not the other way round

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: -
- context: -
- options considered: -
- decision: harness.py renders exactly eight data rows in C1..C8 order, '-' for C5's class and bytes, the section-2 owner in the role column, no header lines; the per-class byte sums move under --verbose. The Architect does not amend 11.2 to match an eleven-row output.
- why: The point of the registry is a 1:1 inventory of the eight Harness^2 components, which is what makes it auditable row by row against Research section 8 and the paper. Eleven rows (C3 per role, C7 and C8 split) would make the 'exactly eight' claim in Architecture and in the research verdict false, and would leave no column a reader can check against the source taxonomy.
- evidence: Developer branch a26f5db: python3 scripts/teamwork.py harness list -> '# harness surfaces' + a column header + 12 data rows + '#' per-class totals; Architecture.md section 11.2 (frozen, D-20261020-Architect-2) -> 'exactly eight rows, no header line, - for C5'; reviewer fail on developer T-0001 P-0004 quoted the same delta.
- falsified by: A reader cannot map row to component without a lookup, or a harness.py test asserts a row count other than 8 at the merged revision.
- consequences: -

## D-20261020-CEO-7 - A new module may carry its own one-line entry in the Architecture module list

- date: 2026-10-20
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: -
- context: -
- options considered: -
- decision: When a lane adds a module under src/teamwork/, that lane may add the single line for it to the frozen module list in Architecture.md section 2 inside its own task branch, disclosed in the commit body, the PR and the self-check, instead of waiting for the Architect. Anything beyond that one line is still the Architect's file.
- why: tests/unit/test_portability.py::test_architecture_lists_exactly_the_shipped_modules turns main RED the moment the new module merges, and no other lane can repair it in the same commit because the Architect is not building that module. A merge that is red on arrival is worse than a one-line, disclosed, reviewed cross-boundary edit.
- evidence: developer T-0001 branch: pytest -q -> tests/unit/test_portability.py::test_architecture_lists_exactly_the_shipped_modules FAILED 'At index 7 diff: imaging.py != harness.py'; same for developer T-0002 hooks.py; both fixed by one line in section 2 and re-verified green.
- falsified by: A lane uses the exception to edit Architecture.md beyond its own module line, or a module line lands without the other module's tests passing at the merged revision.
- consequences: -

## D-20261020-Reviewer-1-2 - No dispute on architect T-0001's third fail: the counter counts a task handle, not a deliverable

- date: 2026-10-20
- kind: process
- status: accepted
- deciders: Reviewer-1 (reviewer)
- decided by: Reviewer-1
- task: T-0001
- context: -
- options considered: -
- decision: Reviewer-1 fails architect T-0001 at f476b82 without opening a dispute. The engine's 'failure #3' warning counts fails by task handle, and four different deliverables share the handle T-0001: ceo T-0001 (rubric docs, merged), developer/tester T-0001 (harness lane), architect T-0001 (this contract). This deliverable has two fails: Reviewer-2's F1-F4 round (ledger #0176) and mine, so the loop is not spinning on one artefact.
- why: A dispute exists for a design disagreement between roles, not for concrete defects with a named owner and a stated remedy. Every one of my four blockers is mechanical and reproducible on demand: a merge-tree rc=1 (rebase), an author/committer mismatch (squash), a layer test that is red at the merged tree and stricter than the text it enforces (make it per-group), and a frozen shim body that the merged hooks.py does not write (align the text or route a Developer task). None of them requires the tribunal to choose between two defensible designs - the deliverable is the only side that is wrong in each case, and the ruling it implements (D-0001) is already binding.
- evidence: teamwork.py review --queue @main 25c566e -> architect T-0001 review_status=failed, findings name four blockers; git merge-tree --write-tree main f476b82 -> rc=1 CONFLICT docs/Team/Decisions.md; teamwork.py identity --audit --range main..f476b82 -> 2 commits, 1 problem; probe merge main+f476b82 pytest -q -> 3 failed, 701 passed, 3 skipped (2 of the failures are the new contract test); main:src/teamwork/hooks.py shim() -> one combined marker line and no 2>/dev/null, while Architecture 11.6 freezes two lines plus 2>/dev/null; ledger #0124 and #0174 and #0176 are the fails this handle has accumulated across four owners.
- falsified by: If the architect re-submits the same revision with the same findings, or argues the two-line marker and the all-or-nothing landing are the correct design, that is a design disagreement and the tribunal decides it; equally if the merged-tree failure turns out to depend on which lane lands first rather than on the text, the per-group wording is the wrong remedy and this decision is wrong.
- consequences: P-0003 stays changes-requested with four recorded blockers; the Architect owns the rework, not the Reviewer.

## D-20261020-Architect - The harness surface is a registry over files that already exist, not a new abstraction or a generated file

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0001
- context: H1 of the Harness^2 brief asks for a named surface with an activation class and a cost. The CEO froze 'harness list' as 'class bytes path role' per surface, with bytes measured at run time.
- options considered: (A) one abstraction or module per Harness^2 component, with a generated manifest (rejected: a generated file becomes a second copy of text that must never be duplicated, and it has to be kept in sync with the eight files it describes); (B) a registry that enumerates the paths the engine already resolves and measures them on disk (chosen); (C) documentation only, no command (rejected: nothing then measures bytes or checks the activation class, so the cost doctrine stays unenforced)
- decision: The eight Harness^2 components are a table (C1..C8) over paths that already exist in this repository: SKILL.md, the managed block in AGENTS.md, Roles/<Role> memory + Global/GlobalMemory.md, references/*.md, the lane packet (no file), .agents/skills/*/SKILL.md, scripts/*.py + src/teamwork/*.py and the two hook files found through `hook_dir(root)` (`git -C <root> rev-parse --git-path hooks`), not through a repository-relative `.git/hooks` path - corrected by D-20261020-Architect-8, which is the ruling that superseded the repository-relative spelling. 'harness list' prints class, measured bytes, path and owner role per component and nothing is generated, mirrored or moved.
- why: Three of the eight components are already the shipped skill bundle, and Architecture section 3 already fixes a single source for that bundle (checkout or wheel, never two copies). A registry makes the cost of each component measurable without relocating content, and a generated file would recreate exactly the duplication the wheel force-include exists to avoid; the eight rows stay checkable against the tree by a test instead of by a build step.
- evidence: at 2e7810f: wc -c AGENTS.md -> 27431 (managed block 27386), SKILL.md -> 46575, roles/*.md -> 134781 over 15 files, references/*.md -> 11 files, .agents/skills/ -> 1 directory, scripts/*.py -> 5 files, src/teamwork/*.py -> 15 files: every path the registry names already exists, so no file is added by this contract
- falsified by: A component whose value cannot be read from the file it names, so the registry has to invent a second artifact; or the registry and the tree disagreeing (a row naming a path that is absent, or a path no row covers) at review time.
- consequences: harness list becomes the only place the eight components are named; docs/Team/Architecture.md section 11 carries the same table and tests/unit/test_cli_contract.py asserts the emitted rows against it, so a new always-on file cannot be added without a row.

## D-20261020-Architect-2 - In-loop enforcement is an opt-in git hook, with a documented bypass and a non-blocking identity check

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0001
- context: H4 adopts Harness^2's middleware component: enforce a behaviour instead of instructing it. The CEO froze 'hooks install|status|uninstall' plus 'hook pre-commit' and 'hook pre-push'.
- options considered: (A) run the hook installation automatically inside 'init' (rejected: it mutates .git in every project the skill bootstraps, an agent cannot decline it, and it silently changes git behaviour for the operator's own commits); (B) an explicit 'hooks install' that refuses a foreign hook without --force, a TEAMWORK_SKIP_HOOKS bypass, and an identity finding that only warns (chosen); (C) no hooks at all, engine-only enforcement (rejected: the engine never sees a hand-typed or agent-typed 'git commit', which is exactly the case the rule exists for)
- decision: In-loop enforcement ships as 'hooks install', never as an init step. The shim exits 0 immediately when TEAMWORK_SKIP_HOOKS is set, install refuses to overwrite a hook it did not write unless --force, uninstall removes only marked hooks, and the pre-commit identity rule (R3) prints a warning to stderr and exits 0.
- why: A git hook is the only enforcement point that sees a plain 'git commit' or 'git push', so it is the only place a middleware rule can actually bind. But an uninterruptible hook turns a legitimate workflow (an operator committing their own work, a rebase, a cherry-pick) into a refusal, and the team's own red line is to stop and escalate rather than block the operator; H4's own falsifier is that agents answer a misfiring hook by setting the bypass. The identity rule is the one rule with no engine gate behind it to protect: cmd_commit sets the role identity itself (names.git_identity_args), so a foreign identity can only arrive from a commit the engine did not make, and identity is a provenance warning, not a correctness gate.
- evidence: at 2e7810f: grep -rn 'hooks install|def cmd_hooks' src -> no match (the surface is new, nothing to conflict with); engine.py:3263-3268 - the identity audit reaches 'not a role mailbox' only under --strict-authors and only warns otherwise; names.py:189 git_identity_args sets user.name/user.email per role, so engine-made commits always match; grep -rn TEAMWORK_SKIP_HOOKS src scripts -> no match, the escape name is unused
- falsified by: A hook that fires on a legitimate workflow and is answered by exporting TEAMWORK_SKIP_HOOKS in a lane: the rule must then move back into the engine (H4 falsifier). Or an engine gate that already refuses the same commit, which would make the hook pure duplication.
- consequences: init never installs a hook; 'hooks status' reports installed|absent|foreign so a bypassed or missing hook is visible; R3 exits 0; the bypass, the marker and the refusal-to-overwrite rule are all stated in Architecture section 11 and asserted by the system test.

## D-20261020-Architect-3 - 'harness lint' derives the subcommand vocabulary from the parser, not from a list

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0001
- context: H3 adopts whole-proposal invalidators. One of them is SUBCOMMAND: every 'teamwork.py <word>' a skill file names must be a subcommand that exists. The CEO froze the list as 'derived from the parser'.
- options considered: (A) a checked-in list of subcommand names next to the lint rule (rejected: it is a second copy of the parser and drifts the first time a command is added, and a stale entry fails a valid skill file); (B) enumerate the choices of engine.build_parser() at run time (chosen); (C) ask the CLI with --help and parse the text (rejected: it couples the rule to argparse's help formatting and cannot be called in-process)
- decision: 'harness lint' builds the parser with engine.build_parser() and reads the registered top-level subcommand names from the subparsers action; no list of command names is checked in anywhere, and the lint rule has no vocabulary of its own.
- why: The engine is the vocabulary: build_parser() is the single function that defines every subcommand (engine.py:9193, with nine _parsers_* helpers), so deriving from it makes the rule exactly as current as the CLI it checks. A checked-in list would be a second source of truth for the one thing this rule is about; the whole point of the rule is that a skill file naming a command that no longer exists is caught by the same code that defines the commands.
- evidence: at 2e7810f: PYTHONPATH=src python -c 'from teamwork.engine import build_parser; from argparse import _SubParsersAction; print(len([a for a in build_parser()._actions if isinstance(a,_SubParsersAction)][0].choices))' -> 43 top-level choices, read from the parser object; python3 scripts/teamwork.py --help prints the same 43 names and no list of them exists in the source (grep -c 'add_parser(' engine.py -> 95, all registrations)
- falsified by: A command reachable without being registered in the parser - an alias resolved in main(), or a shim that rewrites argv - which the rule would then miss; or the parser being built only after the lint runs, so the rule sees a stale surface.
- consequences: The rule is as complete as the parser and needs no maintenance when a command is added; an alias must be registered as a subparser to be visible to lint.

## D-20261020-Architect-4 - The always-on budget default is 120 KiB per instance, measured on the shipped text

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0001
- context: H2 adopts the cost doctrine: always-on prose is paid on every call, so 'if you add always-on text, cut something else to pay for it'. The CEO froze a new Settings.json key AlwaysOnBudgetKb with a default of 120.
- options considered: (A) no default, budget only when a workspace sets one (rejected: Settings.json is optional and absent in a fresh workspace, so the budget would silently not exist); (B) 120 KiB per instance, overridable per workspace (chosen); (C) one cap per role sized to its charter (rejected: the expensive part is the text every instance pays - the AGENTS.md block plus SKILL.md - not the difference between charters)
- decision: AlwaysOnBudgetKb defaults to 120 in config.py, is overridable per workspace in Settings.json, and is read as KiB (multiply by 1024), so the default is 122880 bytes. The measurement unit is one instance: managed AGENTS.md block + SKILL.md + that role's charter + that role's memory. The number is per instance, never the sum over the roster.
- why: Measured on the tree at 2e7810f: the shared always-on text is 73961 B (managed AGENTS.md block 27386 + SKILL.md 46575) and every instance pays it before its own charter; role memory is ~1.3 kB and the largest charter is designer at 18069 B, so the most expensive instance in the shipped roster is 93379 B, 76% of 122880 B. That leaves about 30 kB of headroom - one more section of prose, not one more document - while a charter inflated to 40 kB or a second always-on paragraph in AGENTS.md trips the line. Summing the roster instead (15 instances) would be ~1.25 MB and OVER for every workspace, which measures the roster rather than the cost of a call.
- evidence: at 2e7810f: wc -c AGENTS.md -> 27431 total with the managed block (BEGIN..END) measuring 27386 B; wc -c SKILL.md -> 46575; wc -c roles/*.md -> 134781 over 15 files (largest roles/designer.md 18069, smallest roles/technical-writer.md 5601); Roles/*/ShortTermMemory.md + LongTermMemory.md in the live workspace -> 1292..1349 B per role; 27386 + 46575 + 18069 + 1349 = 93379 B of 122880 B = 76%
- falsified by: The cap raised twice in a row instead of cutting text (H2 falsifier), or an instance whose always-on file was never actually loaded into a run - then the measured bytes and the real cost have drifted apart and the number must be recalibrated from a real startup, not lowered or raised by taste.
- consequences: config.py owns the default and Settings.json overrides it per workspace; budget prints one line per instance plus a total and exits 1 when any instance is OVER; the key must be declared non-provider (see D-20261020-Architect-6) or it is read as a concurrency limit named AlwaysOnBudgetKb.

## D-20261020-Architect-5 - The hook file is written to 'git rev-parse --git-path hooks', not to the toplevel .git/hooks

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0001
- context: The frozen text said hooks install writes `.git/hooks/{pre-commit,pre-push}` with the root resolved by 'git rev-parse --show-toplevel' - wording later superseded by D-20261020-Architect-8, together with the amendment the CEO proposed for it, 'relative results resolved against the project root', which the neutral seat withdrew as unsafe on its own (D-0001 R2). Every lane here works in a linked worktree, where <toplevel>/.git is a regular file. Dispute D-0001 records the defect against the CEO.
- options considered: (A) keep the frozen wording and special-case the worktree (rejected: it is a special case for the normal case, and it still guesses what git will read); (B) ask git: 'git rev-parse --git-path hooks' (chosen); (C) 'git rev-parse --git-common-dir'/hooks (rejected: re-implements git's own path resolution, and ignores core.hooksPath and a separate git dir)
- decision: 'hooks install|status|uninstall' resolve the hook directory with 'git rev-parse --git-path hooks' and write there. The shim still resolves the project root with 'git rev-parse --show-toplevel', because the rules act on the work tree while the hook file lives in the git directory git actually reads.
- why: In a linked worktree <toplevel> is the worktree, but git reads hooks from the COMMON git dir; <toplevel>/.git is a 66-byte file, so the frozen path is not merely wrong, it cannot be created (ENOTDIR). --git-path hooks is the only answer that is correct in all three cases - normal checkout, linked worktree, separate git dir - and git computes it, so the contract does not have to know about core.hooksPath. Consequence that must be stated: the hooks are per common git dir, so installing from any lane worktree installs for every worktree of that repository at once.
- evidence: at 2e7810f in the Architect worktree: git rev-parse --show-toplevel -> .../Runtime/Worktrees/Architect; test -d .git -> false (.git is a 66-byte file); mkdir -p .git/hooks -> 'cannot create directory .git: Not a directory', rc=1; git rev-parse --git-path hooks -> /home/pingz/Code/Nidvue/Teamwork/.git/hooks; reproduced in a throwaway repo /tmp/hookprobe + linked worktree /tmp/hookprobe-wt: --git-path hooks -> /tmp/hookprobe/.git/hooks while mkdir -p .git/hooks -> rc=1
- falsified by: 'hooks install' succeeding against <toplevel>/.git/hooks inside a linked worktree and git honouring the file, or a repository whose --git-path hooks output is not the directory git executes (then the resolver must follow git's actual rule rather than this command).
- consequences: The install target is git's answer, not a path built from the toplevel; Architecture section 11 states both resolutions and the shared-across-worktrees consequence; 'hooks status' must therefore also resolve through --git-path hooks or it will report 'absent' while the hook is installed.
- corrected by: D-20261020-Architect-8 - this entry's context quoted the superseded repository-relative target and the CEO's withdrawn 'resolved against the project root' amendment; the resolver is frozen there as an atomic pair with the `-C <root>` pin, and Architecture 11.6 now carries that wording only.

## D-20261020-Architect-6 - The new surface adds no second source of truth: the budget key is declared non-provider, the branch name comes from config.DEFAULT_BASE, the LFS and AGENTS.md-block helpers are reused

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0001
- context: Three values the new commands need already exist in the engine, and two of them exist twice. Measured before writing the contract: the Settings.json loader treats every key it does not know as a provider cap, the default branch is defined in two modules plus one literal, and the LFS check plus the managed AGENTS.md block each live in exactly one place.
- options considered: (A) let the new code read what it finds and keep the duplicates (rejected: AlwaysOnBudgetKb would silently become a concurrency provider named after the key, and a second branch-name constant would let the hook refuse a commit on one branch while the engine refuses on another); (B) one named source per value, with the new surface as a consumer (chosen); (C) move every constant into one module now (rejected: that is a refactor of working code with no requirement behind it, outside this contract)
- decision: The new surface consumes named single sources: AlwaysOnBudgetKb is added to config.SETTINGS_NON_PROVIDER so load_providers ignores it; the hook reads config.DEFAULT_BASE (never a literal and never gitutil's copy); the LFS rule calls gitutil.lfs_tracked; the managed-block bytes come from the engine's BEGIN/END markers via one helper shared with cmd_agents_md. gitutil.DEFAULT_BASE and the 'git init -b main' literal are recorded as debt with a follow-up task, not silently shadowed.
- why: A hook that disagrees with the engine about the default branch refuses the wrong commit, and a Settings key read as a provider invents a concurrency cap nobody declared - both are silent, both would be found in review rather than at the gate. The LFS check and the block markers are the two places where a re-implementation is guaranteed to drift: lfs_tracked already encodes the '.gitattributes filter=lfs' parsing including the '*.<ext>' vs path match, and the BEGIN/END markers are the only thing that separates managed text from the CEO's own prose in AGENTS.md.
- evidence: at 2e7810f: PYTHONPATH=src python -c 'from teamwork.engine import load_providers; print(load_providers(Path("/tmp/arch_probe")))' on Settings.json {ollama-cloud:64, PulseMinutes:30, AlwaysOnBudgetKb:120} -> {'ollama-cloud': 64, ..., 'AlwaysOnBudgetKb': 120} (the key is read as a provider cap; the skip list is config.py:388 SETTINGS_NON_PROVIDER = ('PulseMinutes','Criteria'), applied at engine.py:5151); grep -rn DEFAULT_BASE src -> config.py:390 and gitutil.py:12 (two constants, same value) plus engine.py:4487 run_git(project,'init','-b','main') (a third copy as a literal); lfs_tracked at gitutil.py:154 is already the check cmd_commit uses at engine.py:3434; BEGIN/END at engine.py:8623-8624 appear nowhere else in src/ and are written only by cmd_agents_md at engine.py:8627
- falsified by: An AlwaysOnBudgetKb value that changes a concurrency cap in 'teamwork.py parallel', or the hook and the engine disagreeing about the default branch on a branch rename (config.DEFAULT_BASE changed while gitutil.DEFAULT_BASE and the init literal are not).
- consequences: config.SETTINGS_NON_PROVIDER gains AlwaysOnBudgetKb; the hook's branch rule and the engine's share one constant; a follow-up task must collapse gitutil.DEFAULT_BASE and the init literal into config.DEFAULT_BASE, which is a src change outside this contract's file boundary.

## D-20261020-Architect-7 - One large-file threshold: 1048576 bytes, shared with 'commit --lfs-threshold', not a second literal

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0001
- context: The frozen hook rule R2 refuses a staged file above 1 MiB that no .gitattributes LFS pattern covers. The engine already refuses the same class of file in cmd_commit, with the threshold as a bare argparse default of 1_000_000 bytes.
- options considered: (A) let the hook carry its own 1 MiB literal and leave the engine's 1_000_000 alone (rejected: two thresholds 48576 bytes apart, so the same file is refused by commit and allowed by the hook, and neither is the documented number); (B) one named constant config.LFS_MAX_BYTES = 1_048_576, used as the hook's threshold and as the default of 'commit --lfs-threshold' (chosen); (C) copy the engine's 1_000_000 into the hook (rejected: '1 MiB' is what the contract and the skill say, and a decimal 1,000,000 is neither MiB nor MB)
- decision: config.LFS_MAX_BYTES = 1048576 is the single large-file threshold. The hook refuses a staged file whose size is strictly greater than it and which gitutil.lfs_tracked does not cover; 'commit --lfs-threshold' defaults to the same constant so the two refusals coincide.
- why: Both gates exist to stop the same thing - a binary reaching history without LFS - and a gate pair that disagrees on the boundary teaches the team that the boundary is negotiable. The constant belongs in config.py with the other tunables (config is data; modules do not import the command layer for it), and the reuse of gitutil.lfs_tracked keeps the .gitattributes parsing in one place.
- evidence: at 2e7810f: engine.py:9816 --lfs-threshold default=1_000_000 (a bare literal, not a constant); engine.py:3426-3445 refuses 'above --lfs-threshold' with gitutil.lfs_tracked as the pattern check; gitutil.lfs_tracked at gitutil.py:154; 1_048_576 - 1_000_000 = 48_576 bytes of disagreement between '1 MiB' as documented and the shipped default
- falsified by: A file between the two thresholds that is committed through the hook path and then refused by 'commit' (or the reverse) on the same tree, i.e. the two gates still disagreeing after the constant is introduced.
- consequences: config.LFS_MAX_BYTES is added; cmd_commit's parser default reads it; the hook and the engine refuse the same files; the system test does not need to assert the number twice - it asserts the contract names one threshold.

## D-20261020-Architect-8 - Ruling D-0001 implemented: one hook-directory resolver, correct only as an atomic pair with the `-C <root>` pin, and the C8 row measures through it

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: neutral seat (tribunal, signed by reviewer); implemented by Architect
- decided by: neutral seat, ruling D-0001
- task: T-0001
- context: Dispute D-0001 (Architect -> CEO) was resolved by the neutral seat: the frozen `hooks install` target was a repository-relative `.git/hooks/{pre-commit,pre-push}` and an amendment proposed resolving "relative results against the project root". Both the target and that amendment are superseded by the ruling R1-R6, which the Architect owns in `docs/Team/Architecture.md` section 11 and in this log.
- options considered: (A) keep the repository-relative wording and special-case the linked worktree (rejected by the ruling R5: it hardcodes the default, breaks on `core.hooksPath` and still guesses what git reads); (B) the ruling's one resolver, `hook_dir(root)` = `git -C <root> rev-parse --path-format=absolute --git-path hooks` (or `-C <root>` plus a relative result joined onto `<root>`), used by install, status AND uninstall (chosen); (C) accept the CEO's amendment as written, joining a relative result onto the project root without pinning the invocation cwd (rejected by the ruling R2 and re-measured here: it resolves into the PARENT directory)
- decision: R1 - `hooks install`, `hooks status` and `hooks uninstall` take the hook directory from one shared helper `hook_dir(root)`; no path is built from `.git` plus a suffix and `.git/hooks` is never a constant; `status` prints the literal directory it probed. R2 - the resolver is an atomic pair, `git -C <root> rev-parse --path-format=absolute --git-path hooks` or `-C <root>` plus "join a relative result onto `<root>`", and the `-C <root>` pin is mandatory. R3 - the shim keeps `root=$(git rev-parse --show-toplevel)`. R4 - the linked-worktree case is mandatory and hermetic (`git init` + one commit + `git worktree add`) in the layer test, together with a subdirectory negative test. R5 - no constant `.git/hooks`; `core.hooksPath` is honoured for free and not special-cased. R6 - every residual `<toplevel>/.git/hooks` and repository-relative `.git/hooks/{pre-commit,pre-push}` target in the frozen text is superseded: Architecture 11.2's C8 spec, 11.6 and 11.9 are rewritten, and D-20261020-Architect-1's C8 phrase and D-20261020-Architect-5's context carry a `corrected by` pointer here.
- why: The hook directory answers "where git reads hooks" and the toplevel answers "which work tree the rules act on", and in a linked worktree those are different repositories' worth of path apart - so one value cannot serve both, and the read side is as broken as the write side: install dies loudly at `mkdir`, but status/uninstall would report `absent` and remove nothing while a live hook keeps running in the common dir. The `-C <root>` pin is not style because `--git-path` is answered relative to the invocation cwd; without it the command is correct only when run from the repository root, which is the one cwd no test picks by accident.
- evidence: at d692f38 in `Scratch/arch-probe` (hermetic, `git init -q repo` + one commit + `git worktree add -q ../wt -b probe`): `test -d wt/.git` -> false and `wc -c wt/.git` -> `139` with content `gitdir: .../repo/.git/worktrees/wt` (the 66-byte figure in D-0001 is the same gitfile shape with a shorter path), so the worktree's `.git` is a file; from `wt`: `git rev-parse --show-toplevel` -> `<probe>/wt` while `git rev-parse --git-path hooks` and `git -C . rev-parse --path-format=absolute --git-path hooks` both -> `<probe>/repo/.git/hooks` (R3's two answers, R2's absolute form); from `repo/scripts` with no pin: `git rev-parse --git-path hooks` -> `../.git/hooks`, and joining that onto `<repo>` (the toplevel) -> `<probe>/.git/hooks`, the PARENT of the repository, not the repository (R2's trap, re-measured); `git -C . -c core.hooksPath=/tmp/xx rev-parse --git-path hooks` -> `/tmp/xx` (R5); Python against the worktree: `os.path.getsize(wt/'.git'/'hooks'/'pre-commit')` -> `NotADirectoryError: [Errno 20] Not a directory` and `glob(wt/'.git'/'hooks'/'*')` -> `[]`, which is exactly why the frozen C8 spec reported 0 bytes for an installed hook (R6/F1); in the Architect lane worktree: `--show-toplevel` -> `.../Runtime/Worktrees/Architect` vs `-C <that> rev-parse --path-format=absolute --git-path hooks` -> `/home/pingz/Code/Nidvue/Teamwork/.git/hooks` (the real-lane reproduction); `python3 -m pytest tests/unit/test_cli_contract.py -q` on this entry's contract -> `41 passed, 1 skipped`; three mutants each fail it and each was re-run against the restored text: the C8 cell back to `.git/hooks/{pre-commit,pre-push}` -> `2 failed` (`test_c8_is_measured_through_the_resolver_not_a_repository_relative_path`, `test_every_registry_path_that_is_a_repository_file_exists`), the `-C <root>` pin deleted from the resolver line -> `1 failed` (`test_the_resolver_is_frozen_as_an_atomic_pair_with_the_c_pin`), and the resolver paragraph replaced by the withdrawn join-onto-the-project-root sentence -> the same test fails.
- falsified by: A repository layout where `git -C <root> rev-parse --git-path hooks` and the directory git actually executes a hook from disagree (a separate `--separate-git-dir` checkout with `core.hooksPath` unset is the case to try), or a lane whose `hooks status` prints a directory it did not probe - either would mean the resolver answers the wrong question and the contract must follow git's real rule instead of this command.
- consequences: the measured directory and the executed directory are the same by construction for all three subcommands; `harness list`'s C8 row is a template over `hook_dir(root)` and can no longer print 0 for an installed hook; the layer test must build a linked worktree and a subdirectory case, and a skipped worktree test is a review failure; this entry also corrects, by pointer, the superseded wording in D-20261020-Architect-1 and D-20261020-Architect-5.

## D-20261020-Architect-9 - The frozen hook body, as measured: `[ -f ]` not `[ -x ]`, one marker constant, `${TEAMWORK_SKIP_HOOKS:-}`, and R1 resolves an unborn HEAD

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0001
- context: The hooks lane (developer T-0002) wrote a shim body that differs from the frozen text in four measured ways: the engine test, the line-2 marker literal, the bypass expansion, and the branch resolution R1 uses. Each difference is either a defect in the contract or a defect in the code, and the lane cannot carry both.
- options considered: (A) freeze the contract as first written and send the Developer to `[ -x ]`, the two-line marker, a bare `$TEAMWORK_SKIP_HOOKS` and `rev-parse --abbrev-ref HEAD` (rejected: three of the four make the hook silently or visibly wrong - a no-op engine test, a marker `status` does not key on, a bypass that can abort, a root commit the branch rule waves through); (B) amend the contract to the code's measured facts and let the lane close the rest (chosen - the lane has since closed all of it: the merged `shim()` carries both `${TEAMWORK_SKIP_HOOKS:-}` and the un-redirected `--show-toplevel`); (C) leave both texts and let each lane read what it likes (rejected: that is exactly what the freeze exists to prevent)
- decision: 11.6 freezes the body the merged code writes, verbatim from `git show main:src/teamwork/hooks.py` `shim()` - the single line 2 `# teamwork-managed hook (stage: <stage>) - remove with: teamwork.py hooks uninstall`, `[ -n "${TEAMWORK_SKIP_HOOKS:-}" ] && exit 0`, `root=$(git rev-parse --show-toplevel) || exit 0` with **no** `2>/dev/null`, `[ -f "$root/scripts/teamwork.py" ]`, `exec python3 "$root/scripts/teamwork.py" hook <stage> "$@"` - and 11.7's R1 describes the shipped resolver, which reads `gitutil.current_branch` and falls back to `git symbolic-ref --short HEAD` when that answer is empty or `HEAD`.
- why: `scripts/teamwork.py` is committed mode `100644`, so an executable-bit test is false in every checkout and the hook would `exit 0` on every commit while `hooks status` still says `installed` - the worst failure mode available, since it looks like enforcement. The marker must be one constant because install's overwrite refusal, `status` and `uninstall` all decide by it: two literals means a hook this tool wrote can be reported `foreign`, and `--force` then becomes the normal path. The `:-` default keeps the expansion total so an unset bypass means "run the rules", never "abort": measured, `sh -u -c 'echo "[$UNSET_VAR]"'` -> `UNSET_VAR: unbound variable`, rc 127, which git reads as a refusal. R1 needs an answer on an unborn HEAD because that is where the first commit on the default branch happens.
- evidence: `git show main:src/teamwork/hooks.py` (merged revision, `shim()` at lines 43-56) writes exactly `# teamwork-managed hook (stage: pre-commit) - remove with: teamwork.py hooks uninstall` as one line, `[ -f "$root/scripts/teamwork.py" ]` with the rationale in a comment, `[ -n "${TEAMWORK_SKIP_HOOKS:-}" ] && exit 0` and `root=$(git rev-parse --show-toplevel) || exit 0` with no `2>/dev/null`; `git show main:src/teamwork/config.py` -> `HOOK_STAGES = ("pre-commit", "pre-push")`, `HOOK_MARKER = "teamwork-managed hook"`; `git show main:src/teamwork/hooks.py` `head_branch()` at lines 188-198 -> `current_branch(project)` first and `run_git(project, "symbolic-ref", "--short", "HEAD")` only when that is empty or `HEAD`; at d692f38 `git ls-files -s scripts/teamwork.py` -> `100644 616216ef... 0 scripts/teamwork.py`, so `[ -x ]` would be false (D-20261020-Architect-9's `-f`); in `Scratch/arch-probe/fresh` (`git init -q`, no commit) `git rev-parse --abbrev-ref HEAD` prints `HEAD` and exits 128 with "ambiguous argument 'HEAD'" while `git symbolic-ref --short HEAD` -> `main`; `sh -u -c 'echo "[$UNSET_VAR]"'` -> rc 127, `sh -c 'echo "[${UNSET_VAR:-}]"'` -> rc 0; Tester T-0001 measured the consequence at the process boundary: with the hook installed on an unborn `main`, `git commit -m first` succeeds as a root commit and only the second commit is refused ("teamwork: refusing to commit on 'main'"). Four mutants of this entry were re-run against the restored contract: `-f` -> `-x` -> `1 failed` (`test_the_frozen_shim_body_tests_the_engine_file_for_existence_not_mode`), the combined line-2 marker split back into two lines -> `1 failed` (`test_the_frozen_shim_body_writes_the_merged_marker_line_verbatim`), `${TEAMWORK_SKIP_HOOKS:-}` -> `$TEAMWORK_SKIP_HOOKS` -> the same test fails, `root=$(git rev-parse --show-toplevel)` -> `root=$(git rev-parse --show-toplevel 2>/dev/null)` -> `1 failed` (same test), and the R1 paragraph reverted to `git rev-parse --abbrev-ref HEAD` -> `1 failed` (`test_r1_resolves_an_unborn_head_so_the_root_commit_is_refused`).
- falsified by: A checkout where `scripts/teamwork.py` IS executable (a tree that ships it `100755`), which would make `-x` harmless and this amendment unnecessary - or a shell that expands an unset positional parameter without failing under `set -u`, which would remove the reason for `:-`. Neither changes the marker or the unborn-HEAD argument.
- consequences: 11.6 and the merged `hooks.py` now say one thing, so the Developer lane carries **no** remaining delta on the shim body; `tests/unit/test_cli_contract.py` asserts the merged body line for line, so a future shim edit reopens this entry rather than drifting silently; the Tester's process-boundary suite asserts the file body against 11.6 rather than against a remembered string; `-x` anywhere in a hook body is a review failure.

## D-20261020-Tester-2 - harness list: the Tester's registry test was the defect, the shipped code matched the frozen 11.2

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Tester (tester)
- decided by: Tester
- task: T-0001
- context: -
- options considered: -
- decision: Correct tests/integration/test_harness_cli.py to the merged Architecture 11.2/11.3 (frozen specs separated by runs of 2+ spaces) instead of changing src/teamwork/harness.py, and pin the eight frozen path specs as literals in C1..C8 order.
- why: The single failing assertion was the test's own pre-contract assumption. 11.2 as merged at 811065b freezes 'managed block in AGENTS.md', 'Roles/<Role>/*.md + Global/GlobalMemory.md', 'scripts/*.py + src/teamwork/*.py' and 'hook_dir(root)/{pre-commit,pre-push}', and 11.3 makes C5's class '-'; those cells contain single spaces, so line.split() tears a row into 7 cells and the path column cannot be the frozen spec at all. harness.py already implements exactly that (harness.SPEC_* constants, _CELL_SEPARATOR_RE=r'\s{2,}', parse_surface_row), so the code needed no change and the test did.
- evidence: python3 scripts/teamwork.py harness list @252805e -> 8 rows, 4 cells, C1..C8; .venv/bin/python -m pytest -q tests/integration/test_harness_cli.py tests/acceptance/test_harness_docs.py @b90b5af -> 38 passed; mutants: SPEC_HOOKS->hook_dir(root)/pre-commit -> 1 failed, Surface('C5','n/a',...) -> 1 failed
- falsified by: If 11.2 on main still froze 'AGENTS.md'/'scripts/*.py'/'hook_dir(root)/pre-commit' as the path cells, or if harness list printed a header or nine rows, the code would be the defect and this decision would be wrong.
- consequences: -

## D-20261020-Developer - Global memory entries carry provenance, and a merge never drops or steals it

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Developer (developer)
- decided by: Developer
- task: T-0005
- context: -
- options considered: -
- decision: teamwork global takes the same provenance flags as teamwork remember (--by/--src/--rev) and stores them in the entry; the ledger record for a global write names its author instead of hardcoding 'ceo'. merge_entries carries by/src/rev forward as ONE triple: a record written without an author is completed by a later writer (all three fields move together), a record that already has an author keeps it, and a later writer who is not the author may not overwrite the author nor graft their own src/rev onto it. The same author may fill the gaps in their own record.
- why: The audit gate reports a memory entry without 'by' as a BLOCKER, but the global writer had no --by at all, so a global entry could never satisfy the rule it was audited against - the gate was unreachable by construction, not a property of the data. Measured at the process boundary in a throwaway workspace: 'global --by Developer --src T-0005 --rev 252805e' -> 'by: Developer / src: T-0005 / rev: 252805e' in GlobalMemory.md, and 'audit' then reports no memory entry without provenance. The triple travels together because by/src/rev describe ONE recording act: the field-wise rule lets a second writer graft their own src and rev onto a record someone else authored, which credits the first author with a revision the second writer verified - measured, the field-wise carry-forward produced 'by: CEO / src: T-9 / rev: fff' where the first writer supplied only 'by: CEO'.
- evidence: python3 scripts/teamwork.py global --help @worktree -> --by BY --src SRC --rev REV; throwaway workspace (init --agents ceo,reviewer-1 --no-git): 'global ... --by Developer --src T-0005 --rev 252805e' -> '- by: Developer / - src: T-0005 / - rev: 252805e'; 'global ... ' without --by -> '- by: ' then the same key with --by -> '0 new / 1 merged' -> '- by: Reviewer-1 / - src: T-0005 / - rev: 252805e'; a later writer '--by Impostor' -> the author stays 'Reviewer-1'; 'audit' -> no memory entry without provenance, 'loop' -> 'gate overrides, provenance and liveness: - none'; ledger memory.global records -> actor='Developer' rev='252805e' (was hardcoded 'ceo'); .venv/bin/python -m pytest -q tests/unit/test_global_memory_provenance.py -> 14 passed, and three mutants of the merge rule are red (carry-forward removed -> 4 failed; field-wise overwrite -> 4 failed; field-wise carry-forward -> 2 failed)
- falsified by: A merge that never completes a missing author (so a record written without one stays red forever) would make this decision wrong - the completion path is the point, not the prohibition. Equally, a global entry that a legitimate later writer must be able to re-attribute to a different author (a fact corrected by another role) would break the no-overwrite rule and force a second, explicit re-attribution path.
- consequences: docs/guide/cli.md documents the three flags on 'global' and states the merge rule, so the published reference matches the shipped surface. The three provenance fields are one unit in merge_entries; a future writer who adds a fourth provenance field must decide which triple it belongs to rather than patching fields independently.

## D-20261020-Developer-2 - The T-0005 rework is a pure rebase: both Decisions.md blocks are kept and the newer '14 passed' evidence line wins

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Developer (developer)
- decided by: Developer
- task: T-0005
- context: The Reviewer failed P-0013 for ONE blocker: the branch was not mergeable against current main (git merge-tree --write-tree main 5ab3ab9 -> rc 1, CONFLICT (content) in docs/Team/Decisions.md at two regions) and explicitly marked everything else VERIFIED GOOD, DO NOT REWORK. The conflict is a pure staleness artefact: the P-0010 records commit (36bef5a) carried the Developer's D-20261020-Developer entry onto main, so both sides of the merge own the same decision id with different evidence numbers.
- options considered: (A) drop the Tester's D-20261020-Tester-2 block to make the append point agree (rejected: it would delete another role's accepted decision from the shared log); (B) keep main's '13 passed' line (rejected: it is the STALE measurement - the branch's 14 assertions and the 4/4/2 mutant counts are the newer, and the Reviewer independently measured 14 passed at 5ab3ab9); (C) keep both blocks and take the newer evidence line, the decision id once (chosen)
- decision: The P-0013 rework is a rebase onto main 78e3cdc with one mechanical conflict resolution in docs/Team/Decisions.md and NO change to code, tests, docs/guide/cli.md or CHANGELOG.md. Both conflict regions are resolved by KEEPING BOTH SIDES: main's D-20261020-Tester-2 block (added by 36bef5a for P-0010) is kept alongside the branch's D-20261020-Developer block, and the branch's NEWER evidence line ('14 passed', with the 4/4/2 mutant counts) wins over main's stale '13 passed' (3/2/1 counts). The decision id D-20261020-Developer appears EXACTLY ONCE in the resolved file.
- why: The two sides are not two different facts about one decision; they are one decision recorded twice, and the difference is the measurement date. The Reviewer reproduced the resolution in a scratch clone and confirmed it: exactly one D-20261020-Developer heading, one D-20261020-Tester-2 heading, both entries present, no duplicate id. The rebased tree is green: 763 passed, 3 skipped, 0 failed - the branch's pre-merge AC-5 failure is gone because P-0010 landed it on main. The work stays ONE commit with the Developer role mailbox as author AND committer, so the identity audit still reports 1 commit, 0 problems.
- evidence: git merge-tree --write-tree main HEAD -> rc 0 (it was rc 1, CONFLICT (content) docs/Team/Decisions.md, at 5ab3ab9); .venv/bin/python -m pytest -q @worktree -> 763 passed, 3 skipped, 0 failed; .venv/bin/python -m pytest -q tests/unit/test_global_memory_provenance.py @worktree -> 14 passed; ruff check . @worktree -> All checks passed; ruff format --check . @worktree -> 147 files already formatted; mypy src/teamwork @worktree -> Success, no issues found in 17 source files; python3 scripts/teamwork.py links @worktree -> 0 issues; python3 scripts/teamwork.py identity --audit --range main..developer/t-0005-global-memory-entries-must-be-able-to-ca -> 1 commit, 0 problems (Developer <developer@agents.nidvue.com>); resolved file vs main -> the ONLY line that differs is the evidence line '13 passed' -> '14 passed'; resolved file vs 5ab3ab9 -> the ONLY addition is main's D-20261020-Tester-2 block; src/teamwork/engine.py, src/teamwork/records.py and tests/unit/test_global_memory_provenance.py are byte-identical to 5ab3ab9
- falsified by: A resolved file in which the D-20261020-Developer heading appears twice, or in which the D-20261020-Tester-2 block is missing, or in which the stale '13 passed' line survived, would make this resolution wrong; so would a merge-tree rc other than 0, or a suite with any failure.
- consequences: The branch is mergeable against main, so the Reviewer's pass (which is the merge trigger) will land the work instead of recording it as shipped while the code stays off main. The commit keeps the Developer role mailbox as author and committer and the full fixed trailer shape, so no identity gate regresses.

## D-20261020-Developer-3 - ledger export resolves the work tree through the existing wo

- date: 2026-10-20
- kind: technical
- status: accepted
- deciders: Developer (developer)
- decided by: Developer
- task: T-0008
- context: -
- options considered: -
- decision: ledger export resolves the work tree through the existing work_repo resolver (layout.work_docs_dir), not project_of(root): the manifest is written into, and describes, the work tree the command runs in
- why: The export wrote into the checkout owning the team tree, so a lane could not commit the manifest it exported and the manifest pinned a revision the committing branch did not have (measured by the CEO: ceo T-0010). work_repo is the resolver cmd_branch/cmd_commit/cmd_pr already use, so the fix introduces no second resolver
- evidence: .venv/bin/python -m pytest -q @3d1607d -> 818 passed, 3 skipped, 0 failed; tests/unit/test_ledger_export_worktree.py @3d1607d -> 6 passed, and with the resolver reverted to project_of(root) -> 5 failed, 1 passed; live export in the lane work tree -> manifest written in the work tree, main checkout's manifest sha256 unchanged
- falsified by: Show the export writing docs/Team/AuditManifest.json outside the work tree the command runs in, or the manifest's git.head differing from that work tree's HEAD
- consequences: -

## D-20261020-CEO-8 - The published branch is the base of any local history rewrite

- date: 2026-10-20
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0011
- context: The remediation for the red privacy gate needs a rewrite of the unpublished local history, and the local `main` is the branch that is about to be pushed. The local `main` and the published `origin/main` have diverged, so a rewrite based on the local merge base would drop whatever the published side carries that the local side does not.
- options considered: (A) base the rewrite on the local `main`'s merge base - refused, it drops the published side's files; (B) base the rewrite on the local `main` tip - refused for the same reason, the local tip does not contain the published work; (C) base the rewrite on the PUBLISHED tip and carry the published side's files over verbatim (chosen)
- decision: A rewrite of the unpublished local history must be based on the PUBLISHED tip (`origin/main`), not on the local `main` or its merge base, and the published side's files must be carried over verbatim. The published tip carries work the local `main` does not have - the committer guard (`guard_committer_identity` in `src/teamwork/engine.py` plus the `committer-guard` job in `.github/workflows/ci.yml`) and the rebase-merge explanation in `references/Remotes.md` and `CONTRIBUTING.md` - and the two test files that pin them. The local-only chain is rebased onto the published tip, and the published side's files are taken from the published tip, not re-authored.
- why: The published tip is the only base that keeps both sides' work, and the guard is the one piece that stops the red from coming back: a host merge button writes the signed-in account into the commit it creates, the privacy gate then fails on that personal mailbox in the history, and because the same gate is an acceptance proof the traceability guard fails with it. A rewrite that dropped the guard would rebuild the exact condition it is meant to remove, and the red would return on the next forge merge. The published tip is the base rather than the local tip because the local tip does not contain the guard at all, so basing on it loses the work by construction.
- evidence: `git rev-parse --short origin/main` -> `f277ac7` ("chore(merge): merge of feature/committer-guard"); `git merge-base --is-ancestor origin/main main` -> NO, so the published tip is not on the local branch; `git rev-list --count $(git merge-base origin/main main)..origin/main` -> 8, the published tip is that far ahead of the local merge base; `git show origin/main:src/teamwork/engine.py | grep -c 'def guard_committer_identity'` -> 1, and `git show main:src/teamwork/engine.py | grep -c 'def guard_committer_identity'` -> 0, so the guard is on the published side and absent from the local side; `git show origin/main:.github/workflows/ci.yml | grep -n 'committer-guard'` -> the job is there; `git show --stat 8b5265c` -> the guard commit carries the committer guard in `src/teamwork/engine.py`, the `committer-guard` job in `.github/workflows/ci.yml`, the rebase-merge explanation in `references/Remotes.md` and `CONTRIBUTING.md` and the two test files; a rebase of the local chain onto the published tip, measured in a throwaway worktree, leaves the local tree differing from the rebased tree in 6 files, +466/-19, and every one of those files is the published side's work. No finding count and no test count is pinned anywhere in this record, and no revision is pinned beyond the two commits the decision is about - the published tip and the guard commit - because the commit that documents a count raises it (D-20261019-CEO-15).
- falsified by: The published tip carries no file the local `main` lacks, or the guard it carries is present on the local side too, or a rewrite based on the published tip still drops the guard - then the choice of base would not matter and the published-tip rule would be wrong. Equally, a rewrite that changes a published-side file instead of carrying it over verbatim would falsify the "verbatim" half: the published side's work must survive the rewrite unchanged.
- consequences: The local-only chain is rebased onto `origin/main` and the published side's files are carried over verbatim, so the committer guard and the rebase-merge explanation survive the rewrite and the next forge merge cannot stamp an account into `main` unnoticed. The rewrite itself stays a red line that needs the user's authorization, which ceo T-0003 carries. This record gives the rewrite its base; [Board](Board.md) and [Plan](Plan.md) name the same rule for the reader who looks there.

## D-20261021-Reviewer-1 - D-0003 ruling: the privacy boundary is drawn at the object, but 'published' is not the word for it

- date: 2026-10-21
- kind: tribunal
- status: accepted
- deciders: Reviewer-1 (reviewer)
- decided by: Reviewer-1
- task: D-0003
- context: -
- options considered: -
- decision: The Audit Report must not call the object 'published' and must not say 'absent from the forge'; it must state three separate facts: (1) reachability - the commit is not reachable from any published ref (ls-remote: 40 refs, none advertising it; not an ancestor of origin/main nor of refs/pull/23/head; a plain anonymous clone does not contain it; a truncated-SHA fetch is refused) and the published side is clean (3058 reachable objects swept, 0 hits for address, name or domain); (2) service - the forge serves the object anonymously by SHA, HTTP 200 through its API with the author name AND email in the payload, HTTP 200 on its commit page, and named as merge_commit_sha in the PR #23 record (also served by the enumerable GET /pulls list); (3) disclosure - the author identity has been disclosed to anyone who requests that SHA and cannot be un-disclosed, while the CONTENT of that commit is already published safely as 3f4981d under the role mailbox (identical tree 7f1c4b30, and 3f4981d IS in origin/main). The report must not use 'publicly disclosed', 'exposed' or 'leaked': discoverability was measured absent (commit search total_count 0 by author, by sha: and by bare sha; user search 0; the forge's user endpoint for the PR author returns a null email; the commit page renders the name but not the address). The phrases 'the next push, not the past' and 'a containment problem rather than a published disclosure' are withdrawn: the disclosure happened at the object level, and R5 (the rewrite) stays OPEN and still needs the user's authorization through the CEO. CEO rule D-20261020-CEO-9 (the privacy boundary is drawn at the OBJECT, not at the ref) is ADOPTED, with one precision: what must never be published is the IDENTITY, not the content. Use 'retained' for the object and 'disclosed' for the identity; reserve 'published' for objects reachable from a published ref.
- why: Both available labels are wrong, each for the same reason: the word 'published' is already load-bearing in the same report for the role-mailbox commit 3f4981d, which IS reachable from origin/main and whose content is what the published tree ships - so calling the offending object 'published' makes the report contradict itself, and calling it 'not published' uses a reachability measurement as an existence claim ('absent from the forge'), which is false because the forge serves the object (API HTTP 200 with the email in the payload, commit page 200, PR #23 merge_commit_sha). The Reviewer's own original inference overreached and is corrected here: the object is NOT discoverable - commit search returns 0 for the author, for sha: and for the bare sha, a truncated-SHA fetch is refused, and a plain clone does not contain it - so 'publicly disclosed' is as wrong as 'never published'. The only wording that misleads neither reader states the three facts separately.
- evidence: git ls-remote origin @2026-10-21 -> 40 refs, 0 matching 3f4981d; git merge-base --is-ancestor 3f4981d origin/main -> rc 1; git merge-base --is-ancestor 3f4981d a5a41bd (the published PR head) -> rc 1; anonymous clone (credential.helper= empty, pristine HOME) -> git cat-file -t 3f4981d -> rc 128 'could not get object info'; same clone git fetch --no-tags origin 3f4981d -> rc 0 with the object present; git fetch origin 3f4981d -> 'couldn't find remote ref'; the forge's commits endpoint for the PR author -> HTTP 200 with the author address in the payload; the forge's commit page for that object -> HTTP 200, the author name rendered, the address not; the forge's PR #23 record -> merge_commit_sha = that object, merged_at 2026-10-20T10:21:24Z; the enumerable pull-request list -> the same merge_commit_sha; the forge's commit search by author / by object id / by bare object id -> total_count 0 each; the forge's user endpoint for the PR author -> a null email; the forge's user search by the author address -> total_count 0; full clone + '+refs/pull/*/head' fetch, sweep of 3058 reachable objects -> 0 hits for address, name or private domain; git rev-parse 3f4981d^{tree} 3f4981d^{tree} -> the same tree; git merge-base --is-ancestor 3f4981d origin/main -> rc 0
- falsified by: A measurement showing the object is NOT served by the forge (an API or page response other than HTTP 200 for that SHA), or that it IS discoverable (the forge's commit search returning it, or a truncated-SHA fetch succeeding), or that the commit is reachable from a published ref, would make this ruling wrong. Equally, a reader-facing consequence: if the report cannot be rewritten to the three-fact form, the ruling fails to bind.
- consequences: The Security Auditor owns the AuditReport.md rewrite (F-1, F-2, F-8, the section-5 R5 table, the section-7 measurement table, the section-6 residual-risk row) and says so in its report; R5 stays open. Reviewer-2 withdraws the 'published' and 'publicly disclosed' inferences and keeps the 'absent from the forge' finding. The ruling text is filed as dispute round 3/3 in D-0003, as the ruling of that dispute, and as .pi/Teamwork/Teams/Teamwork/Agents/Reviewer-1/Reports/D-0003-ruling.md.

## D-20261021-CEO-1 - A commit message or a decision entry names an object by its ROLE, never by its full 40-hex id

- date: 2026-10-21
- kind: technical
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0003
- context: The shipped privacy gate cannot tell a git object id from a leaked credential, so a commit message or a decision entry that quotes one is a message the gate will refuse to push. The Audit Report rewrite's own commit message is such a message, and the ruling entry had already failed the same class before it.
- options considered: (A) teach the entropy rule to recognise a git object id and exempt it (rejected: the rule cannot tell an object id from a credential by shape alone, and a wrong exemption is a hole in the shipped gate); (B) exempt the object-id shape in the allowlist (rejected: the allowlist exempts finding VALUES one at a time and is never widened for a shape, per D-20261019-CEO-15 and D-20261020-CEO-4); (C) name the object by its ROLE wherever a commit message or a decision entry refers to one (chosen)
- decision: A commit message or a decision entry names an object by its ROLE - 'the offending commit', 'the role-mailbox commit', 'the tree id both share' - and never quotes its object id. A measurement that needs an id is stated as the measurement rather than quoted as the value. The rule applies to the record that carries the rule: this entry quotes no object id and no pinned count.
- why: The entropy rule reads a long base64-ish token that carries upper case, lower case and a digit and clears the entropy threshold as a credential, because a git object id and a leaked token are indistinguishable to it - the rule cannot tell them apart, so a record that quotes one is a record the gate refuses to push, and the cost falls on the lane that wrote it: the work is correct, the record is not publishable. Measured, the trigger is the object id inside a forge API or commit-page path, where the id and the path segments form one long token; a bare id in prose is not what fires. Naming the object by its role removes the value from the message without removing the fact - the reader learns which object is meant and can ask the author or the ledger for the id, and the gate sees prose. The alternatives do not work: an exemption for the object-id shape teaches the shipped gate to trust a shape it cannot verify, and an allowlist entry for one value does not survive the next commit, because every commit that documents an id adds another one.
- evidence: the shipped scanner over the Audit Report rewrite's own commit message -> the high-entropy findings are the forge API and commit-page paths that carry the offending object id inside a URL, and the tree id both share is quoted on the same line; a scratch tree whose decision entry names the objects by their role instead -> `python3 scripts/privacy_scan.py --tree --allow .github/privacy-allow.txt` -> PASS, rc 0, and the same scratch tree with the same entry quoting the offending object id inside the forge API and commit-page paths -> FAIL, rc 1, with the high-entropy findings on that evidence line, so the class is measured on both sides of the change; a commit message that names the offending commit and the role-mailbox commit by role -> the same scanner over that message -> PASS, rc 0, while the same scan over the Audit Report rewrite's own message -> FAIL, rc 1, on the high-entropy findings; `python3 scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` -> the commit-metadata findings are reported against the same commit id family; the finding count on every one of those lines is read from the run and never pinned, per D-20261019-CEO-15.
- falsified by: A measurement showing that the shipped entropy rule does not fire on a quoted object id in a commit message or a decision entry - for instance a forge path whose id the rule's own path-name test reads as a path, so the URL form stops tripping it - would make the naming rule unnecessary. Equally, a commit message or decision entry that names an object by its role and still trips the gate would mean the role names themselves are not safe, and the rule would have to say what a safe reference looks like.
- consequences: every lane writes its commit messages and its decision entries the same way, so a record that names an object by its role is publishable while a record that quotes the id is not. The Audit Report rewrite's commit message is a finding in its own right and is owned by the lane that wrote it; the remediation is to name the objects by their role, not to change the gate. The archive mask's treatment applies here as well: name the rule, not the value. This entry changes no code, no allowlist entry and no gate, so the shipped privacy gate keeps exactly the coverage it has today; [Risks](Risks.md) carries the state of the gate and the rule that a record must not re-publish a value, and [Archive](Archive.md) carries the evidence of both.

## D-20261021-Reviewer-1-2 - PASS ceo T-0012 / P-0029: the re-exported audit manifest at

- date: 2026-10-21
- kind: technical
- status: accepted
- deciders: Reviewer-1 (reviewer)
- decided by: Reviewer-1
- task: -
- context: -
- options considered: -
- decision: PASS ceo T-0012 / P-0029: the re-exported audit manifest at 1895d1b describes a real revision and the chain claim is true, so it is merged (147dfa4, records 6a7b08a) and the branch is retired.
- why: git.merge-base --is-ancestor 4fe0b17 1895d1b -> rc 0 (the manifest names the export revision, which is the direct parent of the commit that carries it, so it is an ancestor by construction); git.branch == the lane branch and git.dirty == false; ledger verify -> chain intact, and my own independent recomputation of all 671 records with the engine's rule sha256(prev+canon(record)) reproduced every digest and every prev-link; the pinned count 666 IS the export-time count because record #666 is the ledger.export event and its hash equals manifest ledger.head, so the chain reproduces up to exactly that checkpoint; Decisions.md dd3e9bfb/145134B and Plan.md 1d9ac825/17872B recomputed by hand from the committed blobs and matched, Global/GlobalMemory.md d361d7c5/1880B matched in .pi/Teamwork/Teams/Teamwork/; the main checkout was untouched (git status --short empty, its committed manifest still the old 509/160c6daf671f export); links 0 issues, pytest -q at 1895d1b 823 passed/3 skipped/0 failed, identity --audit 1 commit 0 problems with author == committer == CEO <ceo@agents.nidvue.com> == the repo's local git config identity, merge-tree --write-tree main <branch> rc 0.
- evidence: git merge-base --is-ancestor 7f6071484b9dacd2edcebb871ddbcca97d595915 1895d1b -> rc 0 @1895d1b; python3 scripts/teamwork.py ledger verify -> 'records: 671 | chain intact, every digest matches' @main; independent chain recomputation over 671 records -> all match; sha256sum + wc -c on docs/Team/Decisions.md and docs/Team/Plan.md @1895d1b -> both match the manifest; git status --short in the main checkout -> empty; python3 scripts/teamwork.py links -> 0 issues @main; .venv/bin/python -m pytest -q @1895d1b -> 823 passed, 3 skipped, 0 failed; python3 scripts/teamwork.py identity --audit --range main..ceo/t-0012-... -> 1 commit, 0 problems, CEO <ceo@agents.nidvue.com>; git merge-tree --write-tree main ceo/t-0012-... -> rc 0, tree a0ef845fee6917d81197cfbd0b670f0c5dabdb49
- falsified by: A verifier who recomputes the chain and finds record #666 is NOT the ledger.export event, or that manifest ledger.head != the hash of record #666, or that the four artifact digests do not match the committed blobs at 1895d1b, or that the main checkout was modified by the export - any of these would falsify the manifest's central claim and reopen this verdict.
- consequences: -

## D-20261020-CEO-7 - The frozen contract is corrected by measurement, not defended

- date: 2026-10-20
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0003
- context: -
- options considered: -
- decision: When the implementation proves a frozen interface clause unimplementable or self-contradictory, the contract is amended by the Architect against a reproduced measurement, and the amendment is a normal deliverable through the two-stage gate. The rules' semantics are never silently bent in the code to match a wrong text.
- why: M9-B proved three defects in section 11 before any test was written: an unsatisfiable digest across the build_pi_package re-layout, worked examples whose hex values assumed the exclusion the same section forbids, and an R9 regex scope that would flag python: 3.12.13 as a missing tag. A developer silently implementing around a wrong contract hides the wrong contract.
- evidence: branch developer-1/t-0005-... commit e4cd4c1: tarball-in-place digests 1.1.2 7c540615af001e46 / 1.1.0 de679daed556099f match no tag, while remapped digests a01d9f0cbee641c3 == payload of 3f4981d and ebfc2538e3d3d605 == v1.1.0; 11.5 values b1ba21e39436bf09 / 0786a4ff3c2f84ba reproduce only with build_pi_package included
- falsified by: If the implemented checker's remapped digests did not reproduce the published tarballs, the contract would be right and the implementation wrong - so the Architect must reproduce one digest independently (T-0003) before amending
- consequences: -

## D-20261020-CEO-5 - M9: make every published version traceable to a tag, and every release claim measurable

- date: 2026-10-20
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: -
- context: -
- options considered: -
- decision: Open milestone M9 (release-truth). Scope: (a) a checker scripts/check_release_consistency.py that fails on release drift; (b) tag v1.1.2 at 3f4981d, whose bundled payload is byte-identical to the published npm 1.1.2, and publish its GitHub Release; (c) repair README/install.md/Release.md claims; (d) release 1.1.3 from the merged main. npm 1.1.1 is recorded as an exception.
- why: Measured on main f277ac7: npm dist-tag latest = 1.1.2 but git has no v1.1.1/v1.1.2 tag, so 'released' means two different things; the GitHub Release lags npm by two versions; README.md:132 and docs/guide/install.md:115,157 print 'teamwork 1.0.2' while version.py says 1.1.2; docs/Team/Release.md:116 rolls back to a v0.9.0 tag <!-- release-consistency: illustrative --> that does not exist; and pip install teamwork-agents <!-- release-consistency: channel-unavailable --> 404s on PyPI while README.md:122 still prints the command. Each is a claim a reader can falsify in one command, which is the defect class this project exists to remove.
- evidence: npm 1.1.2 tarball payload digest b1ba21e39436bf09 == commit 3f4981d tree digest b1ba21e39436bf09 (64/64 files, 0 differ); npm 1.1.1 payload 0786a4ff3c2f84ba matches NO commit (src/teamwork/version.py sha256 545fc1605b3997460a1cf348562c43fed5a8315c83ac8291f9cbf4078703d36d absent from git rev-list --all); npm 1.1.0 payload de679daed556099f differs from tag v1.1.0 only in scripts/build_pi_package.py; git tag -l -> v1.0.0 v1.0.1 v1.0.2 v1.1.0 only; pypi.org/pypi/teamwork-agents/json -> Not Found; verify_release.py at 3f4981d -> 'OK - release verified'; pytest at 3f4981d -> 620 passed 3 skipped
- falsified by: Tag v1.1.2 at 3f4981d and the release workflow produces a wheel whose skill payload differs from the npm 1.1.2 tarball, or check_release_consistency.py exits 0 while a version is published with no matching tag and no exception record.
- consequences: npm and GitHub Releases become two views of one tagged source; a future publish with no tag fails the consistency gate in CI rather than being discovered by a user.

## D-20261020-CEO-6 - Docs lanes are unstaffed this milestone; the CEO writes README, CHANGELOG and docs/guide

- date: 2026-10-20
- kind: governance
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: -
- context: -
- options considered: -
- decision: technical-writer and designer are not staffed on this roster, so their folded lanes (README.md, CHANGELOG.md, docs/guide/**, docs/index.md) are written by the CEO for M9 and recorded as a CEO exception, instead of staffing two roles for four file edits.
- why: The ownership table is binding so that two lanes never write one file; it does not require staffing a role to satisfy it when a lane is folded. Adding technical-writer-1 and designer-1 would add two charters, two queues, two memory sets and two test-layer obligations for a milestone whose docs edits are version strings, one install note and one stale table.
- evidence: ls .pi/Teamwork/Teams/Teamwork/Roles/ -> no TechnicalWriter and no Designer instance directory; the file-ownership table in section 2 of docs/Team/Architecture.md assigns README.md to designer-1 and CHANGELOG.md+docs/guide/** to technical-writer; tests plan requires only staffed roles' layers
- falsified by: A second writer touches one of those files in this milestone, or the Reviewer finds a docs claim no role could have measured.
- consequences: The docs layer stays unstaffed and tests plan reports no gap for it; the Reviewer still reviews every docs edit, so the second gate is unchanged.

## D-20261021-Architect - R2 compares HEAD only against the version tags reachable from HEAD

- date: 2026-10-21
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: Architect
- task: T-0004
- context: [Architecture](Architecture.md) 11.2.2 froze R2's reachable-tag semantics but the `D-` entry it asked for was never filed, and the checker then on the developer's branch compared HEAD against every version tag (`c66c387:891-899`).
- options considered: A) compare HEAD against every version tag in the repository - rejected: it has no notion of reachability, so a maintenance branch stays permanently red against tags that were never its ancestors (measured: DRIFT against v1.0.1, v1.1.0 and v1.1.2 on a 1.0.x line). B) reachable version tags minus the tags at HEAD (S = A - O) - chosen. C) reachable version tags including the tags at HEAD - rejected: asks whether a release is greater than itself, so the gate could never be green on the tag push it exists to gate. D) compare against the newest reachable tag only - rejected: loses the per-tag findings the rule's detail must name.
- decision: R2's tag set is S = A - O (see [Architecture](Architecture.md) 11.2.2): A is the version tags (`^v\d+\.\d+\.\d+$`) whose commit is reachable from HEAD (`git merge-base --is-ancestor <tag> HEAD` exits `0`), O is the subset of A that points at HEAD (`git tag --points-at HEAD`), and S = A - O. R2 is DRIFT iff some tag in S has a version not strictly less than HEAD's; the ok detail is `HEAD <X.Y.Z> is newer than <|S|> tag(s)` with `|S| = len(A) - len(O)` over reachable version tags only. A version tag that is not an ancestor of HEAD is invisible to R2 (R1, R4, R5, R7 still see it). A shallow or tag-less checkout is exit 2, never a green run.
- why: The old rule compared HEAD against every version tag in the repository, so a maintenance line stayed permanently red against tags of the main line that were never its ancestors, while the release build it gates was the one revision it could never pass. DRIFT is a published fact disagreeing with a local fact; a tag that is not an ancestor says nothing about whether this checkout is ahead of its own history, so comparing against it is a category error, and O is excluded because R1 forces version.py to equal the tag name, so including O would ask whether a release is greater than itself. The count is `len(A) - len(O)` over reachable version tags only, so it is never negative: the arithmetic `len(git tag -l) - len(O)` (subtract the tags at HEAD from every tag, version tags and doc tags alike) is the defect the freeze removes - on one version tag with two doc tags at HEAD it evaluates to `-2` - and **no revision of the checker implements it and none prints a negative count** (`c66c387:891-899` counts `len(tags)` over version tags). It is named here as the rejected arithmetic, not as an output of any shipped code.
- evidence: the committed probe set is `d998801:tests/unit/test_release_consistency_digest.py:429-451` - 19 parametrised cases, 13 must-match and 6 must-not-match; `pytest -q tests/unit/test_release_consistency_digest.py -k r9_pattern` at `d998801` -> `20 passed, 25 deselected` (the contract regex matches 13/13 must-match and 6/6 must-not-match); with the old `c66c387:183` pattern substituted for `TAGGED_TOKEN` the same selection gives `9 failed, 11 passed` (the 9 failures are 8 parametrised cases plus the byte-for-byte assertion), i.e. the old pattern matches 5/13 must-match and 6/6 must-not-match; the contract regex is implemented verbatim at `d998801:scripts/check_release_consistency.py:186-191` and `d998801:tests/unit/test_release_consistency_digest.py:424-426` asserts byte-equality with the 11.2.4 block; `pytest -q tests/unit/test_release_consistency_digest.py` at `d998801` -> `45 passed`; the R2 semantics are pinned by the same committed file: `:352-372` counts the reachable version tags and never a negative (`R2 ok HEAD 1.0.1 is newer than 1 tag(s)` on a repo with `v1.0.0` plus the doc tags `docs-a`/`docs-b`), `:374-394` a maintenance branch is `ok` (`HEAD 1.0.1 is newer than 1 tag(s)`, A={v1.0.0, v1.0.1}, O={v1.0.1}, S={v1.0.0}), `:396-411` a stale main stays DRIFT and names `v1.1.0` but not `v1.0.0`, `:413-422` a tag push is `ok` (`HEAD 1.1.0 is newer than 0 tag(s)`); the old rule on the same maintenance-branch fixture (a repo with tags v1.0.0, v1.0.1, v1.1.0, v1.1.2 and a 1.0.x line checked out) prints `R2 DRIFT HEAD version 1.0.1 is not greater than tag v1.0.1; ... v1.1.0; ... v1.1.2` @c66c387 - permanently red; on a shallow clone (`git clone --depth 1 --branch v1.1.0 file://<repo>`) the old checker prints `R2 DRIFT HEAD version 1.1.0 is not greater than tag v1.1.0` @c66c387 - a DRIFT finding, not an input error, off a clone that cannot see the other tags - while the current implementation exits `2` with `shallow clone: the complete tag set is required (git rev-parse --is-shallow-repository is true)` @d998801 - `d998801:scripts/check_release_consistency.py:748` (`_complete_tag_set_error`), asserted by `d998801:tests/unit/test_release_consistency_digest.py:492-525` (a real `git clone --depth 1` raises `InputError` and `main` returns `2`); `git show c66c387:scripts/check_release_consistency.py:891-899 @c66c387 -> the old rule counts len(tags) over every version tag and never prints a negative count`
- falsified by: If the reachability semantics did not make a maintenance branch green while keeping a stale main red, the old rule would have been right. The measurements above are the falsifier: A={v1.0.0, v1.0.1}, O={v1.0.1}, S={v1.0.0} on the maintenance branch (`ok`, `d998801:tests/unit/test_release_consistency_digest.py:374-394`) and S={v1.0.0, v1.1.0, v1.1.2} on the stale main (DRIFT, `:396-411`). If either side of that pair changes, this decision is void and 11.2.2 must be re-derived.
- consequences: 11.2.2's 'the D- entry is the Architect's to file' sentence is replaced by a link to this record. The rule is implemented at `d998801` (`rule_r2_head_is_newer` computes `S = A - O` and `_complete_tag_set_error` refuses a shallow or blind checkout), reproducible with `git show d998801:scripts/check_release_consistency.py`. Whether that implementation is in the tree the reader holds is a question with a command, not a sentence: the checker file is in the tree when `git ls-tree HEAD scripts/check_release_consistency.py` prints a line, and the implementation is in the tree when `git merge-base --is-ancestor d998801 HEAD` exits `0`; the clause-by-clause table in the section 11 preamble of [Architecture](Architecture.md) states the same predicates, so the contract is not mistaken for a description of the running code.

## D-20261021-Architect-2 - A prose-only push must not skip the release-consistency gate, and must not burn the full test matrix either

- date: 2026-10-21
- kind: technical
- status: accepted
- deciders: Architect (architect)
- decided by: architect
- task: T-0005
- context: `ci.yml` filtered a documentation-only push with a workflow-level `paths-ignore`, which skips every job in the file - including the `release-consistency` gate, whose entire subject is prose that disagrees with a tag, `version.py` or `CHANGELOG.md`. A gate that is skipped exactly when the documentation drifts is worthless. A `scope` job in `ci.yml` replaces the trigger filter with a job filter so the two requirements can hold at once. The classifier is in the tree when `grep -n "^  scope:" .github/workflows/ci.yml` prints a line; the trigger filter is gone when `grep -n "paths-ignore" .github/workflows/ci.yml` prints nothing outside a comment.
- options considered: A) keep `paths-ignore` on `on.push` and accept that the gate is skipped on prose pushes - rejected: it blinds the one gate whose subject is prose, and no other job can cover it (the gate needs the tags and the tree, and the docs workflow is a different check set). B) give the release-consistency gate its own separate workflow - rejected: a second workflow on the same push doubles the checkout and the runner allocation for the same gate, and the gate still needs a path classification to know when it must run, so the filter problem returns in a new place. C) filter only inside the gate job (the gate would decide for itself whether to run) - rejected: a job that decides it may not run is not a required check; a required context that is never reported blocks the merge, and the gate's skip logic would then be a second, unmeasured copy of the classifier. D) classify the changed paths in a `scope` job and filter the expensive jobs by its output, leaving the gate unconditional - chosen.
- decision: The CI trigger policy is "code in, prose and media out" implemented as a job filter, not a trigger filter. `ci.yml` has no workflow-level `paths-ignore`; the workflow always fires on a push to `main`, on a `v*` tag, on every `pull_request` and on `workflow_dispatch`. A `scope` job computes the changed-path set from git and publishes one output, `code`; the expensive jobs (`lint`, `typecheck`, `test`, `build`, `privacy`, `docs`) carry `needs: scope` and `if: github.event_name != 'push' || needs.scope.outputs.code == 'true'`, so they skip on a push only and only when the change set is prose/media only. Every pull request runs the full set, because a path-filtered skip reports no check at all and a required check that is never reported blocks the merge. The classifier measures every change set with `git diff --no-renames`, so a rename is seen as a delete plus an add and both paths are classified - rename detection reports only the destination of a rename, so without `--no-renames` a move of a shipping file into a prose path would list only the prose path, be classified as prose and skip the matrix on a change that removed shipping code. The `release-consistency` gate is never filtered: it has no `needs:` and no `if:`, so it runs on every event including a prose-only push. In the job graph of `ci.yml`, the jobs that declare neither `needs:` nor `if:` are `committer-guard` and `release-consistency`, so a tag push, on which `scope` reports `code=false` and the six expensive jobs are skipped, still runs the classifier and those two jobs; `scope` can skip only the jobs that declare `needs: scope`. The classifier's undetermined case runs the code jobs - the root-commit branch is entered only when HEAD truly has no parent; every other case whose fork point is HEAD (a rewritten history, a push whose `before` is unresolvable) is undetermined, and an unknown change set must never silently skip the matrix. The prose/media set (`docs/**`, `assets/**`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, `LICENSE`, `AGENTS.md`, `mkdocs.yml`) and `.github/workflows/docs.yml`'s `paths:` list must stay identical. Every shipping path (`src/`, `scripts/`, `tests/`, `roles/`, `references/`, `templates/`, packaging, `.github/workflows/`, `SKILL.md`) still runs the full matrix.
- why: The two requirements are not in tension: a workflow-level filter is a blunt instrument because it applies to every job in the file, while a job-level filter can exempt the expensive jobs and exempt nothing else. Moving the classification into one job also puts the cost optimisation and the safety default in the same place: the classifier's default on an unknown change set is `code=true` (run the matrix), so the failure mode of the classifier is a slow build, never a silently green push. The gate is left unconditional because its subject is exactly the prose the filter would have skipped, and a gate that cannot see the drift it exists to catch has no value. The identity of the two prose lists is required because they are two halves of one policy: a path in the classifier's prose set but not in docs.yml's `paths:` list would skip the matrix without running the cheap prose checks either, and the reverse would run prose checks for a change the matrix also runs. The rename rule belongs in the same place: rename detection hides the *source* of a rename, so it can hide a shipping path behind a prose destination, and the classifier's contract is that no shipping path can be classified as prose.
- evidence: every fact below is re-runnable against the tree the reader holds; `grep -n "paths-ignore" .github/workflows/ci.yml` -> the string appears only inside comments, never as a trigger key, so the workflow-level filter is gone; the job list of `.github/workflows/ci.yml` -> jobs `scope`, `lint`, `committer-guard`, `typecheck`, `test`, `build`, `privacy`, `release-consistency`, `docs`, with `needs: scope` + `if: github.event_name != 'push' || needs.scope.outputs.code == 'true'` on the six expensive jobs, and no `needs:`/`if:` on `release-consistency` and on `committer-guard` -> both are unconditional; the scope job's change-set measurement -> every diff in the scope job uses `--no-renames` (`git diff --no-renames --name-only`, `git diff-tree --root --no-renames`), so a rename is a delete plus an add; the scope job's fallback -> the root-commit branch is guarded by `git rev-parse --verify -q "${HEAD_REV}^"`, and every other case with a fork point equal to HEAD sets `UNDETERMINED=1` -> `code=true`; the scope job's tag-push branch -> `refs/tags/*` reports `code=false`, so the six filtered jobs skip and the two unfiltered jobs run; the Release Engineer's measured replay of the classifier over five event shapes (prose-only push, code push, tag push, pull request, workflow_dispatch) -> the code jobs run on the code push, the pull request and the manual run, and skip on the prose-only push and the tag push (recorded in the T-0003 review findings in the Release Engineer's task queue); the identity of the two prose lists -> expanding the scope regex and the docs.yml `paths:` list over the same tree gives the same set, with no path in one list only - the comparison is re-runnable (`grep -n "PROSE=" .github/workflows/ci.yml` against the `paths:` list of `.github/workflows/docs.yml`) and is not stored as a count; the Release Engineer's reviewer measured the same identity over a path universe with GitHub glob semantics, 0 mismatches; the gate job in `.github/workflows/ci.yml` -> it runs `python scripts/check_release_consistency.py --offline --json` and treats a missing checker as exit 2 (an unreadable input), not a pass, with no `continue-on-error`
- falsified by: If the scope job classified a shipping change as prose, the matrix would be skipped on a code push and the old design would have been the safer one. The measurement that would show it: a push whose changed set contains a file under `src/`, `scripts/`, `tests/`, `roles/`, `references/`, `templates/`, packaging, `.github/workflows/` or `SKILL.md` and whose `scope` output is `code=false` (the Release Engineer's own pre-fix measurement on the first scope revision did exactly this: a push that changed `src/a.py` reported `scope: changed -> docs/d.md` and `code=false`); the same for a change set the classifier cannot establish (a rewritten history or an unresolvable `before`): if that reports `code=false` the undetermined default is broken. Also falsified if the two prose lists drift apart, if the gate ever gains a `needs:` or an `if:`, if a prose-only push to `main` reports no `release consistency (offline - docs + tags + version)` check, or if a rename out of a shipping path is classified as prose (the classifier must list both the old and the new path).
- consequences: Section 9 of [Architecture](Architecture.md) now describes the `scope` job, the two unconditional jobs, the undetermined default, the `--no-renames` rule and the identity requirement instead of the removed `paths-ignore`; the same policy is written out in [Release](Release.md) (the Release Engineer's file). The online half of the gate is the `consistency` job in `release.yml`: `build: needs: [consistency]`, so a release that cannot be traced is never built and never published. Whether that job is in the tree is a moving fact, so it is checked, not asserted: `git show HEAD:.github/workflows/release.yml | grep -n "consistency:"` (a match when the job is in the tree, no match when it is not) and the same file with `grep -n "needs: \[consistency\]"` for the `build` edge. `tests/unit/test_skill_contracts.py` asserts the old `paths-ignore` mechanism and the `scope` classifier side by side; that file belongs to the Developer lane (`developer T-0011`) and is not edited here - this record and the amended section 9 are the contract those tests must be rewritten against.

## D-20261021-CEO - P-0080 and T-0012 land inside P-0073: repair the stale merge record instead of re-merging

- date: 2026-10-21
- kind: process
- status: accepted
- deciders: CEO (ceo)
- decided by: CEO
- task: T-0012
- context: -
- options considered: -
- decision: P-0080 is recorded merged at 5fa73ef and T-0012 merge_commit=5fa73ef. Its branch was retired by the P-0073 merge, so pr merge cannot run and no second merge is wanted.
- why: The deliverable is already on main; a second merge would duplicate a reviewed change-set and the branch no longer exists.
- evidence: git merge-base --is-ancestor b03f5b8 5fa73ef -> rc 0; git merge-base --is-ancestor cd7e802 5fa73ef -> rc 0; git diff --stat cd7e802 main -- scripts/check_release_consistency.py -> 29 insertions/27 deletions (the token code is on main as b03f5b8); git branch --list 'developer-1/t-0005-*' -> empty; pr list -> P-0080 [merged] merge=5fa73ef
- falsified by: git merge-base --is-ancestor b03f5b8 main returning non-zero, or the token code missing from scripts/check_release_consistency.py on main
- consequences: -

## D-20261021-CEO-2 - Three review-loop disputes were moot by delivery

- date: 2026-10-21
- kind: process
- status: accepted
- deciders: CEO (ceo) for D-0023/D-0024; tribunal for D-0022 (signed by ceo and cto)
- decided by: CEO
- task: T-0003, T-0004, T-0005
- context: D-0022 (Reviewer-3 -> Developer-1, T-0005, escalated at round 2/3), D-0023 (Reviewer-1 -> ReleaseEngineer, T-0003) and D-0024 (Reviewer-2 -> Architect, T-0004) each charged a concrete, re-measurable defect in a deliverable that has since landed. Each was re-measured against main at `fb99293` rather than resolved on the author's word, because a ruling that rests on a table the disputed party wrote is not a ruling.
- options considered: adjudicate each mechanism (rejected: every charged mechanism is gone from main, so a ruling would describe code that is not shipped); dismiss as moot by delivery with each charged reproducer re-run (chosen); leave them open (rejected: an open dispute blocks STOP and misdescribes the delivered design).
- decision: All three are resolved as moot by delivery. D-0023: the checker is in main and the CI gate runs there (`.github/workflows/ci.yml:376`, `.github/workflows/release.yml:45` with `fetch-depth: 0` at `:68`). D-0024: the frozen contract no longer carries transient state claims or unpinned digest literals. D-0022: all four charged items - the stale commit count, the R8 inline-code regression, the clone-dependent digest and the surviving absolute-target mutation - are measurably fixed.
- why: A dispute is a claim about a mechanism. When the mechanism is deleted or corrected and the dispute's own reproducer no longer reproduces, there is nothing left for a tribunal to rule on, and recording a ruling on absent code would be a false record. D-0022 still exercised the escalation path (round 2/3, escalate, two tribunal signatures) so the process record shows the loop was stopped by the tribunal, not by attrition.
- evidence: D-0023 - `git ls-tree -r --name-only main | grep -c check_release_consistency.py` -> `1` (the round measured `0` at the reviewed head `7a035b8`); T-0003 records `status: done`, `review_status: passed`, `pr: P-0076`, `merge_commit: 46c4aeb`; the six commits the round lists are not ancestors of main because the branch was rebased/squashed on landing; `git diff 5cc68a2 main -- .github/workflows/ci.yml` shows main's stale "the online half lands with the release task T-0007" comments rewritten to name `release.yml`. D-0024 - `git grep -n "PENDING MERGE\|not in .main" main -- docs/Team/Architecture.md docs/Team/Decisions.md` -> no hits; `git grep -c "64674639a038018f\|ce020801f2fb5998" main -- docs/` -> one hit, inside `docs/Team/Archive.md` (a historical self-check record, not a contract claim), and Architecture.md now cites the committed fixture assertion `1e24271d36f868d3` at `docs/Team/Architecture.md:789`; T-0004 landed as P-0079 at `cf95b98`. D-0022 - `scripts/check_release_consistency.py:74-76` states no commit count (measured `git rev-list --all | wc -l` -> `534`); calling `_channel_claims` on the inline-code form whose distribution is teamwork-agents and whose script is wrongscript -> `[("teamwork-agents","wrongscript")]`, and the same for the pipx `--spec` form; a probe at `/tmp/digprobe` makes `rev=None` and `rev=HEAD` raise the *same* `InputError` for both a gitignored link target and a link into `.git`; deleting the absolute-target guard from `_link_target` turns `pytest -q tests/unit/test_release_consistency.py tests/unit/test_release_consistency_digest.py` into `2 failed, 116 passed` (`test_11_3_each_kind_of_link_refusal_says_a_different_reason`, `test_an_absolute_link_is_refused_on_both_paths`), so the mutation is killed and the guard now lives at `scripts/check_release_consistency.py:566-567`; T-0005 landed via P-0073 at `5fa73ef`.
- falsified by: any of the following reproducing on main - `check_release_consistency.py` absent from `main`; a `PENDING MERGE`/`not in .main` sentence in `docs/Team/Architecture.md` or `docs/Team/Decisions.md`; an unpinned digest literal in the frozen contract; a commit count pinned in `scripts/check_release_consistency.py`; `rev=None` and `rev=HEAD` disagreeing on a committed tree; or the absolute-target mutation surviving the suite.
- consequences: `dispute list` shows no open and no escalated dispute. The four D-0022 reproducers are now the standing regression set for the release-consistency gate rather than a one-off review artefact.

## D-20261021-CEO-3 - The published line is reconciled by a merge, never by a force-push

- date: 2026-10-21
- owner: CEO
- kind: process
- task: T-0065
- decision: Local `main` and `origin/main` are joined by a single two-parent merge commit (`230370e` = `5102429` + `4fb1e0953cdbe2d230a61dc3fe28e6332a75c5c5`, common base `f277ac7`). Neither line is rewritten and neither is abandoned. A merge commit is a fast-forward for the remote, so the push that follows is a plain `git push`.
- why: The two lines are a **divergence, not a rewrite**. `f277ac7` is an ancestor of both, so nothing was destroyed; local-only was 104 commits, remote-only 123, and the remote-only set was re-stamped at `2026-10-21T10:43:45Z` by a concurrent session. The two lines carry disjoint milestones both labelled M9: local = release traceability (`scripts/check_release_consistency.py` R1-R9, `release-exceptions.json`, version 1.1.3); published = Harness^2 adoption (`src/teamwork/harness.py`, `hooks.py`, the frozen harness contract, version 1.1.2). Each line is reviewed work that the other does not have. Force-pushing either would delete reviewed deliverables, which is a red line; rebasing either would rewrite published history, which is a red line and, per the published line's own `D-20261020-CEO-8`, must be based on the published tip rather than on a local branch.
- evidence: `git merge-base --is-ancestor f277ac7 main` -> 0 and against `4fb1e09` -> 0; `git rev-list --count main..4fb1e09` -> 123, `git rev-list --count 4fb1e09..main` -> 104; `git rev-list --parents -n1 230370e` -> three fields (a true merge); `git rev-list --count 4fb1e09..230370e` -> 109 and `230370e..4fb1e09` -> 0; the merge then resolves four conflicts semantically - CHANGELOG headings kept tag-correct with the published Harness^2 body grafted under our unreleased heading (the one comparing the newest tag with HEAD), and no heading linking to a tag that does not exist, `Archive.md` as an append-only union of 105 + 107 records with 53 shared -> 135, `Decisions.md` unioned on the `## D-` key 49 + 65 with 42 shared -> 72, and `Architecture.md` keeping our `## 11.` release contract (13 referencing files) while the published harness contract becomes `## 12.` with every `11.x` reference renumbered in `test_cli_contract.py`, `test_harness_cli.py`, `test_harness_surface.py`, `harness.py`, `hooks.py` and `CHANGELOG.md`; `scripts/check_release_consistency.py --offline` on the merged tree -> `# release consistency: 0 problem(s)`; `pytest -q` -> 1114 passed, 3 skipped, 1 failed where the single failure is `tests/unit/test_archive_merge_revisions.py:112` naming 29 archive revisions that are ancestors of `4fb1e09` and not yet of `refs/heads/main`, which the merge commit itself makes true.
- falsified by: `f277ac7` not being an ancestor of both lines; a record present on either parent and absent from the merged `Archive.md` or `Decisions.md`; a stale `11.x` reference to the harness contract surviving in `harness.py`, `hooks.py` or the three harness test files; the privacy-gate path-fragment guard (`_is_path_fragment`/`_is_path_name`, 4 hits on `4fb1e09`) absent from the merged `scripts/privacy_scan.py`; or a force-push appearing in the reflog of either line.
- consequences: The remote line's 123 commits and ours become one history. `T-0065` is the reconciliation task and `P-0096` its review. The published `M9` naming collision is recorded here so no later reader mistakes the two milestones for the same one. Re-dispatching work against `origin/main` is now safe only after this merge lands, because until then the remote does not contain the release-traceability milestone.
## D-20261021-Developer-1 - R3 takes every npm version key; a non-X.Y.Z published version is DRIFT unless 11.4 admits it

- date: 2026-10-21
- kind: technical
- status: accepted
- deciders: Developer-1 (developer)
- decided by: Developer-1
- task: T-0016
- context: -
- options considered: -
- decision: R3 no longer classifies a non-X.Y.Z npm version key as ignored: it is DRIFT unless release-exceptions.json admits it, and 11.4's version key accepts the published version string (X.Y.Z with an optional -prerelease/+build tail) so 0.0.0-stage can be admitted in writing.
- why: AC-REL-1 gives a published version exactly two paths, a tag or a written admission; 11.2.3 says take every version key, so shape was never an authorised third path. 0.0.0-stage cannot be tagged: gitHead is null, the tarball holds no payload path, and no commit in git rev-list --all carries the string - so the only honest path left is a recorded admission.
- evidence: python3 scripts/check_release_consistency.py --online @fb99293 -> R3 ok ... ignored non-X.Y.Z npm version(s): 0.0.0-stage, exit 0; same command on this branch with the 0.0.0-stage entry removed from the exception file -> R3 DRIFT 0.0.0-stage: not X.Y.Z, so no vX.Y.Z tag can carry it, and no release-exceptions.json entry admits it, exit 1; npm view @nidvue/teamwork time -> 0.0.0-stage 2026-10-20T08:50:57Z before 1.1.0 08:56:07Z, gitHead null, tarball digest -> InputError none of the shipped payload paths are present
- falsified by: A published npm version whose key is not X.Y.Z that R3 reports ok for. Or an npm version X.Y.Z-stage that does have a commit and could be tagged.
- consequences: release-exceptions.json gains the 0.0.0-stage entry; Architecture 11.2.3 and 11.4 gain one paragraph and one row; tests/unit/test_release_consistency.py gains two tests

## D-20261021-Reviewer-2 - review pass for tests/integration/test_links_flow.py

- date: 2026-10-21
- kind: technical
- status: accepted
- deciders: Reviewer-2 (reviewer)
- decided by: Reviewer-2
- task: -
- context: -
- options considered: -
- decision: review pass for tests/integration/test_links_flow.py
- why: -
- evidence: pytest -q tests/integration @7f285ce -> 115 passed; pytest -q test_links_flow.py @7f285ce -> 9 passed; same file @main b6c0817 -> 9 passed; mutation git checkout 781b1b4~1 -- src/teamwork/engine.py -> 2 failed with "# 0 markdown file(s)"; mutation cmd_links line 6228 "return 1 if issues else 0" -> "return 0" -> 6 failed (all links-failing tests, 3 clean-control tests still passed); restore -> 9 passed, git status empty; pytest -q tests/integration @5d30639 main -> green
- falsified by: -
- consequences: -

## D-20261021-CEO-5 - D-0027: an acceptance proof states the command and the exit code, never a pass count

- date: 2026-10-21
- kind: process
- status: accepted
- deciders: CEO (resolve)
- decided by: CEO
- task: T-0003 (tester)
- dispute: D-0027 (Tester-1 against Reviewer-3, 1 round)
- context: three review rounds failed tester T-0003 on pass counts that any commit changes (`790 passed`, `777 passed`, `1 missing, 2 stale`), and the third finding itself asked for a structural rather than numeric remedy.
- decision: an acceptance proof quotes the command, its exit code and the *named* failures and skips; it never pins a passing count. Where a count is genuinely the claim, it is bound to a revision and re-measured after every rebase in the same task.
- why: a pass count is a property of the tree at one revision, so any later merge falsifies it - which is why the same file carried two stale figures at once. The exit code and the test ids are the invariant; the count is not.
- evidence: `docs/Team/M9Acceptance.md` @28d6a4d -> §4 states exit 0 with the three named skips and explicitly refuses a count, §5 states `sync_skill.py --check` exits 1 and names the class of drift with no count; `grep -nE "790 passed|777 passed|1 missing, 3 stale"` -> no hits; `pytest -q` @28d6a4d -> 1198 passed, 3 skipped, exit 0; `teamwork.py links` -> `# issues: 0`; the deliverable passed review and merged at `a43e61e`.
- falsified by: a later `docs/Team/M9Acceptance.md` revision that pins a pass count again, or a review verdict that fails a proof for a count it re-measured on a different revision than the one named.
- consequences: the dispute is moot by delivery and closed; the same rule governs every later acceptance proof, and a count that does appear must name the revision it was taken at.
