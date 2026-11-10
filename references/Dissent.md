# Decisions, dissent and the tribunal

Reference for the /teamwork skill. Loaded on demand; `SKILL.md` keeps the
operating procedure.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md)

## Decision and dissent protocol

The team's decisions are independent and evidence-based, not consensus by
deference.

**Every agent decides independently.** A decision is only valid with an evidence
chain: claim, data/measurement (command, file, benchmark, revision, source+date),
reasoning from evidence to conclusion, rejected alternatives, the bet you are
making, and the test that would falsify it. "I think", "should be fine" and
"best practice" are not evidence. Prefer measuring over debating; when a
measurement is impossible, label the decision provisional.

**Dissent is mandatory, not optional.** An agent that finds a design or decision
unreasonable must challenge the owner with counter-evidence instead of silently
complying or working around it:

```sh
python3 "$SKILL/scripts/teamwork.py" dispute open \
    --by developer-1 --against architect --topic "sync DB calls in request path" \
    --position "will not meet the p99 target" \
    --evidence "bench: 12ms/query x8 = 96ms @abc123 > 50ms budget" --task T-0007
python3 "$SKILL/scripts/teamwork.py" dispute round D-0001 --by architect \
    --message "pooling measured at 14ms total @def456"
```

**3-round cap, then the tribunal.** The two agents get at most three rounds. If
they still disagree, the dispute escalates to the **CEO + CTO + CFO tribunal**,
which discusses it and issues a final, binding ruling:

```sh
python3 "$SKILL/scripts/teamwork.py" dispute escalate D-0001 --by developer-1
python3 "$SKILL/scripts/teamwork.py" dispute sign D-0001 --by ceo   # and cto, cfo
python3 "$SKILL/scripts/teamwork.py" dispute resolve D-0001 --by ceo \
    --decision "pool + 20ms timeout + load-test gate"
```

The tool enforces this: a 4th round is refused, an escalated dispute cannot be
resolved until all three tribunal members have signed, and `audit` flags any open
dispute at the round cap. The ruling is recorded in `docs/Team/Decisions.md` and
is final - the losing side implements it and says so in its report. A dispute
never blocks unrelated work; keep going on everything not contested.

**Who may sit.** The party rule is per instance: an instance is a party when it
is named in `raised_by`/`against`, and a party may never sign or resolve - not
even with `--force`, which waives the signature requirement, not the party rule.
A role leaves the panel only when EVERY one of its instances is a party, so in a
dispute between two Reviewers the third, uninvolved Reviewer is the neutral seat
and may rule it.

## Parallel lanes

The team is a set of lanes, not a queue:

- **Lane 0 (blocking, short):** requirements -> acceptance criteria -> frozen
  interfaces -> task graph. Everyone else starts the moment this lands.
- **Lane A (code):** developers implement against the contract; unit tests are
  part of each change.
- **Lane B (verification):** testers build integration/E2E suites from the same
  contract in parallel with implementation, then run and monitor them.
- **Lane C (design):** designers produce specs and copy from the contract, then
  review the merged UI.
- **Lane D (research/ops/cost):** PM research, COO risk and process, CFO cost,
  running continuously and feeding lanes A-C.
- **Lane E (docs):** produced from merged code, scheduled last, never a gate.

Rules: one writer per file/worktree; interfaces frozen before parallel writers
start; interface changes require a `Decisions.md` entry plus notification to
every dependent lane; a lane that finishes takes the next unblocked task instead
of waiting.

## Failure handling

- **Infrastructure failure** (spawn, tool, provider): stop the lane, record the
  exact error, worktree state and partial diff, retry once cleanly, then report
  to the CEO. Never silently switch execution mode.
- **Blocked on a dependency**: mark the task `blocked` with the exact unblock
  action and owner, tell the Project Manager, and take other executable work.
- **Blocked on the user**: CEO asks one consolidated question; the lane keeps
  working elsewhere meanwhile.
- **Contradictory evidence**: escalate to the CEO; record the resolution in
  `Decisions.md` and global memory.
- **Repeated failure of the same task**: the CEO re-scopes, splits, or reassigns;
  it is never marked done to make the board look green.
- **Red-line refusal**: expected and correct behaviour. Record it, escalate, and
  continue with the rest of the plan.
