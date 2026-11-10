# Memory and task state

Owner: CEO.

Reference for the /teamwork skill. Loaded on demand; `SKILL.md` keeps the
operating procedure.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md) | [Coordination](Coordination.md)

## Memory model

Each agent owns three markdown files in its directory; the CEO additionally owns
the shared one. Management is via the script so caps and promotion are
deterministic, not vibes.

| Layer | File | Loaded | Purpose |
|---|---|---|---|
| Short-term | `ShortTermMemory.md` | at startup (`load`) | working memory for the current tasks |
| Long-term | `LongTermMemory.md` | never; queried (`recall`) | durable facts, interfaces, gotchas |
| Archive | `ArchivedMemory.md` | never; searchable | evicted long-term entries |
| Shared | `Global/GlobalMemory.md` | read on demand | facts no agent should re-ask |

```sh
teamwork.py load <agent>                                  # startup context
teamwork.py remember <agent> "<fact>" --key k --importance 0-5 [--pin]
teamwork.py recall "<query>" --agent <agent> | --global | --all
teamwork.py touch <agent> <key>                            # mark as used
teamwork.py consolidate --all                              # auto maintenance
teamwork.py global "<fact>" --key k --importance 4         # CEO only
```

Consolidation rules (automatic on `remember`/`load`, run manually by the CEO):

- A short-term entry unused for `STALE_DAYS` (3) with fewer than `MIN_USES` (2)
  uses is **promoted** to long-term when its importance >= 2, otherwise dropped.
- Overflow beyond `SHORT_CAP` (24) is promoted or dropped by score.
- Long-term is capped at `LONG_CAP` (64); the lowest-scoring entries (importance,
  use count, recency) are moved to the archive, pinned entries are never evicted.
- Duplicate keys merge: highest importance, summed uses, newest body.
- Caps are configurable with `TEAMWORK_SHORT_CAP`, `TEAMWORK_LONG_CAP`,
  `TEAMWORK_ARCHIVE_CAP`, `TEAMWORK_STALE_DAYS`, `TEAMWORK_MIN_USES`.

What belongs where: task-local working notes and in-flight decisions in
short-term; verified interfaces, commands, revisions, gotchas and rejected
approaches in long-term; team-wide facts in global memory (CEO), proposed by the
owner who discovered them.

## Task lists and priority

Every agent keeps a private `TaskQueue.md`, priority ordered. `P0` = critical path
code, `P1` = tests/verification, `P2` = docs/polish, `P3` = nice-to-have.

```sh
teamwork.py task add <agent> "<title>" --priority P1 --deps architect:T-0003 \
    --shared <issue/PR> --body "acceptance criteria"
teamwork.py task next <agent>            # highest-priority task with deps done
teamwork.py task list <agent>            # ready/blocked per task
teamwork.py task set <agent> T-0002 --status doing
teamwork.py task set <role> T-0002 --status selfcheck   # then selfcheck, pr open, review, pr merge
teamwork.py board                        # all queues: counts, next task, blockers
```

Rules: dependencies are explicit (`agent:T-0001` for cross-agent), a task with
unmet dependencies is never started, a finished task is marked `done` with
evidence before the agent looks for the next one, and an agent with executable
work never idles.
