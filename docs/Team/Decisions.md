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
- status: accepted
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
- status: accepted
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
