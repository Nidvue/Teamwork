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

### 4.3 `memory search` - one retrieval path over all four stores

`memory search <query> [--role R]` ranks lessons, knowledge and memory together
with the same score as the pack and prints the top 10 with their store and
pointer. `recall` keeps its current contract (short/long memory only) so no
existing script breaks; the new command is the one the docs point at.

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
