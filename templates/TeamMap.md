# Team map

The team's own tree. **Hidden and independent of project output.** Every name is
PascalCase; one tree per team, so two teams in one repository never collide.

```text
{project}/.pi/Teamwork/Teams/<Team>/     # this tree (hidden, never committed)
├── TeamMap.md            # this map
├── Settings.json         # provider caps
├── Global/               # CEO-owned shared memory
│   ├── GlobalMemory.md
│   └── GlobalMemoryArchive.md   (created on first eviction)
├── Criteria.md           # acceptance criteria + verification evidence
├── Tests.md              # one record per test layer and area
├── TestPlan.md          # required layers per area
├── Ledger.jsonl         # append-only, hash-chained audit trail
├── Skills.md            # team-skill registry
├── Disputes.md           # design/decision challenges
├── Reviews.md            # PRs awaiting / passed the Reviewer
├── Roles/<Role>/         # SHARED memory + queue for every instance of a role
│   ├── Role.md
│   ├── ShortTermMemory.md
│   ├── LongTermMemory.md
│   ├── ArchivedMemory.md
│   └── TaskQueue.md
├── Agents/<Instance>/    # private to one instance
│   ├── StartHere.md  WorkLog.md  Inbox.md
│   └── Artifacts/  Reports/  Scratch/
└── Runtime/              # ephemeral
    ├── LedgerHead.json
    ├── Locks/
    ├── Worktrees/<Instance>/       # optional per-instance worktree
    └── Slots/<Provider>/<Agent>.slot
```

Project output - code, tests and the reviewed documents in `{docs}/` - lives in
the repository and is committed. The team tree above is local state and is
gitignored.

## Team

- Team name: `<Team>`
- Project: `{project}`
- Team root: `.pi/Teamwork/Teams/<Team>/`

## Audit trail

Every mutation appends one hash-chained record to `Ledger.jsonl`, and every record
carries provenance (actor, role, target, revision). Verify it, follow a claim, or
export an externally checkable manifest:

```sh
python3 {skill}/scripts/teamwork.py ledger verify      # recompute the chain
python3 {skill}/scripts/teamwork.py ledger show --tail 40
python3 {skill}/scripts/teamwork.py trace <T-id>
python3 {skill}/scripts/teamwork.py ledger export      # -> {docs}/AuditManifest.json
```

## Commands

```sh
python3 {skill}/scripts/teamwork.py map                       # this map + detected code/test dirs
python3 {skill}/scripts/teamwork.py agents                    # roles, instances, queue sizes
python3 {skill}/scripts/teamwork.py board                     # shared queues and next task per role
python3 {skill}/scripts/teamwork.py parallel                  # free slots vs ready work
python3 {skill}/scripts/teamwork.py task next <instance>      # claim the next task of your role
python3 {skill}/scripts/teamwork.py load <instance>           # your role's short-term memory
python3 {skill}/scripts/teamwork.py recall "<query>" --all    # search long-term + global memory
```

## Quality gates and integration path

```text
branch start -> commit -> SelfCheck -> Review -> done -> merged into main
                            (owner)    (Reviewer)          (Reviewer only)
```

The owner self-reviews and self-tests, then the Reviewer verifies independently.
Every agent works on its own branch; `main` only receives Reviewer merges, and a
merged branch is deleted.

Every role owns one test layer: `goal` CEO, `requirements` Product Manager, `plan`
Project Manager, `tech` CTO, `release` Release Engineer, `data` Data Engineer,
`process` COO, `cost` CFO, `system` Architect, `ui` Designer, `docs` Technical
Writer, `unit` Developer, `integration` Tester, `acceptance` Reviewer, `security`
Security Auditor. `tests plan` shows coverage and gaps; the default per area is the
core set (`unit`, `integration`, `acceptance`).

## Concurrency

Caps in `Settings.json` (Ollama Cloud 64, DeepSeek official API ~2500, openai/anthropic 64). Hold a
lease for model-heavy work: `slot acquire --agent <instance>`, `slot renew`,
`slot release`. At the cap, do work needing no slot or fan out on another
provider - never block.

## Priority

1. **Code** - working, reviewed, merged implementation.
2. **Tests** - unit tests (Developer) and integration/E2E tests (Tester), run.
3. **Documentation** - from verified code, never blocking 1 or 2.