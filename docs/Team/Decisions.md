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
- falsified by: pip install teamwork-agents does not expose the teamwork command.
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
- why: Measured on main f277ac7: npm dist-tag latest = 1.1.2 but git has no v1.1.1/v1.1.2 tag, so 'released' means two different things; the GitHub Release lags npm by two versions; README.md:132 and docs/guide/install.md:115,157 print 'teamwork 1.0.2' while version.py says 1.1.2; docs/Team/Release.md:116 rolls back to a v0.9.0 tag that does not exist; and pip install teamwork-agents 404s on PyPI while README.md:122 still prints the command. Each is a claim a reader can falsify in one command, which is the defect class this project exists to remove.
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
- evidence: ls .pi/Teamwork/Teams/Teamwork/Roles/ -> Architect CEO CTO Developer ProductManager ProjectManager ReleaseEngineer Reviewer SecurityAuditor Tester (no TechnicalWriter, no Designer); docs/Team/Architecture.md:66-89 assigns README.md to designer-1 and CHANGELOG.md+docs/guide/** to technical-writer; tests plan requires only staffed roles' layers
- falsified by: A second writer touches one of those files in this milestone, or the Reviewer finds a docs claim no role could have measured.
- consequences: The docs layer stays unstaffed and tests plan reports no gap for it; the Reviewer still reviews every docs edit, so the second gate is unchanged.
