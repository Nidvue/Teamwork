# PROJECT - <name>

Owner: CEO. Single source of truth for *what done means*. No task closes without
mapping to an acceptance criterion here.

Related: [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## Objective

<one paragraph: what we are building and what "finished" means>

## Brief

The intake record: the prompt as given, what it means, and the brief the team
builds against. Written once by the CEO with the `tw-brief-intake` skill before
anything is decomposed; every lane reads this section before its first task.

### Original prompt (verbatim)

> <the prompt unchanged: no cleaning, no translation, no summary - this is the
> only ground truth for an intent dispute>

### Intention

- Who asks, and for whom: ...
- Job to be done: ...
- What "good" looks like when it is finished: ...
- Non-goals: ...
- Requirements the prompt only implies: ...
- The misreading we must not make: ...

### Rewritten brief

1. Objective: <one sentence, one measurable outcome>
2. Deliverables: <artifact -> path, one per line>
3. Acceptance criteria: <AC-n, each with the command that proves it>
4. Constraints and invariants: ...
5. Interfaces to freeze: <contract -> owner>
6. Lanes: <owner -> artifact -> file boundary -> dependency>
7. Unknowns and assumptions: <each with a resolution owner>
8. Evidence plan: <criterion -> test layer -> the role that runs it>

### Research that changed the brief

- <finding> - <source: title, direct URL, access date>

(The full evidence base lives in [Research](Research.md); this list carries only
what changed a sentence of the brief.)

## Definition of done

- [ ] AC-1 <verifiable statement> - proof: `<command or artifact>`
- [ ] AC-2 ...
- [ ] All criteria verified by executed evidence on a recorded revision
- [ ] Unit + integration tests pass; docs match merged code

## Scope

- In: ...
- Out (not doing): ...
- Constraints (time / budget / technical): ...
- Invariants that must not break: ...

## Metrics

| Metric | Target | How measured |
|---|---|---|
| | | |

## Assumptions and open questions

| # | Item | Owner | Status | Resolution |
|---|---|---|---|---|
| 1 | | | open | |

## Sources

- [title](https://full-url) - accessed YYYY-MM-DD
