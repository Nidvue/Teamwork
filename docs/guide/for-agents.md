# For agents - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Installation](install.md) · [Quickstart](quickstart.md) · [How it works](how-it-works.md) · [Architecture](architecture.md) · [CLI reference](cli.md)

If you are the agent reading this repository, not the human who installed it: you
can install and drive this skill yourself. Do the steps in order, and repeat them
safely - every one is idempotent.

## 1. Find the skill directory, then install

A skill is a directory; the only host-specific part is where that directory is
scanned from. Use your host's skills directory if it names one, otherwise the
portable conventions below work.

| Scope | Convention | When |
|---|---|---|
| Project | `.agents/skills/teamwork/` | The team protocol should travel with the repository |
| User | `~/.agents/skills/teamwork/` | The team should be available in every project |

```bash
# already installed? any hit means yes
ls .agents/skills/teamwork/SKILL.md ~/.agents/skills/teamwork/SKILL.md 2>/dev/null

# not installed: clone once into the directory your host scans
mkdir -p .agents/skills
git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork
rm -rf .agents/skills/teamwork/.git   # plain files, not a nested repo
```

The installed layout and the optional package channels are compared in
[Installation](install.md). You do not need a package manager to run the team.

## 2. Verify before you promise anything

```console
$ python3 .agents/skills/teamwork/scripts/teamwork.py selftest
teamwork selftest: 5/5 checks passed
```

Use the directory you actually cloned to; the engine is the same in all of them.

Exit `0` means the bundle and the engine are intact. Anything else: report the
failure with the command and its output, and stop. Do not improvise a replacement.

## 3. Follow the skill, from its own directory

1. Read `<skill>/SKILL.md` completely, then `<skill>/roles/<your-role>.md` for the
   role you are acting as.
2. Run `scripts/teamwork.py init --roster slim` (or `standard`/`full`, or
   `--agents` for an exact list; the skill usually does this for you) and
   `agents-md` so the constitution is in place before any work starts.
3. Claim work with `task next <you>`; never sit idle while ready work exists.
4. Record evidence as `command @revision -> result`; submit with `selfcheck`, then
   `pr open`. A different role reviews and merges - you never merge your own work.
5. Check your mailbox before you start anything long:
   `message inbox --for <you>`. A message is queued, prioritised and delivered in
   your next lane packet; `take` it so no other lane of your role does the same
   work, and `done` it with the result. An `urgent` message is the one that
   preempts your lane - that is why its task goes `paused` until the mailbox is
   empty.
6. Keep your own startup read small: `load` prints a capped memory index rather
   than every entry, `context find` answers a question without loading a whole
   record file, and `harness budget` shows the bytes you cost against the cap.
7. Stop only when `loop` prints `STOP` and `audit` reports no problems.

Read [references/Adapters.md](https://github.com/Nidvue/Teamwork/blob/main/references/Adapters.md)
for the six host operations,
[references/Concurrency.md](https://github.com/Nidvue/Teamwork/blob/main/references/Concurrency.md)
for slot leases and model routing,
[references/Coordination.md](https://github.com/Nidvue/Teamwork/blob/main/references/Coordination.md)
for the multi-agent failure modes and the checks that catch them, and
[Quickstart](quickstart.md) for the workspace layout. Do not read the whole tree
first; the skill is written to be loaded on demand.

## 4. Rules that are not optional

- No claim about code, tests or CI without a recorded command, revision and result.
- Never fake a test run, never merge your own work, never weaken a gate.
- A red line (secrets, force-push, publishing, production calls) is refused and
  recorded with `redline` - then escalated, never executed.
- The user talks to the CEO only. Every other role reports to its manager
  (`teamwork.py map` draws the tree): the CTO for engineering, the COO for
  planning, the Product Manager for requirements and docs. Escalate upward,
  not sideways to the CEO.

## 5. What "done" means from the inside

An agent that finishes a task has not finished the work. The task is done when
its self-check recorded a real test, an independent role passed the revision, and
the merge landed. Until then the task is still `doing` or `selfcheck`, and
`loop` refuses `STOP`. The full sequence - claim, implement, test, self-check,
PR, review, merge - is on [How it works](how-it-works.md) and every command is in
the [CLI reference](cli.md).

When your own self-check or a review fails, record a lesson before re-submitting:
`teamwork lesson add` writes it to the role's shared `Lessons.md`, and the next
instance of that role starts from the correction instead of the mistake.
