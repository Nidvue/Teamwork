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
- status: accepted
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
- evidence: owner message in session 2026-10-17 'team agent email domain suffix should be agents.nidvue.com not local, update the corresponding commits'; git log --format='%an <%ae>' -> ceo@agents.nidvue.com / teamwork@agents.nidvue.com; python3 scripts/privacy_scan.py --tree --history -> 0 findings
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
- evidence: git log --format='%an <%ae>' -> ceo@agents.nidvue.com / teamwork@agents.nidvue.com; python3 scripts/privacy_scan.py --tree --history -> 0 findings; grep -rn 'agents.nidvue.com' -> only agents.nidvue.com
- falsified by: A commit or shipped document carries a mailbox outside agents.nidvue.com, or the owner changes the suffix again.
- consequences: -

## D-20261018-CEO - Re-attribute the commit history to the acting roles (authorized)

- date: 2026-10-18
- kind: redline
- status: accepted
- deciders: operator (user), CEO
- decided by: ceo
- task: -
- context: `main` carried 36 commits authored by the CEO, one by the product identity `Teamwork <teamwork@agents.nidvue.com>` and one by the Reviewer; the role that did the work must be the author.
- options considered: A - leave history and enforce forward only (non-destructive; old attribution stays wrong); B - `.mailmap` (display only, SHAs unchanged, per-commit role unknowable); C - rewrite authors, committers, trailers and tags by changed-path role (correct everywhere; every SHA changes and releases are re-pointed).
- decision: C, with the operator's explicit authorization. Each commit is attributed to the role that owns its dominant paths; author and committer dates are preserved; the `Role:` and `Acting role:` trailers are rewritten; `v1.0.0`-`v1.0.2` are re-pointed to the rewritten commits.
- why: the operator judged attribution correctness worth the SHA churn. A local bundle (`.pi/backup-pre-rewrite.bundle`, gitignored) is the rollback, and the new identity audit prevents recurrence.
- evidence: `git log --format='%an <%ae>' @a307cc0 -> 36 CEO, 1 Teamwork, 1 Reviewer`; the operator selected option 3 in the session of 2026-10-18.
- falsified by: a rewritten commit whose author does not own its dominant paths, or any red gate on the rewritten tree.
- consequences: every SHA changes, the three release tags move, existing clones and forks must re-fetch; the CI identity audit makes the rule enforceable from here on.
