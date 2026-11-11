# MEMORY - research, design and lifecycle of the team's memory

Owner: CEO.

Related: [Project](Project.md) · [Plan](Plan.md) · [Throughput](Throughput.md)

This page answers one question: **how do agents here accumulate knowledge and
experience, and act on it later, without spending the token budget or the wall
clock on remembering?** It records what is verified, what this engine already has,
what it lacks, and the design that closes the gap.

## 1. Sources (verified 2026-11-07)

- [The components of agent memory](https://www.anthropic.com/research/components-of-agent-memory) - accessed 2026-11-07.
- [MemGPT: towards LLMs as operating systems](https://arxiv.org/abs/2310.08560) - accessed 2026-11-07.
- [Generative agents: interactive simulacra of human behavior](https://arxiv.org/abs/2304.03442) - accessed 2026-11-07.
- [A-MEM: agentic memory for LLM agents](https://arxiv.org/abs/2502.12110) - accessed 2026-11-07.
- [Zep: a temporal knowledge graph for agent memory](https://arxiv.org/abs/2501.13956) - accessed 2026-11-07.
- [Mem0: building production-ready AI agents with scalable long-term memory](https://arxiv.org/abs/2504.19413) - accessed 2026-11-07.

## 2. What the Anthropic article actually measured

Every row was read from the page text on 2026-11-07; none is quoted from a
secondary summary.

| claim | measured in the article | status |
|---|---|---|
| memory is four layers: transcripts, notes, representations, injected context | the post is organised around exactly those components, with a fifth process ("dreaming") that maintains them | verified |
| dreaming consolidates, corrects and prunes memory off the hot path | "reflecting on logs to fix mistakes or produce new notes and representations ... often called dreaming" | verified |
| notes need provenance | Opus 5 "included a rule (and also how it knew the rule was true)"; Sonnet 5 "wrote a correction when it had answered wrong" | verified |
| too much memory is worse than too little | Pokémon Red, one run each at ~10,000 steps: Sonnet 3.7 wrote 413 files in 225 folders and earned 1 badge; Fable 5 wrote nine files in two folders plus one `global.md` and earned 4 badges | verified, single run, the authors do not attribute the difference to file count alone |
| a wiki representation beats raw search once it grows | 25 questions over ~350,000 files / ~420M tokens from Stainless: search alone 53%; search + wiki 54% -> 61% as the wiki grew; wiki alone peaked at 48%; ~20,000 tokens saved per question | verified |
| dreaming scales with sessions | 2 -> 128 sessions took graded criteria from 13% to 48% | verified |
| CL-Bench database task: memory beats stateless | the article reports a memory-ablation comparison and names which models closed the learning loop; **the exact 0.655 -> 0.838 figures do not appear in the page text** | `UNVERIFIED` here - chart-only value, do not cite as a number |
| injected memory is a cost and a risk | "injected memories use up valuable tokens, and an incorrect note can be carried into every session" | verified |

**The transferable lesson is not the numbers, it is the lifecycle:** decide what
is worth writing, attach the reason it is true, maintain the store off the hot
path (merge, correct, prune), and inject only what the current task needs.

## 3. What this engine already has

| layer | where | today |
|---|---|---|
| transcripts | `Ledger.jsonl` (hash-chained), `Agents/<I>/WorkLog.md`, `docs/Team/Archive.md` | append-only, replayable, never read whole |
| notes | `Roles/<R>/ShortTermMemory.md`, `LongTermMemory.md`, `Lessons.md`, `Knowledge.md` | written by `remember`, `lesson add`, `knowledge add`; each carries `by`/`src`/`rev` or `evidence` |
| representations | `ctx://` (ls/tree/read/find/digest) over memory, lessons, knowledge, skills, docs, tasks; `Knowledge.md` topics and tags; `memory search` (4.3) | a **view**, computed on read; `memory search` ranks all three stores with one scorer and caps its output |
| injected context | `load [--task T]` prints short memory + open lessons + a task-aware pack (4.1), capped by `AlwaysOnBudgetKb` | **task-aware** on `--task`, static top-10 without it - so every existing caller keeps its shape |
| consolidation | `consolidate` promotes stale short-term entries by age and importance; `memory dream` (4.2) merges duplicates, archives stale records and reports contradictions | `dream` is the verification/merge pass the article's "dreaming" describes; `consolidate` keeps its age-based promotion |

Measured gaps (2026-11-07, this workspace; closed by `memorypack.py` at
`ec61726`, see 5):

1. `recall "lock" --agent developer` returns **no match** even though the
   developer lessons and knowledge discuss locks: `recall` searches only
   short/long memory, so the 40+ lessons and 20+ `K-` records written this
   engagement are invisible to the retrieval path. Experience is written and
   never read.
2. Injection is static. A developer lane receives the same top-10 knowledge
   whether it is fixing a lock race or writing a doc row.
3. `uses` counters exist but only `knowledge touch` increments them, so ranking by
   usefulness is inert.
4. Nothing detects a duplicate, a contradiction or a stale entry. `knowledge add`
   warns on a duplicate topic; nothing merges, supersedes or forgets.

## 4. Design - four layers and a dream pass, inside the token budget

Non-negatives: stdlib only, no new store, no background daemon, no embedding
service, and the always-on budget is not raised. Everything below is file-based
and O(n) over a few hundred small records.

```text
 write (hot path)            maintain (dream, cheap, on demand)      read (hot path)
 ------------------          ----------------------------------      ---------------
 transcript  -> ledger       verify evidence still resolves           pack(role, task)
 note        -> knowledge    merge duplicates -> supersede            search(query)
               lessons      flag contradiction -> older superseded    recall (all stores)
               memory       archive stale (unused, old) -> archived
 representation -> ctx://    rebuild the topic digest + links          digest/topic
 injected context <- pack()  measure bytes reclaimed (ledger event)    <= budget bytes
```

### 4.1 `memory pack` - the injected-context layer (task-aware, capped)

`memory pack --role <role> --task <T-id | free text> [--budget N]` collects
lessons + knowledge + short memory for that role, scores each record, and prints
the best ones until the byte budget is spent.

Score (deterministic, no model call):

```text
score = 0.50 * term_overlap(query, record)      # tokenised, stopwords removed
      + 0.20 * (importance / 5)
      + 0.15 * recency(updated, half_life = 30 d)
      + 0.15 * min(uses / 5, 1)
tie-break: id ascending
```

`term_overlap` is the fraction of distinct query terms found in the record's
statement/title/tags, so a two-term task title cannot be beaten by one long
record repeating a single word. Every rendered line is one record: `id`, `kind`,
the statement clipped to 200 characters, and where the full record lives - so the
pack is a **pointer index**, never a copy of the store.

`load --task <T-id>` uses the pack instead of the static top-10 and prints the
pack's byte count. Default budget: 4,000 bytes (about 1k tokens), a third of what
`load` prints today.

### 4.2 `memory dream` - the maintenance pass (off the hot path)

`memory dream [--role R] [--dry-run | --apply]` runs four deterministic checks
over lessons and knowledge:

| check | rule | action on `--apply` |
|---|---|---|
| duplicate | same normalised topic/key and term overlap of the statement >= 0.8 | keep the newer active record, mark the older `superseded` with `superseded_by` |
| contradiction | same topic/key, both active, statements disagree (overlap < 0.5 and same topic) | do **not** auto-resolve: print both and require a person or the owning role to decide |
| stale | `uses == 0` and `updated` older than 90 days and not `pinned` | `archived` (kept, out of the pack and out of `load`) |
| unreferenced evidence | `evidence` empty or `< 20` chars | reported only; a record with no evidence is a claim, not knowledge |

`--apply` appends one `memory.dream` ledger event per action with the ids and the
byte delta, so the pass is auditable and repeatable. It never deletes a record and
never rewrites a statement: the only mutations are `status` and `superseded_by`.

**The pass has a trigger.** A maintenance step nobody schedules never runs, so
every `pulse` and every `swarm run` prints one line before it dispatches:

```text
# memory: 49 record(s) -> 0 duplicate(s), 0 stale, 0 contradiction(s), 0 without evidence;
  `memory dream --apply --by <you>` acts, nothing was written
```

The trigger reports and never writes: the mutation stays an explicit, named
command, so no background process edits the stores and every change has an
author.

### 4.3 `memory search` - one retrieval path over all four stores

`memory search <query> [--role R]` ranks lessons, knowledge and memory together
with the same score as the pack and prints the top 10 with their store and
pointer. `recall <query> --agent R` reaches the same three stores: it keeps its
short/long memory output and adds one section per role's `Lessons.md` and one for
the project `Knowledge.md`, each hit naming its id and store. The old behaviour
(the command agents call seeing only memory) is what made experience write-only.

### 4.4 Write discipline (the reason a note is trustworthy)

A record is worth writing when it is **a rule or a fact that a future task will
rely on without re-checking**, and it is only reviewable when it carries the
reason:

- knowledge: `statement` + `evidence` (command @rev -> result, path:line, or URL
  + access date). `knowledge add` already refuses without evidence.
- lesson: `mistake` + `cause` + `rule` + `evidence`.
- memory: `body` + `by` + `src` + `rev`.

No model call decides salience: the agent writing the record does, and the dream
pass audits it later. That is the article's "judgment about what to save" moved to
the cheapest possible place.

### 4.5 The injection point for a spawned lane

A parallel wave is where the injection layer pays for itself: several agents start
at once, each on a different task, and none of them should pay for the whole
store. So the lane packet's first read is the pack, not the static block:

```text
tw load <Instance> --task <T-id>   # role memory + the pack for this assignment
```

The packet is generated by `src/teamwork/lanes.py` (`build_packet`), so every lane
started by `lane start` or `swarm run` receives the same contract. The pack is not
only named there: `build_packet` injects it under its own heading
(`engine.memory_pack_block`), so the prompt a lane receives already carries the
ranked records and their byte footer - a model cannot skip the task-aware memory
by not running a command, and the footer is the first number in the packet.
`load` without `--task` keeps its old output, so a person or a host that runs it
by hand is not surprised; only a spawned lane is guaranteed the injected form.

## 5. Budgets (measured, not aspirational)

Every row was measured on this workspace at `ec61726` (the memory lifecycle
branch, rebased on `main`) against the live team tree, 45 records: 2 lessons,
29 knowledge records and the role memory sets. The command is the measurement.

| surface | before | after | command |
|---|---|---|---|
| `load` for a lane | 6,381 B (Developer) | 5,797 B with `--task T-0036`; the pack inside it is 3,936 B of records + a 2-line header/footer | `teamwork.py load Developer [--task T-0036] \| wc -c` |
| a task-aware pack | n/a | 4,174 B total, 3,936 B of records against a 4,000 B budget | `memory pack --role developer --task T-0036 \| wc -c` |
| pack determinism | n/a | two runs, byte-identical (`cmp` exit 0) | `memory pack ... > a; memory pack ... > b; cmp a b` |
| `memory dream --dry-run` | n/a | 0.069 s wall over 45 records, no model call | `time teamwork.py memory dream --dry-run` |
| retrieval | `recall` reached only short/long memory | `memory search review` -> 7 of 7 records (lessons + knowledge), 1,795 B, capped at 2,000 B / 10 records | `memory search review \| wc -c` |
| dream apply | n/a | 1 duplicate superseded, 31 records before and after (0 deleted), 2 lines changed, `bytes +28` in the ledger, second apply 0 actions and no new event | `memory dream --apply --by <you>` twice on a copy |
| a spawned lane's prompt | n/a | 7,640 B packet, of which the injected pack is 3,938 B (16 records, budget 4,000) - measured on `Agents/CEO/Runs/L-0026.md` from the injection wave | `wc -c` on the packet; `grep -A1 'Memory pack for this assignment' <packet>` |
| `uses` on the read path | only `knowledge touch` incremented it | `load Developer --task T-0043` -> 15 injected records counted, one `memory.pack` ledger event, every injected record +1 and a second load +1 again | `grep -c 'memory.pack' Ledger.jsonl`; `grep -A 9 '^## K-' Knowledge.md \| grep uses` |
| `recall` coverage | short/long memory only | `recall "merge hook" --agent Developer` -> the knowledge record; `recall "backtick" --agent Developer` -> the lesson; `--all` searches every role | `teamwork.py recall '<term>' --agent <role>` |
| the maintenance trigger | none | `pulse` and `swarm run` print the dream line over 49 records in the same command that dispatches, and write nothing | `teamwork.py pulse \| grep '^# memory:'` |

The cap in `Settings.json` is **not** raised: the task-aware `load` is 584 B
smaller than the static one it replaces, and the pack alone is 2,445 B smaller.

## 6. Acceptance criteria

| id | criterion | owner | verifier |
|---|---|---|---|
| AC-M20-1 | `memory pack --role R --task T` injects task-relevant lessons/knowledge within its byte budget, deterministically (same input -> same output), and is smaller than the `load` it replaces | Developer | Reviewer |
| AC-M20-2 | `memory search` reaches lessons, knowledge and memory in one query and caps its output | Developer | Reviewer |
| AC-M20-3 | `memory dream --apply` merges duplicates, archives stale records and reports contradictions without deleting or rewriting any record, is idempotent, and appends one auditable ledger event per action | Developer | Reviewer |
| AC-M20-4 | no store grows unbounded: every record carries provenance, and the dream report proves the byte delta | Developer | Reviewer |
| AC-M20-5 | the always-on budget is unchanged, `loop`/`audit` stay green on the merged revision, and the measured before/after is recorded here | CEO | Reviewer |

## 7. Non-goals and falsifiers

Non-goals: embeddings or a vector database, a network service, a second memory
store, changing the on-disk format of the existing files, or an LLM in the
retrieval path.

- If a pack does not change the next action (no lane cites it), the pack is
  ceremony: reduce it to the pointer index and measure again.
- If `dream --apply` ever removes a record or edits a statement, the design is
  wrong and the pass is reverted.
- If pack bytes exceed the `load` they replace, the cap is doing its job - trim
  the prose, do not raise the cap.

## 8. M22 - what the article says that this engine still did not do (2026-11-09)

Read at `bc9b981`, against the same page as section 1. Five mechanisms the article
names were absent here; the sixth (a wiki representation) is deliberately deferred
with a falsifier rather than copied.

| # | component the article names | what the article says | this engine at `bc9b981` | M22 |
|---|---|---|---|---|
| 1 | transcripts as the foundation | "it's reasonable to consider transcript search as the foundation" of memory | `context find` and `recall` reach memory, lessons, knowledge, skills, docs and tasks - **not** `Ledger.jsonl` or `WorkLog.md`, so the transcript is written and never read | AC-M22-3 |
| 2 | a note carries how it was known | Opus 5 "included a rule (and also how it knew the rule was true)" | `evidence` is a free string; nothing ever re-checks it, so a note that was wrong from the start is trusted forever | AC-M22-1 |
| 3 | dreaming corrects against the transcript | the Mt. Moon note was checked against the session transcript and rewritten | `memory dream` compares records to each other (duplicate, contradiction, stale, no-evidence); it never compares a record to ground truth | AC-M22-1 |
| 4 | dreaming focuses on a goal | the LAB run rewrote its wiki-building instructions from its own failures: 41 of 57 facts, then 57 of 57 | the pass is fixed; every record is checked the same way whatever the team is doing | AC-M22-2 |
| 5 | the injected layer is a small index | Claude Code loads only "the first 200 lines or 25 KB of `MEMORY.md`", which "serves as an index" | `load` and the packet inject ranked *content* with no index of what exists, so a lane cannot know what it is missing | AC-M22-4 |
| 6 | a wiki representation | search alone 53%; search + wiki 54% -> 61% as the wiki grew; wiki alone 48%; the wiki can exceed the corpus (Borges) | no page store | deferred - see 12 |

The lesson this milestone takes from the article is the one section 2 already
states, applied one level down: **correction needs a ground truth**, and the
ground truth this engine already owns is the transcript (the ledger), the tree (a
path and a line) and the revision (`@sha`). Verify against those before writing
anything smarter.

## 9. `memory verify` - the correction pass (frozen contract)

```sh
tw memory verify [--role R] [--focus '<goal | T-id>'] [--limit N] [--json] [--apply] [--by X]
```

Evidence is parsed into **every** kind it carries, and the worst status wins
(`drifted` > `unverifiable` > `verified`); the reason names each kind that was
checked. Before T-0062 the pass stopped at the first match, so a drifted path
behind a valid revision passed:

| kind | shape | verified when | drifted when |
|---|---|---|---|
| revision | `@<sha>` or `rev <sha>` | `git cat-file -e <sha>^{commit}` exits 0 | the object is not a commit in this repository |
| path | `path/to/file:LINE` or `path/to/file` | the file exists and holds at least LINE lines | the file is missing, or shorter than LINE |
| source | `https://...` | the record also carries an access date (`accessed YYYY-MM-DD` or `(YYYY-MM-DD)`) not older than 400 days | the date is older than 400 days |
| none | anything else, including a source with **no** access date | - | reported `unverifiable`, never `drifted` |

The undated-source row was added after the first implementation read the table as
`drifted` and the Reviewer read it as `unverifiable`: a contract table has to be a
total function, and this one was not (`L-0002`). Silence is never drift.

Output is one line per record - `- [<id>] <kind> <verify_status> | <reason> | <pointer>` -
then `# verify: <N> record(s), <V> verified, <D> drifted, <U> unverifiable (limit <L>)`.
`--json` prints the same records as one object per line. Two runs on the same tree
and the same day are byte-identical.

`--apply` writes only two fields on **knowledge** records - `checked: YYYY-MM-DD`
and `verify_status: verified|drifted|unverifiable` - and appends one
`memory.verify` ledger event with the counts. It never edits a statement or an
evidence string and never deletes a record; lessons and short-term memory have no
such field, so they are reported and left byte-identical.

`memory dream` gains one group, `drifted`, computed by the same function, and
`--focus` selects and orders the records verified (9.1). The four existing groups
(duplicate, contradiction, stale, no evidence - the four `_print_dream_group` calls
in `_memory_dream`) keep their rules; nothing else about the pass changes.

### 9.1 `--focus` (frozen)

`--focus <text | T-id>` reuses the 4.1 score: a T-id resolves to the task title
through `memorypack.task_query`, then records are ranked by that query and the
first `--limit` (default 25) are verified; the rest are reported as
`# verify: N deferred by --focus`. Without `--focus` the order is pointer
ascending and `--limit` applies to nothing (every record is checked), so a plain
run is byte-identical to the pass before this milestone.

## 10. Transcript reach (frozen contract)

```sh
tw context find '<query>' --scope transcripts
tw recall '<query>' --agent <Role> --transcripts
```

Two sources, both already on disk and both append-only:

| source | pointer | one hit is |
|---|---|---|
| `<team>/Ledger.jsonl` | `Ledger.jsonl#<n>` (1-based line) | one ledger event |
| `Agents/<Instance>/WorkLog.md` | `Agents/<Instance>/WorkLog.md:<line>` | one worklog line |

Ranking is the 4.1 score over the hit's text; the output is capped at 10 hits and
2,000 bytes with the same `# search:` footer `memory search` prints; a rendered
hit clips its text to 200 characters. The reader streams the file line by line and
never holds the whole ledger, and `--scope transcripts` is additive - the other
scopes keep their output byte-for-byte.

## 11. The index header (frozen contract)

`load <Instance> [--task T]` and every lane packet open with the index, before the
pack:

```text
# memory index: <N> topic(s), <M> record(s)
- <topic> -> <pointer>
# index: <B> bytes (budget 800)
```

Topics are the distinct normalised `topic` of the active knowledge records plus the
open lessons' titles; order is the 4.1 score for the task (importance then uses
without one); at most 8 lines. The header is a pointer list - it never copies a
statement - and `INDEX_BUDGET_BYTES = 800`.

The measured constraint is the reason the header is small, and it was **revised**
after the first implementation failed three reviews on it (`D-0009`, ruling
`D-20261109-CEO-2`):

| # | the constraint, as ruled |
|---|---|
| a | `load` and every lane packet open with the index |
| b | the index is capped at `INDEX_BUDGET_BYTES = 800` and 8 topic lines |
| c | the index is charged against the same injected budget as the pack, so index + pack <= `PACK_BUDGET_BYTES = 4000`, and no cap is raised |
| d | where a role has verbose content to displace (open lesson rows, the `load` preamble) the index is net <= 0 on the whole output |
| e | where a role has no open lessons the index adds at most 800 bytes, pinned by a zero-open-lesson fixture test |

The original wording required the whole output never to grow. That is
unsatisfiable for a role with no lessons - the index has nothing to displace there -
and the article asks for a **capped** top layer (Claude Code loads only the first
200 lines or 25 KB of `MEMORY.md`), not for a shrinking one. The revision is recorded
rather than the finding dropped: the reviewer's measurements stand, and the
zero-lesson bound is now a test.

## 12. Non-goals, rejected alternatives and falsifiers (M22)

| rejected | why, with the evidence |
|---|---|
| a wiki page store now | the article's own numbers: no gain when one document answers, and a wiki can grow larger than the corpus. The store here is tens of records, not 350,000 files. Falsifier to revisit: **more than 200 active records, or a question that needs synthesis across records**. |
| embeddings or a vector index | the corpus is a few hundred small records; a deterministic token score is auditable and free, and an embedding service is a second store |
| an LLM in the verification path | verification must be reproducible and cheap: `git cat-file`, `stat`, a date parse |
| auto-rewriting a wrong note | the article's own correction was a rewrite, but a rewrite by a pass is unauditable. This engine marks `drifted` and leaves the rewrite to the owning role, which is what keeps `apply_dream`'s "never edit a statement" invariant |
| raising the always-on cap to fit the index | the cap is the constraint that makes the index small; if the index does not fit, trim the prose |

Falsifiers: if `memory verify` reports `drifted` on a record whose evidence is
true, the parser is wrong and the record is not; if the index header does not
change a lane's first action in three waves, it is ceremony and is deleted; if the
injected block grows past `bc9b981`, the header is over budget.

## 13. M22 - measured, on the merged revision

Every row is a command and its observed result. "Same store, back to back" means the
`bc9b981` renderer (`.pi/Scratch/ceo/baseline`) and the merged renderer were run one
after the other against one unchanged store, so the only difference is the code.
The store was live during the milestone (it grew from 0 knowledge records to 3), which
is why a count here is never reused as a constant elsewhere.

| surface | before (`bc9b981`) | after (merged) | command |
|---|---|---|---|
| `load Developer` (1 open lesson) | 2110 B | 1942 B (-168) | both renderers, same store, back to back |
| `load Developer --task T-0056` | 2309 B | 2141 B (-168) | same |
| `load CEO` (2 open lessons) | 2482 B | 1959 B (-523) | same |
| `load Tester` (no open lessons) | 1609 B | 1734 B (+125) | same; the index is 228 B, inside the revised 800 B bound |
| a 3-knowledge / 5-lesson fixture | 1827 B | 1177 B (-650) | `tests/unit/test_memory_index.py`, the literal captured from the `bc9b981` renderer on that fixture |
| a zero-lesson fixture | 1137 B | 1262 B (+125) | `tests/unit/test_memory_index.py`, bound `1137 + 800` |
| the index block itself | n/a | 403 B / 5 topic lines for CEO; 325 B / 4 for Developer | `load <Instance> \| sed -n '1,/^# index:/p' \| wc -c` |
| `memory verify --role ceo` | n/a | 68 ms, 5 record(s), 5 verified | `time` in a Python harness over the CLI |
| `memory dream --role ceo` | n/a | 66 ms, `drifted: 0`, the four original groups unchanged | same |
| `context find 'drift' --scope transcripts` | n/a | 93 ms over 2,358 ledger lines + every worklog, 885 B, `# search: 5 of 5` | same |
| a 100k-line ledger | n/a | streamed in < 1 s, `Path.read_text` refused by monkeypatch | `tests/unit/test_transcripts.py` |
| integration layer on a real tree | n/a | `1 verified, 3 drifted, 1 unverifiable`; `--apply` stamps 4 records and a second run writes nothing | `TS-0068` |
| the drift the pass found on the live store | n/a | `L-0003` reports `path drifted` (its evidence names a line that no longer exists) | `memory dream` |

Re-measured at `8a34759`, same method, on the store as it stands (7 CEO lessons,
one of them `L-0019`, written after the first reading) - the table above stays as it
was measured and this block is the current reading of the same surfaces:

| surface | before (`bc9b981`) | after (`8a34759`) | command |
|---|---|---|---|
| `load CEO` | 8112 B | 5455 B (-2657) | both renderers, same store, back to back |
| `load Developer` | 5746 B | 5776 B (+30) | same |
| `load Tester` | 4995 B | 5415 B (+420) | same |
| the index block itself | n/a | 523 B / 8 topic lines for CEO | `load CEO \| sed -n '1,/^# index:/p' \| wc -c` |
| the task pack for `T-0039` | n/a | 13 record(s), 3194 B (budget 3437) | `load CEO --task T-0039 \| tail -1` |

The two readings are the measurement, not noise: between them exactly one lesson was
written (`L-0019`), and `load CEO` moved +354 B on the `bc9b981` renderer (7758 ->
8112) and **0 B** on the merged one (5455 -> 5455). A verbose renderer pays for every
record the store gains; the capped index does not, which is the behaviour `AC-M22-4`
was ruled to buy and the reason a number here names its store state.
| every kind checked, worst wins (T-0062) | at `be86be4` the first matching kind decided, so `K-0011` (`@493219a` plus a path that is gone) read `revision verified` | `memory verify --role Developer` prints `- [K-0011] revision drifted \| revision: 493219a is a commit here; path: teamwork.py is missing`, and the footer counts it as drifted | `python3 scripts/teamwork.py memory verify --role Developer` |

What the four mechanisms do on this team, in one line each:

- **correction** (`memory verify`): a record is `verified` only when its own evidence still resolves - a commit that exists, a path and line that exist, a source with a fresh access date. Everything else is `unverifiable`, and only a resolved-but-stale evidence is `drifted`.
- **focus** (`--focus <goal|T-id>`): the pass checks the records the current goal ranks highest first, `--limit 25` by default, and reports how many it deferred. Without `--focus` the output is byte-identical to the unfocused pass.
- **transcript reach** (`context find --scope transcripts`, `recall --transcripts`): the ledger and the worklogs are now searchable with a pointer per hit, capped at 10 hits / 2,000 bytes, streamed line by line.
- **index** (the header): what the role knows and where it lives, at most 8 topics and 800 bytes, charged against the same budget as the pack.

## 14. Limitations this milestone leaves open

| # | limitation | evidence | follow-up |
|---|---|---|---|
| 1 | fixed by `T-0062` and measured in 13: every kind the evidence names is checked and the worst status wins, so a valid `@sha` no longer hides a drifted `path:line` | `memory verify --role Developer` -> `K-0011` reports `revision drifted` naming both kinds | closed |
| 2 | a lesson's index topic is its mistake sentence clipped at 60 characters, which reads as a fragment ("wrote "the five existing groups keep their rules" in the") | `load CEO` output | a follow-up only if a lane reports it unreadable |
| 3 | the stores are team-local and gitignored, and `privacy_scan` skips `.pi`, so no gate covers them | `scripts/privacy_scan.py:449`; security audit F3 | `T-0059` |
| 4 | the verification pass has no scheduler of its own: `pulse` prints the dream line, but nothing forces a `verify` run | `memory dream` output | acceptable - a pass nobody names is a pass that hides its cost |
| 5 | no wiki representation exists, by decision | section 12; `Research.md` | revisit above 200 active records |

## 15. M23 - memory in practice (frozen contract)

Frozen before any code lands, so the lanes that build it work from one text. Every
number below was measured at `0e9b5c6`, the revision this section is written
against; the command that produced it is in the same row. Sections 4, 9, 10 and 11
stay as they are: this section freezes the four components that section 14 still
leaves open (the short layer, the promotion rule, the dream cadence, the wiki) and
the injection order that carries them.

Four new constants are named here and do not exist in `config.py` yet;
`STALE_AFTER_DAYS` already exists in `memorypack.py` and moves to `config.py`
unchanged:

| constant | value | today | what it bounds |
|---|---|---|---|
| `PROMOTE_USES` | 2 | `MIN_USES` in `config.py` | uses that, on their own, promote a stale short entry (15.3) |
| `SHORT_INJECT_BYTES` | 600 | new | the short block inside the injected pack |
| `DREAM_BUDGET_SECONDS` | 2 | new | wall clock the dream pass may spend on a trigger |
| `WIKI_BUDGET_BYTES` | 1200 | new | one wiki page |
| `STALE_AFTER_DAYS` | 90 | `memorypack.py` | age at which an unused long entry is archived |

### 15.1 The short layer - capture

`Roles/<Role>/ShortTermMemory.md` stays the **one role-shared file**: every
instance of a role writes there and no instance gets a file of its own, because
the role is the unit that shares experience (section 3). At the freeze two of the
8 role stores hold one lane-exit entry each and the other six are empty:
`rg -c '^## M-' Roles/*/ShortTermMemory.md` at `ceef84a` -> `Architect:1`,
`Reviewer:1`, against 24 long-term entries and 48 lessons+knowledge.

An entry is the format `records.parse_memory` already parses and
`records.write_memory` already writes - one `## M-0001 · note` heading, a meta
block (`key`, `importance`, `uses`, `created`, `last_used`, `tags`, `pinned`, `by`,
`src`, `rev`), a blank line, then the body. `M-` ids are allocated per store by
`records.next_id` and are never renumbered, so a pointer into the file stays true.

Writers - exactly two, and neither is a background process:

| writer | when | entry it writes |
|---|---|---|
| the agent | during the run, through `remember <role> "<fact>" --by <instance> --src <T-id> --rev <sha>` (a single write takes the pen for its own duration) | `by` = the instance, `src` = the task, `rev` = the revision the fact was observed at, body = the fact |
| the harness | at lane exit, from the lane transcript `Agents/<Instance>/Runs/L-<nnnn>.md` | `key` = `lane:<T-id>`, `src` = the task id, `rev` = the branch head at exit, `by` = the instance, `importance` = 2, body = the task id, the lane's own outcome word (`ok`/`blocked`/`failed`) and the one-sentence result from the last `LANE-RESULT` line |

Rules that make the two writers safe together:

- **A lane that recorded nothing gets a harness entry.** That is the whole point:
  a lane's experience is lost today because nobody writes it down.
- **No duplicate.** The harness entry is skipped when the store already holds an
  entry with `src` = that task, so a lane that wrote its own note is not echoed.
- **Empty case.** A lane that ended without a `LANE-RESULT` line gets no harness
  entry; its ledger `lane.finish` record already carries `exit` and `result`, so
  nothing is invented.
- **Cap.** `SHORT_CAP` = 24 entries; overflow is resolved by 15.3, never by a
  silent truncation.
- **Pinned never leaves.** `pinned: yes` is the rule this role must never
  re-learn: it is exempt from staleness, from the cap and from demotion.

### 15.2 The injection contract - where the short layer appears

`load <Instance> --task <T-id>` and every lane packet print the same three blocks,
in this order, one after another:

```text
1  # memory index: <N> topic(s), <M> record(s)        <= INDEX_BUDGET_BYTES (800), 8 lines - unchanged
2  ## Short-term memory for this task                 <= SHORT_INJECT_BYTES (600), 5 entries
   - [M-0004] <body clipped to 160 chars> (uses <n>)
3  <the ranked pack, section 4.1>                      <= PACK_BUDGET_BYTES - index - short
```

The short block ranks the role's short entries with the 4.1 score over the same
task query and clips each body to 160 characters, one line per entry, so it is a
pointer list like the pack and never a copy of the store. Its own sub-cap is 600
bytes and 5 entries - a quarter of the pack, because a working note is cheaper to
re-derive than a lesson.

The budget arithmetic is the contract: `index + short + pack <= PACK_BUDGET_BYTES`
(4000), `index <= INDEX_BUDGET_BYTES` (800) unchanged, and `injected_budget()`
subtracts **both** the index and the short block today:
`rg -n 'spent = index_bytes' src/teamwork/memorypack.py` ->
`spent = index_bytes(...) + short_bytes(...)`. `AlwaysOnBudgetKb` is not raised: the short block is paid for by the
pack it displaces.

- **Empty case.** No short entries -> the heading and the block are omitted
  entirely, not printed empty, and the pack gets the full remainder.
- **Second call.** Same store, same task -> byte-identical output (`cmp` exit 0),
  as the pack is today; injection increments `uses` once per injected record per
  call and appends one `memory.pack` event.
- **Packet parity.** `lanes.build_packet` injects all three blocks through
  `engine.memory_pack_block`, so a spawned lane receives the short layer whether or
  not it runs a command.

### 15.3 The promotion rule - short to long, long to archived

One deterministic command, no model call, one named author:
`consolidate <role> --by <instance>` takes the role pen and is the only writer of
the long-term and archive stores.

Staleness is **age only**, and it is the one predicate the whole rule reads:
`stale(entry) = days_since(last_used) >= STALE_DAYS` (3). `uses` never make an
entry not-stale; they decide what happens to an entry that *is* stale. Promotion
is decided by **use alone**: a note earns long-term memory by being recalled, and
nothing else decides that.

| step | rule | destination | ledger action |
|---|---|---|---|
| pin | `pinned: yes` | stays short | none |
| keep | not stale: `days_since(last_used) < STALE_DAYS` (3) | stays short | none |
| promote | stale and `uses >= PROMOTE_USES` (2) | `LongTermMemory.md` | `memory.promote` |
| drop | stale and `uses < PROMOTE_USES` (2) | `ArchivedMemory.md` | `memory.drop` |
| overflow | more than `SHORT_CAP` (24) entries still short: the cut keeps the top 24 by the 4.1 `score`, and an overflowed record with `importance >= PROMOTE_MIN_IMPORTANCE` (2) | `LongTermMemory.md` | `memory.promote` |
| overflow-drop | the same overflowed record with `importance < PROMOTE_MIN_IMPORTANCE` (2) | `ArchivedMemory.md` | `memory.drop` |
| demote | long entry, not pinned, `uses == 0`, age > `STALE_AFTER_DAYS` (90) | `ArchivedMemory.md` | `memory.evict` |
| evict | more than `LONG_CAP` = 64 non-pinned long entries | `ArchivedMemory.md` | `memory.evict` |

The rows are **disjoint**, so no precedence order is needed between them: pin is
exempt by 15.1; a record is either not stale (keep), stale and used at least
`PROMOTE_USES` times (promote), or stale and used fewer times (drop); the two
overflow rows read only the records the cap cut, which the rows above have already
left short. A note lanes actually recall reaches long-term memory; a note nobody
uses is archived rather than kept, which is what bounds `SHORT_CAP` (24) in age,
while a burst of new notes is bounded by the overflow rows.

**Importance decides nothing about survival.** It keeps exactly two jobs: its
`0.20 * (importance / 5)` weight in the 4.1 `score`, which orders the pack and so
selects what the overflow cut drops, and the overflow split above. The boundary is
auditable against the writers, and their numbers are why this rule cannot read
importance: the harness lane-exit writer sets `importance` = 2 (15.1),
`remember --importance` defaults to 2 (`rg -n '"--importance", type=int, default=2'
src/teamwork/engine.py` -> `default=2`), and
`PROMOTE_MIN_IMPORTANCE` is 2 (`rg -n '^PROMOTE_MIN_IMPORTANCE'
src/teamwork/config.py`). A predicate of the
form `importance < 2` is false for every record either writer creates, so a drop
row that required it could never fire.

`STALE_DAYS` (3) is the short-layer window; `STALE_AFTER_DAYS` (90) bounds the
long layer in the `demote` row and is a different store's constant - one name per
store, no shared number.

**Superseded rule.** The first revision of this section (2d8e625) read
`keep = not stale OR uses >= MIN_USES` with `promote = stale AND uses >=
PROMOTE_USES AND importance >= PROMOTE_MIN_IMPORTANCE`. It is withdrawn: the keep
row subsumed the promote row, so nothing could ever be promoted, and the survive
conjunction would have archived a proven note that failed the importance test.
The table above replaces it; `MIN_USES` is retired and `PROMOTE_USES` is the only
uses constant this contract names.

**Second withdrawal (b0606e8).** The second revision of the table read
`promote = stale AND (uses >= PROMOTE_USES OR importance >= PROMOTE_MIN_IMPORTANCE)`
with `drop = stale AND uses < PROMOTE_USES AND importance < PROMOTE_MIN_IMPORTANCE`.
It is withdrawn as unreachable, not as unclear: both writers set importance 2 and
`PROMOTE_MIN_IMPORTANCE` is 2, so the drop row's `importance < 2` holds for no
record the team can create, the short layer could only ever promote, and the
`SHORT_CAP` bound the prose claimed was false. The table above replaces it;
importance is out of the survival rule and the use count alone separates promote
from drop. `D-20261111-Architect` in `Decisions.md` records the withdrawal and the
ruling it implements. `memory_session`'s stale predicate still implements
the old population (`rg -n 'stale = days_since' src/teamwork/engine.py` ->
`stale = days_since(e["last_used"]) >= STALE_DAYS and e["uses"] < MIN_USES`), which keeps a
frequently used note short forever and promotes only old rarely-used notes; T-0098
changes the code to this table, so this document is the corrected rule and the code
follows it.

A demotion **leaves a pointer**: the `memory.evict` event names the record id and
`Roles/<Role>/ArchivedMemory.md`, `recall` and `memory search` still find the
record there, and the archive keeps the statement unchanged. Nothing is deleted by
a promotion step; the one lossy path is archive overflow past `ARCHIVE_CAP` (256),
which is logged to `Runtime/MemoryLog.md` and is the existing behaviour.

`PROMOTE_USES` takes the number `MIN_USES` holds today (2, env
`TEAMWORK_PROMOTE_USES`); the rename is part of this freeze because "minimum uses"
never said *minimum for what*, and because one uses constant keeps the promote and
drop rows provably complementary. A record whose evidence is `drifted` (section 9) is
never promoted: a note that no longer resolves is not knowledge, and the pass
reports it instead.

### 15.4 The dream cadence - when the maintenance pass runs

Two triggers, both on a path that already exists, neither a daemon:

| trigger | what it prints | writes |
|---|---|---|
| every `lane start` | the dream line as the packet's second line | nothing |
| every `pulse` | the same line before it dispatches (section 4.2) | nothing |

- **Budget.** `DREAM_BUDGET_SECONDS` = 2 wall clock per trigger. Measured at
  `0e9b5c6`: `time teamwork.py memory dream --dry-run` -> 42 records, 0 duplicate,
  0 contradiction, 0 stale, 0 without evidence, 41 drifted, well inside the budget;
  section 5 measured 0.069 s over 45 records on the lifecycle branch.
- **Ground truth.** `Agents/<Instance>/WorkLog.md` and `Ledger.jsonl` (section 10),
  plus the tree and the revision for evidence - the three sources section 8 names.
  A record is `drifted` when its own evidence stops resolving (section 9); the pass
  reports it and never rewrites it.
- **Report shape.** The header `# memory dream (<mode>) for <subject>: N record(s)`,
  then one group per finding in this order - duplicate, contradiction, stale, no
  evidence, drifted - then the footer that names the acting command and the byte
  delta, and `deferred <n>` when the budget stopped the pass early.
- **`--dry-run` is the plan.** It prints the proposals and writes nothing.
  `--apply --by <you>` is the only writer: one `memory.dream` event per action with
  the ids and the byte delta, so a second apply over the same store is 0 actions
  and no new event (measured in section 5).
- **Stop condition.** Stop when every record in scope has been checked or
  `DREAM_BUDGET_SECONDS` elapses, whichever comes first; report what was deferred.
  A drift finding never blocks a lane start and never fails a gate on its own.

### 15.5 The wiki - page path, format and consultation

The wiki stays behind the falsifier in section 12 (>200 active records, or a
question that needs synthesis across records). What this section freezes is the
format, so the first page is not designed under time pressure. Today 42 records ->
no page exists.

```text
path   .pi/Teamwork/Teams/<Team>/Wiki/<slug>.md      slug = lowercase kebab
id     W-0001                                        allocated per wiki, never reused

# W-0003 - <one subject>

- sources: K-0007, L-0004, M-0012
- updated: YYYY-MM-DD

## Facts
- <one fact, one line> -> <pointer: record id | path:line | @sha>
```

| rule | what it forbids |
|---|---|
| one subject per page | a page that restates the store |
| links, not copies - every fact line carries the pointer of the record it came from | a fact with no provenance, and the Borges failure (the wiki outgrowing the corpus) |
| at least 2 source records per page | a page that answers what one record already answers |
| `WIKI_BUDGET_BYTES` = 1200 per page, at most 20 pages | an unbounded second store |
| the page is derived state: the records are the truth | a fact only the wiki holds |

- **Consultation.** `memory search` and `context find` rank pages with the same
  4.1 score over the page's fact lines and print `W-0003 -> Wiki/<slug>.md#L<n>`.
  Page hits share `SEARCH_BUDGET_BYTES` (2000) and `SEARCH_LIMIT` (10) with the
  record hits, so a wiki can never grow the read budget - it competes for the same
  bytes, which is what makes the A/B in section 12 measurable.
- **Prune.** At the dream pass, a page whose every fact points at a `superseded`,
  `archived` or `drifted` record, and which cannot be rewritten from an active
  record, is reduced to a one-line stub naming its sources or removed with one
  `wiki.prune` ledger event. A fact the pass cannot resolve is reported, never
  edited - the same invariant `apply_dream` holds.

### 15.6 The measurement table AC-M23-6 fills

Every row is a command and a number, so the criterion is checked by running it, not
by reading prose. `before` is measured at `0e9b5c6`; `target` is what the merged
M23 code must show, and the cell is `TBD` until the code lane records it.

| surface | before @0e9b5c6 | target | command |
|---|---|---|---|
| short entries written | 0 across 8 role stores | >= 1 per role that worked a task, and no lane that recorded nothing left empty | `rg -c '^## M-' Roles/*/ShortTermMemory.md` |
| `load Architect` bytes | 5,572 B | <= 5,572 B - the short block is paid for by the pack, not added | `teamwork.py load Architect --task T-0008 \| wc -c` |
| task-aware pack | 4,145 B against a 4,000 B budget | <= 4,000 B with the short block included in the arithmetic | `teamwork.py memory pack --role architect --task T-0008 \| wc -c` |
| pack determinism | two runs byte-identical | unchanged with the short block | `memory pack ... > a; memory pack ... > b; cmp a b` |
| dream wall clock | 42 records, inside 2 s | <= `DREAM_BUDGET_SECONDS` on every trigger, `deferred` named when it stops | `time teamwork.py memory dream --dry-run` |
| dream findings | 0 duplicate, 0 contradiction, 0 stale, 0 no-evidence, 41 drifted | no auto-rewrite: a drifted record is reported and never promoted | `teamwork.py memory dream --dry-run` |
| dream second call | 0 actions, no new event | unchanged | `memory dream --apply --by <you>` twice on a copy |
| wiki pages | 0, by the section 12 falsifier | 0 until a trigger fires; then every page <= 1,200 B with >= 2 sources | `find Wiki -name '*.md' \| wc -l`; `wc -c Wiki/*.md` |
| retrieval | `memory search review` -> 1,772 B | <= 2,000 B including page hits | `teamwork.py memory search review \| wc -c` |
| promotion | 24 long entries, 5 for Architect, none written by `consolidate`; at `0e9b5c6` `memory_session`'s stale predicate promotes only stale-and-rarely-used notes | every moved record satisfies 15.3: stale and `uses >= 2` is long, every other stale record is archived, importance decides only the overflow split, one ledger action per move, no record deleted | `consolidate <role> --by <you> --dry-run`; `rg -c '^## M-' Roles/*/LongTermMemory.md`; `grep -c 'memory.promote' Ledger.jsonl` |

### 15.7 Non-goals of this milestone

| not doing | why |
|---|---|
| embeddings or a vector index | a deterministic token score is auditable and free; an embedding service is a second store and a second failure mode |
| any third-party dependency | stdlib only, as sections 4 and 12 freeze |
| raising `AlwaysOnBudgetKb` | the cap is the constraint that keeps the layer small; the short block and the index fit inside it |
| a model call inside any pass | write, promote and dream must be reproducible from files alone |
| a new store outside `.pi/Teamwork/Teams/<Team>/` | the wiki lives under the team root, gitignored like the rest of `.pi` |
| a daemon, cron or background writer | both dream triggers sit on an existing command and write nothing |

Two facts a reader should not have to rediscover. First, the label `M23` is also
used for the pi-UI milestone in `Project.md`; this section is the memory milestone
the T-0008 brief names, and the CEO owns renumbering one of the two. Second, the
stores are team-local and gitignored, so no gate covers them yet (section 14 row 3);
every number above is reproduced by hand, and the row that measures it names the
command that does so.
