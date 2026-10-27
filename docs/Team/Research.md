# RESEARCH - Teamwork

Owner: Product Manager. Market context, comparable projects and the reasoning
behind the positioning. Every claim carries a source and an access date.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Archive](Archive.md)

## 1. The gap

Multi-agent orchestration is a crowded field, but almost every popular framework
is a **library you call from your own program**. Nidvue Teamwork is a **process you run
in your repository**: a prompt in, a staffed organisation out, with an evidence
gate before anything counts as done. The differences that are hard to copy are
the *governance* primitives, not the orchestration loop:

| Capability | Teamwork | Typical framework |
|---|---|---|
| Evidence gate before "done" | required record per task | convention / prompt |
| Independent second review | separate Reviewer role | optional |
| Append-only, hash-chained audit ledger | `Ledger.jsonl` + `ledger verify` | none |
| Role-shared memory + private workspace | one queue per role | per-agent |
| Zero runtime dependencies | stdlib only | large dependency tree |
| Works as a coding-agent skill | `SKILL.md` at repo root | n/a |

## 2. Comparable projects and what they prove

| Project | Model | Strength to learn from | Gap Teamwork fills |
|---|---|---|---|
| **CrewAI** | role-playing crews, sequential/hierarchical | crisp "crew of roles" metaphor; excellent docs | no evidence/audit gate; Python lib only |
| **AutoGen** (Microsoft) | conversational multi-agent, event-driven | async runtime, human-in-the-loop | heavy runtime, research-first |
| **MetaGPT** | SOP-driven software company | "software company" framing resonates | code-generation focused, not repo governance |
| **LangGraph** | graph/state machine for agents | explicit state, durable execution | framework, not an org; no ledger |
| **Aider** | terminal pair-programmer | zero-friction CLI, git-native | single agent |
| **Claude-Flow / swarm tools** | CLI swarms | star-worthy READMEs, quick demos | orchestration without verification |
| **Pi skills** | markdown skill bundle | distribution without a package | no installable engine/tests |

Sources: TELUS Digital's eight-framework comparison (2025-03-28), Arize's
orchestrator-worker comparison, and the ACM/Springer survey on agent-to-agent
communication all report the same pattern: orchestration is commoditised, while
*reliability and auditability* are the unsolved parts. That is the wedge.

## 3. What actually earns stars (evidence-backed)

1. **A demo above the fold.** A terminal/animated SVG that shows the value in
   under 10 seconds outperforms a wall of text (GitHub's own maintainer guidance).
2. **A one-line pitch plus a comparison table.** Readers decide in ~15 seconds;
   showing the alternatives answers "why not X" before it is asked.
3. **Copy-paste quickstart.** Install + first result in one block, no build step.
4. **Badges that are green.** CI, license, supported Python range, latest release.
5. **Topics and a description.** GitHub's search ranks on these; the SEO guidance
   for 2025 is explicit that description + topics + README keywords drive
   discovery.
6. **A license with a clear name.** AGPL-3.0 is a deliberate choice: it is
   OSI-approved, it is a strong copyleft signal for a governance tool, and it is
   unambiguous.
7. **Releases with assets.** A tagged release with a wheel, sdist and checksums
   signals a project that is maintained, not abandoned.
8. **A landing page.** A docs site on GitHub Pages gives the README somewhere to
   link and ranks separately in search.

Sources: GitHub Blog "5 tips for promoting your open source project"
(2025-02-06); freeCodeCamp "How We Got 4.5K+ GitHub Stars" (2022-01-26);
Liam ERD "What We Did to Gain 3,000 GitHub Stars" (2025-04-18); GitDevTool
"GitHub SEO Guide 2025" (2025-01-15).

## 4. Honest limits

* Stars are earned by real users, not by repository decoration. This project can
  only optimise the *conversion inputs* (README, topics, demo, install path,
  release). See [Risks](Risks.md) R-1.
* The name `teamwork` is taken on PyPI; the distribution ships as
  `teamwork-agents` while importing as `teamwork`.
* The engine still keeps one oversized module - `src/teamwork/engine.py`, the
  largest file in `src/` (re-measure it with `wc -l src/teamwork/engine.py` rather
  than quoting a number that moves); splitting it is a post-1.0 refactor, listed in
  the roadmap and in [Decisions](Decisions.md).

## 5. Recommendation

Ship a **v1.0.0** that is genuinely installable and testable on three operating
systems, with a README that leads with the demo and the comparison table, a docs
site, a tagged release with checksums, and repository metadata (description +
topics) set for discovery. Do not spend effort on features that do not appear in
the first screen of the README.

## 6. Lauren Tan (pstack): what we adopt, what we reject

Source set: pstack 0.15.9 (`cursor/plugins`, commit `e43c7ee`), Tan's two-part
guide (2026-08-31, 2026-09-10) and the 2026-10-05 synthesis of her talk, all
read as secondary sources. The 2,500-PR/month figure is self-reported and has no
independent benchmark, so it is treated as operational experience, not a KPI.

**The delta is not the thesis.** Both systems say "no claim without evidence".
The difference is *what counts as evidence* and *what the gate is bound to*:

| | Teamwork today | pstack |
|---|---|---|
| Unit of evidence | free-text `command @rev -> result` on a task/test record (`engine.py:_tests_mutate`, `cmd_selfcheck`) | an evidence **packet**: baseline state, action, resulting state, side effect, artifact, replay path |
| Proof of behaviour | a test command the agent chose | a harness that **drives the real product** (browser/PTY/API) and can be re-run by another agent |
| Navigation | the agent greps the repo each time | a maintained **Feature Map** (materialised memory of how to reach each feature) |
| Throughput limit | the **Reviewer**: every deliverable gets a full second review (`AGENTS.md` two-stage gate) | verification coverage; review becomes **sampling** once trust is earned |
| Repetition handling | COO risk register, PM duplicate detection | **gardener**: weed queue -> group by cause -> change the bed (architecture, types, lint, CI) |
| Prompt/skill quality | prose, self-asserted | **blinded evals** with a rubric and a cross-model judge |

### 6.1 Verdicts

| # | Technique | Verdict | Concrete surface in our code |
|---|---|---|---|
| A1 | Verification contract + Feature Map (launch/drive/observe/cleanup) | **Adopt** - biggest gap | new `verify` command group; contract at `.agents/verification/`, map at `.agents/verification/FEATURES.md`; `loop`/`tests` refuse an `acceptance` pass whose claim has no `verify run` record |
| A2 | Structured evidence packet, not a string | **Adopted** (T-0020) | `tests run` / `selfcheck` / `review` take `--baseline`, `--artifact`, `--replay`; artifacts are hashed into `Ledger.jsonl` |
| A3 | Repro-first: prove it fails before the fix | **Adopted** (T-0020) | `tests repro` records the fail->pass pair and checks ancestry; a `--bug` task cannot pass self-check without it |
| A4 | Tiered review + sampling | **Adapt** | `task add --tier docs\|code\|critical` derived from `area`/paths; `review --sample`; keep Reviewer-only merge and independence, reject unattended auto-merge |
| A5 | Gardener + encode-lessons-in-structure | **Adopt** | `teamwork garden` scan -> `docs/Team/Garden.md` queue; third repeat of one finding must cite a lint/CI/test record id |
| A6 | Blinded skill/role evals | **Adopt (later)** | `skill eval` with 3-6 criteria, N isolated worktrees, judge on a **different model family** (`teamwork model` already sets one model per agent) |
| A7 | Make the right path the easiest (architecture as constraint) | **Adopt** | split the oversized `src/teamwork/engine.py` into command modules behind an explicit registry (`src/teamwork/harness.py`, `records.py`, `layout.py` are the start); add an import-boundary lint so parallel lanes never edit one file |
| A8 | Guard the context window | **Adopt (cheap)** | `load --brief` and pulse digests that emit facts, not full files |
| A9 | Loop-closure metrics, not volume | **Adopt (cheap)** | `audit --metrics`: verification coverage, reproducibility rate, first-pass evidence completeness, review-fail rate, regression escapes |
| A10 | `reflect` at task close | **Adopt (cheap)** | `teamwork reflect <T-id>` proposes memory / skill / lint entries from findings and review fails |
| A11 | Throwaway prototype lane | **Adopt (cheap)** | `task add --kind prototype --review na`, artifacts in `Scratch/`, decision must cite the prototype path |
| A12 | Explain the number | **Adapt** | `decision add` demands baseline, method and variance for any measured number |
| - | 2,500 PR/month, agent count as maturity | **Reject** | volume is an output; our gate is loop closure |
| - | Agents merge their own code | **Reject** | collides with Reviewer-only merge and independence; sampling (A4) captures most of the speedup |
| - | Dune-specific bans (no `useEffect`, no comments) | **Reject** | project-specific policy, not a principle; every lint suppression in `src`+`scripts` carries a reason or a narrow rule (count them with `grep -rn noqa src scripts` and `grep -rn "type: ignore" src scripts`) |
| - | Cloud VMs per worker | **Out of scope** | the host supplies execution; the engine stays stdlib-only and host-agnostic |

### 6.2 Adopt first, in this order

1. **A2 + A3** (small, landed as T-0020): evidence is structured and a bug fix
proves the defect existed before it is fixed.
2. **A1** (large): a verification contract and Feature Map per area. Without it,
`acceptance` evidence stays a proxy the author picked.
3. **A5 + A9** (medium): garden queue plus loop-closure metrics. Converts our
review findings into CI rules and shows whether the human is still the loop.
4. **A4** (medium): tiering and sampling. Only after A1/A9, because sampling
without verification coverage is just less review.
5. **A7** (medium-large): engine split. Its value is that lanes stop colliding on
one oversized module; measure before/after on review-fail rate and merge conflicts.

**Falsifiers.** A2/A3 fail if first-pass review acceptance does not rise after ten
tasks. A1 fails if Feature Map maintenance costs more reviewer time than it saves
in agent turns. A4 fails if the regression escape rate rises above the pre-change
baseline. A7 fails if the split does not reduce merge conflicts or per-task
touched-file overlap.

### 6.3 What this does not fix

pstack assumes a product with a drivable surface and strong models with generous
context. A pure library, a compiler or a data pipeline has no UI harness, so A1
degrades to a service verifier (doctor, fixtures, observable state, cleanup) or to
nothing. Our differentiator - independent second review, hash-chained ledger,
role-shared memory - is not in pstack and must not be traded away for throughput.

## 7. Sources

- [Agentic Framework Showdown: We Tested 8 AI Agent Frameworks - TELUS Digital](https://www.telusdigital.com/insights/data-and-ai/article/8-agentic-frameworks-tested) - accessed 2026-10-17
- [Orchestrator-Worker Agents: Comparing Agent Frameworks - Arize](https://arize.com/blog/orchestrator-worker-agents-a-practical-comparison-of-common-agent-frameworks/) - accessed 2026-10-17
- [Agentic AI Frameworks: Architectures, Protocols, and Design Challenges - arXiv](https://arxiv.org/html/2508.10146) - accessed 2026-10-17
- [5 tips for promoting your open source project - GitHub Blog](https://github.blog/open-source/maintainers/5-tips-for-promoting-your-open-source-project/) - accessed 2026-10-17
- [How We Got 4.5K+ GitHub Stars on Our Open Source Project in 6 Months - freeCodeCamp](https://www.freecodecamp.org/news/how-to-get-more-engagement-with-your-open-source-project/) - accessed 2026-10-17
- [What We Did to Gain 3,000 GitHub Stars for the Liam Repository - Liam ERD](https://liambx.com/blog/liam-github-3k-stars) - accessed 2026-10-17
- [GitHub SEO Guide 2025 - GitDevTool](https://www.gitdevtool.com/blog/github-seo) - accessed 2026-10-17
- [Multi-agent orchestration visual summary - Bhaskarjit Sarmah](https://bhaskarjsarmah.github.io/visual-summary/52-agent-orchestration/) - accessed 2026-10-17
- [Lauren Tan and pstack: verification, evals, and building agents that can prove their work - Technical Notes](https://blog.lionet.vn/en/posts/lauren-tan-pstack-verification-agent-engineering) - accessed 2026-10-19
- [On pstack: the skills behind 2,500 PRs a month, and the mental models behind the skills - Barnaby Robson](https://barnabyrobson.org/on-pstack/) - accessed 2026-10-19
- [How Lauren Tan Ships Thousands of PRs a Month - Intelligent Artifact](https://intelligentartifact.com/posts/how-lauren-tan-ships-thousands-of-prs-a-month/) - accessed 2026-10-19
- [pstack source, cursor/plugins at e43c7ee - Cursor](https://github.com/cursor/plugins/tree/e43c7ee/pstack) - accessed 2026-10-19
- [Harness^2: Recursive Agent Harnessing for an Open World - arXiv:2610.14224](https://arxiv.org/abs/2610.14224) - accessed 2026-10-20
- [google-research/harness2 - Google Research](https://github.com/google-research/harness2) - accessed 2026-10-20
- [Measuring multiagent systems - Anthropic](https://www.anthropic.com/research/multiagent-systems) - accessed 2026-10-27

## 8. Harness^2 (Google Research): what we adopt, what we reject

Source set: [google-research/harness2](https://github.com/google-research/harness2) (Apache-2.0, 13,409 stars at access, "not an officially supported Google product") and [Harness^2, arXiv:2610.14224](https://arxiv.org/abs/2610.14224), both read 2026-10-20. Every number below is the paper's own, on the paper's three professional benchmarks (WorkBuddy-Bench, JobBench, Harvey LAB); none is reproduced here and none measures a system like ours.

**The delta is not the thesis.** Both systems improve a harness around a frozen model - `Agent = Model + Harness` on their side, skill + engine + role charters on ours - and the difference is what counts as evidence and what the gate is bound to: they optimise *without* ground truth because their premise says no verifier exists ("tasks typically lack ground-truth labels or reliable verifiers"), while every gate here is bound to an acceptance criterion, an independent review and a revision-bound evidence record. So we adopt their contrastive machinery **only in the residue where we have no verifier** - doc prose, research quality, plan shape, role behaviour - and refuse contrast as a substitute for verification wherever a criterion record already exists.

### 8.1 Where we are already stronger

| Dimension | Teamwork | Harness^2 |
|---|---|---|
| What the verdict is bound to | an acceptance criterion, an independent review, a hash-chained record | a behavioural contrast; the selected harness is `H*` where "the star indicates adoption rather than verified optimality" |
| Independence | the author never closes its own task; Reviewer-only merge; 3 review fails -> dispute -> tribunal | editor and selector are one model (Claude Opus 4.8), and the paper concedes the shared-bias confound itself |
| Provenance | `Ledger.jsonl` hash-chained, evidence artifacts hashed, `trace` end to end | deliverables, adopted harnesses and reflection notes under `runs/`; nothing is revision-bound |
| Evidence shape | `command @rev -> result`, plus `--baseline`/`--artifact`/`--replay`; a bug proves its failing run first | a step record `xi` inside the paper; the released tree keeps the artefacts, not the decision |
| Runtime | stdlib only, offline, no credentials | Python 3.12 + uv, Vertex AI credentials, Docker for WorkBuddy-Bench, Pandoc/Poppler for LAB |
| Cost governance | provider slot leases and caps (`teamwork.py slot`) | measured compute-performance trade-off (Fig. 6), not budgeted and not capped |
| Anti-spin | 3 failed reviews escalate to a binding tribunal ruling | none stated; a wrong premise propagated across candidates (Fig. 14) |

### 8.2 Where they are stronger

| Dimension | Teamwork | Harness^2 |
|---|---|---|
| The harness is a named surface | `AGENTS.md` + `roles/*.md` + `references/*.md` + `.agents/skills/*/SKILL.md` - same kind of surface, no inventory | 8 file-level components, each with an activation class (every call / skill tool / bash / task tool / inside the tool loop) and a stated cost |
| Validation before the work | `teamwork.py links`, `teamwork.py audit`, `teamwork.py loop` run at submit time, after the work exists | 3 invalidators discard a whole proposal before any rollout: unnamed skill, template braces in always-on text, a script the proposal does not ship |
| Cost doctrine per component | "cap each section at roughly one screen", with no ordering between component kinds | skill > script > subagent > plugin > always-on, and "if you add always-on text, cut something else to pay for it" |
| Scoped proposers | a proposal is one undifferentiated plan | INV (how the agent works) and DOM (what a practitioner knows) proposed separately; removing the split costs 2.9 (WorkBuddy) and 3.7 (JobBench), the largest single loss on JobBench |
| A contrast as a first-class record | evidence is one command string per task | reference execution, candidate harnesses, their diffs, probe outcomes and one composition decision per edit, all recorded |
| Enforce over instruct | red lines are prose; the engine enforces only a few (branch, identity, author != reviewer) | component C8 acts in the tool loop, where prose cannot be skipped |
| Lessons carry a confidence | `.agents/skills` entries carry no evidence row and no confidence | cue / lesson / evidence / confidence, `confounded` preferred over invented attribution, `NO_ENTRY` a valid answer |
| A harness-level effect size | no experiment on whether a harness change helps | 3 benchmarks x 4 executor-harness configurations, k=1..5, per-component ablations, nine published failure cases |

### 8.3 Verdicts

Every `teamwork.py` subcommand named below exists in this revision; `tests/unit/test_research_sources.py` fails if this section ever names one the CLI does not have. The `harness` group and `hooks install` that this section used to call "the day it lands" **have landed**: `python scripts/teamwork.py harness --help` exits 0 listing `list`, `lint` and `budget`, and `python scripts/teamwork.py hooks install --help` exits 0, so H1, H3 and H4 are pinned to those real surfaces instead of to a promise. What is still an addition is the *content*, not the command: H1's inventory of activation classes and costs is printed by `teamwork.py harness list`, its budget verdict by `harness budget`, and H5's review order is prose in `roles/reviewer.md` - 8.4 sequences the rest.

| # | Technique | Verdict | Concrete surface in this repo | Falsifier |
|---|---|---|---|---|
| H1 | The harness as a named surface with an activation class and a cost | **Adopt** | `python scripts/teamwork.py harness list` prints every surface with its activation class (always-on / on-demand / in-loop) and size - `AGENTS.md` managed block, `roles/<role>.md`, `references/*.md`, `.agents/skills/<name>/SKILL.md`, `scripts/*.py` + `src/teamwork/*.py`, the git hooks; `teamwork.py map` prints the layout, `teamwork.py stats` the memory size and cap violations | the inventory names a surface no test reads, or the tree grows one nobody listed - a list that drifts is worse than none |
| H2 | Always-on budget: cut something to pay for it | **Adopt** | `references/Docs.md` ("cap each section at roughly one screen"), the `AGENTS.md` writing standard, `teamwork.py stats` (per-agent size and cap violations) | the cap is raised instead of the text cut, twice in a row |
| H3 | Whole-proposal invalidators, checked before a rollout | **Adopt** | `teamwork.py links` (a broken link, a malformed or bare URL, a missing back-link fails it), `teamwork.py audit`, `teamwork.py loop` (refuses the stop condition while a required layer is missing or failing) - **new**: the same checks moved earlier, to submit time | `teamwork.py links` reports 0 on a revision a Reviewer then finds a dead link or a skill nobody can reach |
| H4 | Middleware: enforce, do not instruct | **Adopt** | already in the engine, not in git hooks: `teamwork.py commit` (refuses the default branch, applies the role identity), `teamwork.py review` (refuses the author's own verdict), `teamwork.py tests repro` (refuses a fix with no failing run before the passing one) | a check fires on a legitimate workflow, agents learn the bypass, and the rule has to move back into prose |
| H5 | Ordered, anonymised artefact selection | **Adapt** | **new** review order in `roles/reviewer.md`, claimed through `teamwork.py review --queue`: we take the order (delivered, shaped as asked, faithful to source, internally consistent, fit to use, finished, and our own last gate - the evidence reproduces) and drop anonymity, because the Reviewer verifies the author's evidence on the revision | first-pass review acceptance falls, or findings shrink to style notes, once the order is written down |
| H6 | Scoped proposers, INV vs DOM | **Adapt - doctrine only** | a proposal names its scope: `inv` (how the team works - `AGENTS.md`, `roles/`, `references/`) or `dom` (what the domain knows - [Research](Research.md), [Project](Project.md)), recorded with `teamwork.py decision add --kind` | after ten recorded proposals the scope label predicts nothing about which proposal was adopted |
| H7 | Contrastive Propose-Probe-Compose | **Adapt - verifier-first** | propose = `teamwork.py branch` plus a diff; probe = the same recorded evidence command re-run on the same revision (`teamwork.py tests run --baseline --artifact --replay`); compose = one `teamwork.py decision add` row per adopted edit, with `--evidence` and `--falsify` | a composed change cannot name the execution that motivated it |
| H8 | Library entries with cue / lesson / evidence / confidence, `confounded` preferred, `NO_ENTRY` valid | **Adopt** | `.agents/skills/<name>/SKILL.md` (`teamwork.py skill create --for --body-file`) and the one-line form `teamwork.py remember --src --rev`; both "no change" verdicts written down as valid | skills accumulate with `confounded`-only evidence and nobody prunes them, so the library degrades into prose |
| H9 | Exploration budget; parallel vs sequential | **Adapt - doctrine only** | `SKILL.md` section 5a ("parallelism is the default, not the reward"), `teamwork.py parallel`, `teamwork.py slot`: probe width belongs to lanes, and the engine never churns one skill through k rewrites | the doctrine never changes a scheduling decision - lanes still serialise and the paragraph is decoration |
| H10 | Untrusted material is data, not instructions | **Adopt** | `references/Evidence.md` (anti-hallucination protocol, red lines) and the `AGENTS.md` managed block - doctrine only: no engine check refuses an instruction-shaped artefact today | an agent follows an instruction embedded in a fetched page or a candidate artifact and no gate catches it |
| - | Model-backed harness search, benchmark-driven editors | **Reject** | the engine stays stdlib-only and calls no model (`src/teamwork/`, `scripts/teamwork.py`); the editor is a role lane, not a module | a task's completion can only be established by a model run, and no criterion record can carry it |
| - | Inheriting a refined harness across tasks | **Reject** | collides with frozen interfaces ([Architecture](Architecture.md)) and with role-shared state (`roles/<role>.md` is one copy for every instance) | two lanes inherit one tree state and a role charter changes under them with no reviewed diff |
| - | Label-free as a design goal | **Reject** | we have criteria records and a repro gate (`teamwork.py criteria`, `teamwork.py tests repro`); label-free is their constraint, not our virtue | an acceptance criterion ships with no test that can fail |

### 8.4 Adopt first, in this order

1. **H10 + H5 + H2** (docs and one printed number): no engine risk, and they bind the prose the other seven rows depend on.
2. **H1 + H3 + H8** (one inventory, one validator, one evidence line): deterministic, unit-testable, and they give the doctrine rows a place to land.
3. **H4** (already enforced in the engine; the open half is opt-in git hooks): touches every commit, so last of the mechanical rows.
4. **H6, H7, H9** (doctrine, after H1/H3 name and validate the surface).

**Only the doctrine is adopted for H6, H7 and H9, and the reason is one constraint.** Their pipeline has a model proposing and a model composing on every task; ours has no model in the engine and a lane already holds a slot lease, so the model-backed half cannot ship here. What transfers is the discipline, and it costs nobody an execution:

- **H6** - a proposal must declare whether it changes how the team works (`inv`) or what the domain knows (`dom`), and the two are argued separately. Their ablation is the case for it: two scoped proposers beat two generic ones by 2.9 on WorkBuddy-Bench and 3.7 on JobBench (Gemini 3.5 Flash, OpenCode, k=1). No scoped editor is built.
- **H7** - propose is a branch and a diff, probe is the evidence command re-run on the same revision, compose needs one decision row per edit with its observation. The probe is an execution we already pay for, not 2k candidate rollouts. No composer is built.
- **H9** - width is a scheduling choice: k parallel probes are k lanes (`teamwork.py parallel` says how many are free), not k rewrites of one skill. Sequential recursion is rejected for us anyway: it carries a refined harness forward, which is the inheritance we reject below.

**Falsifiers.** The whole adoption fails if first-pass review acceptance does not rise after ten tasks, if `teamwork.py links` / `teamwork.py audit` findings shrink to style notes, or if the scope label in H6 changes no decision. The doctrine rows fail cheaply, which is why they come last.

### 8.5 What this does not fix

- **No model in the engine, so no reproduction of their numbers.** The +11.5 points are GLM-5 under OpenCode on WorkBuddy-Bench (64.2 -> 75.7), +4.5 is Gemini 3.5 Flash under OpenCode on JobBench (31.5 -> 36.0), +11.8 percentage points is GLM-5 under OpenCode on LAB Partial (59.6 -> 71.4) - one improvement step each, on benchmarks whose rubrics never reach the editor. We cannot reproduce any of it offline and must not quote it as if we had.
- **Parallel recursion costs executions we do not have.** k=5 means k reference runs, 2k probes and k compositions per task; it adds a further 2.9-3.9 points on WorkBuddy-Bench, 3.0-4.2 on JobBench and 2.6-6.7 on LAB Partial, and Fig. 6 shows the gains (4.5 -> 7.5 on JobBench, 5.1 -> 8.4 on WorkBuddy-Bench for Gemini 3.5 Flash/OpenCode) sitting on their own compute frontier. Ours is bounded by provider caps, so width is bought with a slot lease.
- **Contrast is not correctness, by their own account** - "sensitive to execution variability and shared model biases", and transfer is not guaranteed. They are not uniformly ahead either: Meta-Harness leads LAB Partial for Gemini 3.5 Flash under Codex (76.5 vs 75.6), and Harness Scaling lands below its own base harness in seven of twelve pairs. A signal that can lose must never become our gate.
- **Their selector has no way to notice a bad pick.** Of nine regressions in three groups: a 55 chosen over a 95 on WorkBuddy-Bench code, narrower coverage taking LAB from 54 to 26, and an unchecked cache assumption propagating a 2-11 point loss across candidates. Our gate exists for exactly this - independent review, hash-chained ledger, criteria records (`teamwork.py criteria`), repro-first bugs - and H5 keeps the order while dropping the anonymity that would blind the Reviewer to it.
- **What we must not trade away:** independent review (`roles/reviewer.md`: the author never closes its own task), the hash-chained `Ledger.jsonl` with `teamwork.py ledger verify`, criteria records, and the repro pair. No row above may turn a criterion into a preference.

## 9. Anthropic: multiagent coordination failures (what we adopt)

Source: [Measuring multiagent systems](https://www.anthropic.com/research/multiagent-systems), accessed 2026-10-27. All numbers are the paper's own experiments; none is reproduced here.

| Finding | Verdict | Surface | Falsifier |
|---|---|---|---|
| Coordination is environmental, not a capability | **Adopt** | `teamwork.py coordination` checks and `references/Coordination.md` | high findings persist after the mechanisms land |
| Shared model/context makes lanes fail together | **Adopt** | `TEAMWORK_MODEL_ALT` in `model auto`, `C-DIV-MODEL`; duplicate branch/task checks | one-model Reviewer lanes still catch defects a second model would |
| Starved queues cause polling stampedes | **Adopt** | `pulse` defers new lanes past free slots; slot leases; `C-CAP-STARVED` | over-subscription or busy-polling recurs |
| Incompatible directives escalate into sabotage | **Adopt** | reclaim refuses a live lane, no-resource-denial red line, contest-then-CEO ladder | a lane denies a peer a resource |
| Gullibility and premature consensus | **Adapt** | blind-first review, unique-evidence note, source+date, contradiction over averaging | a unanimous wrong verdict passes review |
| Collusion and rubber-stamping | **Adopt** | `C-TRUST-ECHO`, `C-TRUST-MONOCULTURE`, sampled second review | a zero-finding lane is never sampled |
| Merge collapse and abandoned PRs | **Adopt** | one branch per task, rebase before review, `C-MERGE-*` | merge fraction stays below 0.5 |
| Taste is not emergent | **Adopt** | milestone demo to the user; Designer owns assets | a user-facing deliverable ships unreviewed by a human |

### 9.1 What this does not fix

- The paper measures its own swarms, not this engine; no count transfers.
- The checks read records, not intent. A green report is the absence of known signatures, not proof of good coordination.
- Human taste still needs a human: the milestone demo is a gate, and a poor demo is a finding, not a reason to lower a criterion.
