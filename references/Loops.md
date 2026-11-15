# Loops and graphs

Owner: Architect.

Reference for the /teamwork skill. Loaded on demand; `SKILL.md` keeps the
operating procedure.

Related: [SKILL](../SKILL.md)

Two layers make a run stop needing a person, and the team shipped the first one
long before it could name the second:

- **a loop** makes one unit of work correct without a person reading it;
- **a graph** decides which units exist, in what order, and where a person signs off.

A loop without a graph is one excellent step in a badly designed process. A graph
without loops is a lot of unchecked output, fast. Every layer skipped comes back as
manual work: without a harness you click "allow", without a loop you read every
output, without a graph you approve every step.

## The check is the loop

A loop is only as good as the thing waiting at the end of it. A second model
reading the first model's output is a model grading its own homework with a friend:
it feels like review and catches very little. Rank what a gate accepts, strongest
first - `src/teamwork/grades.py` implements exactly this ladder and the gates read
the grade:

| Grade | What it is | Example |
|---|---|---|
| STRONG | a result a program produced | `pytest -q @rev -> 12 passed` |
| STRONG | output matches the schema | `ruff check . @rev -> exit 0` |
| STRONG | the diff stays inside the plan | `undo: revert, 3 file(s)` |
| MEDIUM | the cited source supports the claim | `docs/Team/Board.md:42` |
| MEDIUM | an independent path reaches the same answer | `TS-0006 @rev` |
| WEAK | a reviewer agent approves | a verdict with no command |
| NOISE | "looks good to me", "no errors were thrown" | refused on a pass |

The last row is the one that hurts experienced people: an empty error log means
nothing was *reported*, not that nothing went wrong. A loop that treats silence as
success repeats one mistake until the budget is gone, and every log line looks
clean. Write the check before you write the task; a project with a test suite can
take agent work without a person reading every diff, and a project without one
cannot.

## Every cycle needs five things

"Keep going until it is good" has no end. Count something instead:

| Need | Command |
|---|---|
| a test that says done | a round that adds no fresh finding is dry |
| a round limit | `hunt <topic> --run '<cmd>' --rounds 6` |
| a budget | `--timeout` per round, plus the round limit |
| memory of past attempts | `Runtime/Hunt/<topic>.json`: every key seen **and** every key rejected |
| a person paged if it stalls | an attention item and exit 1, never a silent stop |

`teamwork hunt` is that loop. It runs the command, treats each output line as a
finding, and stops after two consecutive dry rounds. The seen set includes rejected
findings, because a loop that forgets what it already threw away rediscovers the
same dead end and pays for it every round. A loop that spends its rounds still
finding things has not converged - it is stalled, and it pages.

For a *delivery* unit the same five exist in a different shape: the check is the
test layer, the round limit is `review --result fail` returning the task, the budget
is the lane's tool and minute budget, the memory is the findings on the record, and
the page is the third review fail opening a dispute.

## The graph between the nodes

A graph has nodes (one job each, one input, one output) and edges (this node's
output is that node's input). Nothing else. Most agent pipelines are drawn as
straight lines because that is how instructions are written, not because the work
is serial: the pricing step never reads the repository.

**Test every arrow by naming the payload that travels along it.** If you cannot
name it, delete the arrow and let both steps run in parallel. `teamwork graph`
answers the question with numbers: for every edge it reports how many waves the
arrow costs, and it lists the edges whose two ends share no feature, area or tag as
*unproved*. `teamwork graph --cut '<dep> <- <task>'` prints the same graph without
that one arrow, so the decision is a measurement rather than an opinion.

Only wait for everything to finish when the next node needs the full set - ranking
all candidates, deduplicating across sources. Otherwise the wave number is what
matters, and every task in one wave can run in one lane at the same time.

## Four shapes, and where they live

| Shape | When | In this protocol |
|---|---|---|
| chain | each step really reads the previous one | `deps` between two tasks, one wave per link |
| fan-out and join | research, reviews, audits | one task per role, one lane each, join at the Reviewer |
| router | a cheap classifier picks a short or a long path | `review_profile_for`: fast/standard/deep from the diff |
| bounded cycle | repair until the check passes, with a hard cap | self-check -> review fail -> fix, capped at 3 before a dispute |

One rule across all four: **parallel workers need separate contexts**. Put four
reviewers in one shared window and the first comment shapes the other three - you
pay for four reviews and get one, copied three times. That is why every lane is its
own process with its own packet and its own worktree.

## Where a node needs a model, and where it does not

Ask of each node: does it judge, decide, assess or summarise? If yes it needs a
model, sized by the job - small for extraction, strong for synthesis. If no, it is
code: merging lists, removing duplicates, sorting, joining records and classifying
evidence all have one correct answer, and running them through a model makes them
slower, pricier and occasionally wrong. `grades.py` is that rule applied to the
team's own gate.

## When a node fails, send back the unit, not the batch

| Failure | Response |
|---|---|
| tool or network blip | RETRY the same unit |
| model or source down | FALLBACK to another provider or model |
| optional branch failed | SKIP it and record why |
| output failed its check | REPAIR that unit only |
| 3 repairs failed | ESCALATE: the plan is wrong, not the unit |
| budget or permission hit | STOP and wake a person |

The costly mistake is returning the whole batch: four slices of a port, one fails
its tests, all four go back, three correct slices are rewritten into different
versions, and the run stops converging. A returned unit carries the failing check,
the evidence and a **scope** - `review --result fail --scope '<what the fix may
touch>'` - and the retried lane packet opens with it. Without the scope line the
agent fixes the bug plus two things it noticed nearby, and a one-line fix becomes a
four-file diff.

After a fix passes, the cause becomes a rule for whoever splits the work next time
(`teamwork lesson fix <L-id> --check '<cmd>'`). Almost nobody builds this step,
which is why most agent setups are fast but never improve.

## The gate opens by what a mistake would cost

Confidence is the one number a model produces about itself, and a threshold is a
number someone can lower on a busy Friday. Sort by how hard a change is to undo
instead - `grades.undo_class`:

| Class | Meaning | Gate |
|---|---|---|
| `revert` | a copy fix, a new test, an isolated function | one revert undoes it, merge |
| `evidence` | the constitution, the frozen contract, the build config | needs strong evidence |
| `closed` | migration or schema, payment, secret or auth path, a workflow on merge, a deleted file | stays closed until the CEO records who authorized it |

A closed lane has no number to lower. Check evidence in this order: the tests, the
run's history, how often this node's work has been rolled back, the reviewer
agent's opinion, and the model's own claim last.

## Who draws the graph

Two things decide it: how often the job runs, and how hard a mistake is to undo.

| Job | Graph |
|---|---|
| one-off refactor or audit | let the model generate the workflow, throw it away |
| one-off migration on production data | let the model draft the plan; a person reads the plan |
| weekly low-risk job | a fixed graph in the repository |
| weekly job touching money or users | fixed graph, and a person signs the last step |

The trap is letting a model regenerate a weekly workflow from scratch every run: it
splits the work differently each time, so nothing it learns carries over. This
protocol is a fixed graph - roles, gates, layers - and the *wave* is what is
computed per run (`swarm run` sizes it from the board). That is the split that
keeps the learning.

## The commands

```sh
teamwork.py graph                      # waves, critical path, what each arrow costs
teamwork.py graph --cut 'ceo:T-0001 <- developer:T-0002'
teamwork.py graph --check              # exit 1 on a cycle, a dangling dep, a duplicate id
teamwork.py graph --json
teamwork.py hunt '<topic>' --run '<cmd printing one finding per line>' --by <you>
teamwork.py hunt '<topic>' --reject '<dead end>' --by <you>
teamwork.py hunt '<topic>'             # what the loop already saw and threw away
```

`--run` is split with `shlex.split` and executed without a shell, so a round that
needs a pipeline or a redirect belongs in a small script the command calls.

## What is still a person's decision

The graph says what runs and in what order; it does not decide whether a unit
should exist. That stays with the CEO, at the two points where a mistake cannot be
undone: approving the merge of a closed lane, and signing off the plan a migration
will execute.

## Source

The doctrine above was distilled from an article supplied in the session on
2026-11-13 (X/Twitter, `@HoodieFade_`, "Loops & Graphs"). No stable URL was
available to link, so its empirical claims - the Bun port line count, the test-suite
percentage, the 31-to-17-minute example - are **UNVERIFIED** and are not repeated
here as facts. Only the rules were adopted, and each is bound to a command this
repository runs.
