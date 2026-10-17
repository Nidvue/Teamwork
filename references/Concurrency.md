# Concurrency and reuse

Reference for the /teamwork skill. Loaded on demand; `SKILL.md` keeps the
operating procedure.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md)

## Concurrency budget and resource reuse

Run everything as parallel as the providers allow, never past their caps.

| Provider | Concurrent agents | Use it for |
|---|---|---|
| Ollama Cloud | ~10 | focused reasoning lanes: architecture, review, disputes, analysis |
| DeepSeek official API | ~2500 | wide independent fanout: many developer/tester/designer sub-tasks, bulk docs and research |

Caps live in `.pi/Teamwork/Teams/<Team>/Settings.json` and are overridable with
`TEAMWORK_PROVIDER_LIMITS="ollama-cloud=10,deepseek=2500"`.

### Slots are leases

Every model-heavy task holds a lease in `.pi/Teamwork/Teams/<Team>/Runtime/Slots/<provider>/`.
Leases expire after `TEAMWORK_SLOT_TTL_MINUTES` (90) so a crashed lane cannot
leak capacity.

```sh
teamwork.py slot acquire --agent developer-3 --provider deepseek --task T-0012
teamwork.py slot renew   --agent developer-3          # every ~60 min on long work
teamwork.py slot release --agent developer-3
teamwork.py slot list                                  # used / cap / free per provider
teamwork.py slot reap                                  # expire dead leases
```

At the cap, `slot acquire` fails with exit 3 instead of blocking. The lane then
does work that needs no slot (read, plan, review a peer's output), fans out on
another provider, or waits for a lane to release - it never stalls the team.

### Plan the parallelism

```sh
teamwork.py parallel
# - focused reasoning lanes (ollama-cloud): 7 free
# - bulk fanout lanes (deepseek): 2496 free
# - start up to 7 new lane(s) now (ready tasks: 12)
# - 3 lane(s) already hold a slot: hand the next task to a running lane first
# - independent sub-tasks only: one writer per file
```

The CEO uses this before every dispatch round: fill every free slot with
independent ready work, and scale `developer-N` / `tester-N` / `designer-N`
instances to the available capacity rather than to a fixed number.

### Reuse before you recompute

- Reuse a **running lane** before spawning a new one - the teammate already holds
  its memory, role and context.
- Reuse **evidence**: if a verification already passed on the same revision, cite
  it (`BUILD ECONOMY`) instead of re-running.
- Reuse **research and artifacts**: read global memory, long-term memory and
  `docs/Team/` before producing anything new; update in place, never duplicate.
- Reuse **build/test caches**; never rebuild from scratch for a clean slate.
- Reuse **the same artifact across lanes**: a frozen interface, fixture or script
  is shared, not re-created per task.
- Deduplicate before dispatch: `teamwork.py audit` flags near-identical tasks.

### Parallelism rules (non-negotiable)

- One writer per file/worktree. Concurrency never means two agents editing the
  same file.
- Only independent tasks run together; dependent tasks queue on their `deps`.
- The Reviewer, the Project Manager and the CEO are lanes too - keep them fed.
- Never exceed a provider cap to "go faster": the extra lanes fail, and the
  failure costs more than the parallelism gains.


## Per-agent model configuration

The skill does **not** ship a model and does not call an LLM API itself. Each
agent runs through the host's own API, so the model is a property of the *agent*,
not of the project, and every lane can pick one independently:

```sh
teamwork.py model set reviewer   --provider anthropic --model <strong>   # role default
teamwork.py model set developer-1 --provider deepseek --model <cheap>   # instance override
teamwork.py model get developer-1
teamwork.py model list
```

- An **instance** setting wins over the **role** default; an unset agent uses the
  host's own default and records `unset`.
- Give the reasoning-heavy lanes the stronger model (Reviewer, Architect,
  Security Auditor) and the mechanical ones a cheaper or faster one (bulk edits,
  formatting, link checks). Cost and latency are a per-lane choice, not a global one.
- A model change is a recorded act (`Settings.json` + the ledger); the CEO sets the
  lanes at intake, and an agent never changes another agent's model.
- Model choice never changes the protocol: the evidence gates, the two-stage
  review and the ledger hold whatever model produced the work.

### Automatic cost-aware routing

```sh
teamwork.py model auto            # dry run: the plan, per lane
teamwork.py model auto --apply    # write it into Settings.json
teamwork.py model auto --json
```

`model auto` reads the *runtime environment* - which agent host is running (Pi,
Claude Code, opencode, Codex, Cursor, Gemini CLI) and which model that host already
exposes - and routes **the strongest available model to the lanes where a mistake
is expensive** (Reviewer, Architect, Security Auditor, CEO, CTO) and **the economy
model to the mechanical lanes** (developers, testers, writers, formatting, link
checks). Quality where it compounds, cheapness where it does not.

- It never invents a model id: `TEAMWORK_MODEL_STRONG` (or the host's own
  `ANTHROPIC_MODEL` / `PI_MODEL` / `OPENCODE_MODEL` / ...) supplies the strong tier,
  `TEAMWORK_MODEL_ECONOMY` the cheap one, and a lane with neither is reported as
  `unset` together with the variable to set.
- `--apply` is explicit: the plan is a dry run by default, and applying it is
  recorded in the ledger.
- Re-run it when the host or the budget changes; it is idempotent.
- `TEAMWORK_AGENT_HOST=claude|pi|opencode|codex|cursor|gemini` overrides
  detection when the markers are ambiguous (CI, wrapper scripts).
