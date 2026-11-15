# RESEARCH - Teamwork

Owner: Product Manager. Market context, comparable projects and the reasoning
behind the positioning. Every claim carries a source and an access date.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Archive](Archive.md) · [Roles](../../references/Roles.md)

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

## 10. DeepSeek dsh-superagent: what we adopt, what we reject

Source set: the prototype repository
[deepseek-ai/dsh-superagent-prototype](https://github.com/deepseek-ai/dsh-superagent-prototype)
(MIT, 6.3k stars at access, README marked "research prototype, not an official
DeepSeek product") and the documents read there:
[000 Philosophy](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/000-philosophy.md),
[001 Domain model](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/001-domain.md),
[002 Authorization](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/002-authorization.md),
[003 Execution](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/003-execution.md),
[007 Architecture](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/007-architecture.md)
- all accessed 2026-11-01. No number below is theirs measured on our tree; each
row names the record this team must produce before the claim is true.

**The delta.** Both systems are an agent wearing a team's process, and both keep
one writer per state. The difference is *where the gate is*: every gate here is
bound to an acceptance criterion, an independent review and a revision-bound
record, while theirs is bound to an **authorization model** - a Mandate carrying
the policy version it was granted under, an accept mode deciding whether
proactive work may run, and a stage table deciding what a person must do next.
We already have the first half and omitted the second: `task add` accepts any
work from any caller, `pulse` assigns proactively with no authority test, and
"what needs a person" is inferred from free text by whoever reads the board.

| Their mechanism | What it fixes for us | Verdict | Surface | Falsifier |
|---|---|---|---|---|
| Mandate = strength + scope + policy version, immutable, revalidated before resume | a task exists with no recorded reason it was allowed to start | **Adopt** | `task add --mandate explicit\|inferred --basis`; the board shows the strength | an inferred task is claimed with no recorded basis |
| Accept mode `off` / `observe` / `auto` for proactive work | `pulse` assigns on the first wake, so a mis-shaped proactive rule costs a whole lane before anyone sees it | **Adopt** | `PulseMode` in `Settings.json`, `pulse --mode`, `pulse.observe` ledger record | `observe` claims anything, or an `inferred` task is claimed outside `auto` |
| Idempotent intake ("accepting a Trigger twice creates one Ticket") | the same request re-added by a second lane becomes duplicate work | **Adopt** | `task add --key`, duplicate returns the existing id | two tasks carry one key |
| Ticket stage table, first match wins, computed from records | "what needs a person" is guessed from a long report | **Adopt** | `stage` command, `attention` queue | a blocked deliverable shows as working |
| Attention as a first-class record, a healthy state takes no space | an escalation lives in a message that scrolls away | **Adopt** | `attention add\|list\|resolve`; `loop` counts open items | an open authorization is not visible at the STOP check |
| Policy version + revalidation on change | a gate change silently applies to work already accepted | **Adapt** - record the gate set on the task, do not revoke mid-flight (a half-finished change is worse) | `--policy` stamp at intake | a task accepted under an old gate is reverted rather than recorded |
| Source/Trigger/Thread/Subscription fan-out model | our units are already tasks, tests, criteria; a second vocabulary would be a concept we do not need | **Reject** | - | - |
| Durable effect queue with per-kind retry/backoff | the ledger is already append-only and the tree survives a restart | **Reject** | - | a lost record after a restart |
| Allow-list per Source, admission table, bot list | we have one operator and one repo; the roster is the allow-list | **Reject** | - | an unlisted actor starts work |
| Panel UI | the committed documents and `board` are the panel; a web UI is a second surface to keep true | **Reject** | - | a decision exists only in the UI |

### 10.1 What this does not fix

- The prototype is a single-repository, single-operator design. Its queue
  discipline assumes a worker per ticket; our lanes hold several and the review
  queue is the real limit, so the stage table classifies, it does not schedule.
- A Mandate proves *that* a reason was recorded, never that it was a good one.
  The review gate and the criterion records still carry the quality claim.
- An attention queue is only honest if it is drained: an item resolved with a
  free-text "ok" is the same failure as a rubber-stamped review.

## 11. Lauren Tan (Grok Bot team guide): what we adopt, what we reject

Source: [Lauren Tan, Grok Bot team guide](https://x.com/poteto/status/2116576229319233596) - accessed 2026-11-02; [dr eggbot](https://x.ai/bot/_jOdbfkB16zxu7MRcmReE) - accessed 2026-11-02. The guide is seven operating tips from the xAI Grok Bot team; the replies add the least-privilege correction, the proactivity/SOUL thread and five field complaints. It is operational experience, not a benchmark: no number in it measures this project.

**The thesis is ours already:** the unit is the team, not the prompt. Six tips map
to an existing surface, two are adapted, one is rejected in its literal form.

| Tip | Teamwork surface | Verdict | Concrete rule |
|---|---|---|---|
| Add a bot designer (dr eggbot) | no meta-agent | **Adopt** | `tw-team-designer` team skill: interview, roster/skills/permission/routine audit, one-page design |
| Few good bots, not many | slim roster; `audit` roster gaps | **Adopt, strengthen** | every seat names a deliverable, a test layer and a decision right; the designer audits it |
| Bots write their own skills | `.agents/skills/`, `skill create`/`share`/`candidates` | **Adopt, strengthen** | an instruction that defines a repeatable flow becomes a skill in the same task |
| Connectors, vault, all tools | red lines and the review gate | **Adapt - reject "all tools"** | least privilege, one job, one proof per deliverable; no bot-owned email or accounts |
| Remove copy-paste | board, memory, records | **Adopt** | no human relay: a manual relay is a tooling defect, recorded with `attention` |
| Onboard an intern | startup routine and task packet | **Adopt** | restate goal, acceptance and non-goals before planning; the CEO confirms |
| Voice dump + restate | text-only host | **Adapt** | the restatement check applies to the brief; a scope-changing restatement is a requirement change |
| Proactivity / SOUL.md | `pulse`, `attention`, inferred tasks | **Adapt** | proactivity is a record: an idle lane proposes one automation/risk, never silent autonomy |
| Routines | loop/pulse, `harness budget` | **Adopt (cheap)** | trigger + budget + stop condition; a heavy routine gets its own lane |

**The correction that matters.** The guide says to give a bot access to all the
tools. The top reply (CobaltHere) is right for any team with more than one agent:
a clear job, limited permissions, and a way to prove the task was completed;
skills help consistency, verification helps trust; the goal is the smallest team
that reliably ships, not the largest. We adopt the correction and reject the
literal tip. The guide's own field complaints point the same way - routines that
do not fire, agents that skip steps, one persistent thread that burns tokens -
are verification, reliability and context-budget problems, not prompt problems.

**Adoption order.** (1) the `tw-team-designer` skill and the intern protocol (this
change); (2) the skills trigger, now hard; (3) the per-role permission and
verification matrix inside the designer; (4) the proactivity and routine audit on
the pulse. The first two change behaviour cheaply; the last two are audits, not
new machinery.

**Falsifiers.** The designer failed if, after ten designs, the roster does not
shrink or the first-pass review rate does not rise. The intern protocol failed if
the no-relay rule produces no automation task in a week. The routine rule failed
if `harness budget` does not fall for the lanes that move routines out. Each is
measured from the records, not asserted.

### 11.1 What this does not fix

- The guide assumes a hosted chat product with connectors and a voice mode. We
  have one repository, one operator and a red line on external actions; the
  "own email and accounts" tip is exactly the line we do not cross.
- A bot designer is an interview and an audit, not an org chart generator. It can
  recommend the smallest roster; it cannot prove the model will execute it.
- Proactivity is bounded by the pulse and the attention record. A designer that
  proposes work no lane approved is the rubber-stamp failure in another costume.

## 12. Framework comparison (2026-11-02): what we learn, adapt and adopt

Method: three official documentation pages, read in full, compared against the
mechanisms this repository ships (measured in the project review, see
[Risks](Risks.md) R-25 to R-32). Sources: [CrewAI processes](https://docs.crewai.com/en/concepts/processes) - accessed 2026-11-02;
[OpenAI Agents SDK, handoffs](https://openai.github.io/openai-agents-python/handoffs/) - accessed 2026-11-02;
[LangGraph, persistence](https://docs.langchain.com/oss/python/langgraph/durable-execution) - accessed 2026-11-02.

| Framework | What the documentation says | Our equivalent | Verdict |
|---|---|---|---|
| CrewAI | Sequential or hierarchical process; in the hierarchical case a manager agent plans, delegates, "reviews outputs, and assesses task completion". | CEO decomposition plus an independent Reviewer who is never on the author's line. | **Keep ours.** A manager that judges its own team's output is the failure our Reviewer-only merge exists to prevent. |
| OpenAI Agents SDK | A handoff is a tool, one per destination; `input_type` validates the handoff's arguments locally; `input_filter` controls what history the next agent sees; input guardrails apply only to the first agent and output guardrails only to the final one. | Task packets and CLI records; actor and role validation; review and preflight on every deliverable. | **Adapt.** Our gates are stronger (every deliverable, not the first and last agent). Typed input validation at the handoff is a real gap: a task packet is free text until the review reads it. |
| OpenAI Agents SDK, history | Filters choose what the receiving agent sees; the SDK warns that a summary can still carry redacted content. | the root `AGENTS.md` managed block loaded in full, SKILL.md always-on (R-31). | **Adopt the principle.** Decide per section what every instance loads; move the rest to on-demand references. |
| LangGraph | Checkpointers persist thread state for resume, human-in-the-loop, time travel and fault tolerance; stores hold cross-thread memory; the docs warn that checkpoints "accumulate" and recommend "prune old checkpoints ... or set a retention policy". | Hash-chained `Ledger.jsonl` and the records; the evidence archive has no retention (R-25). | **Adopt the retention warning, keep our chain.** LangGraph state is not tamper-evident; ours is, which is the strength to keep. The warning describes our own R-25 exactly. |
| LangGraph, resume | A run resumes from the last checkpoint after an interruption. | Task status and the slot lease; a lane that dies loses its in-flight state unless it wrote a record. | **Adapt.** A lane's progress should be a record written before risky steps, so a reclaimed task resumes from its last record rather than from a summary. |

**Conclusions for this repository.**

1. Our differentiator is the independence and the tamper evidence, not the agent
   graph. Two of the three frameworks put review in the same agent graph; we do
   not, and the comparison says that choice is right.
2. The weaknesses the comparison exposes are the ones the project review already
   found: unbounded evidence growth (the LangGraph retention warning), context that
   every instance pays for (the SDK's history filters), and free-text handoffs (the
   SDK's typed `input_type`).
3. Candidate work, not yet scheduled: validated fields on a task packet at
   `task add` (the handoff analogue), and a per-lane progress record written before
   each risky step (the resume analogue). Each needs an owner and a falsifier before
   it becomes a task.

**Falsifiers.** The retention decision (R-25) fails if a records read over the new
segments is slower than the current whole-file read. The typed packet fails if
review rounds per task do not fall within ten tasks.

**What this does not cover.** Benchmarks. None of the three pages reports a
measured outcome for a multi-agent team, so the comparison ranks design choices,
not performance.

## 13. OpenViking: what we adopt for lessons, experience, knowledge and memory

Source: [OpenViking](https://github.com/volcengine/OpenViking) - accessed
2026-11-03. Architecture and concepts read at
[architecture](https://docs.openviking.ai/en/concepts/01-architecture),
[context types](https://docs.openviking.ai/en/concepts/02-context-types),
[context layers](https://docs.openviking.ai/en/concepts/03-context-layers) and
[retrieval](https://docs.openviking.ai/en/concepts/07-retrieval), all accessed
2026-11-03. License: AGPL-3.0 for the main project (repository README, accessed
2026-11-03); the CLI crate and examples carry Apache-2.0.

The operator asked whether the same design and architecture can manage this
team's lessons, experience, knowledge and memory. The answer is **yes to the
design, no to the dependency**.

**What OpenViking does.** It is a context database for agents: one virtual
filesystem (`viking://`) holding three context types - resources (documents and
code), memories (profile, preferences, entities, events, cases, trajectories,
experiences) and skills (`SKILL.md` plus supporting files) - with rules as a
beta fourth type. Every directory carries generated summaries at three levels:
L0 abstract (about 256 characters), L1 overview (about 4,000), L2 the original
content. Retrieval is directory-scoped vector search, optionally reranked; a
session commit archives the conversation and extracts memories into Markdown.

| Their mechanism | What it fixes for us | Verdict | Surface here | Falsifier |
|---|---|---|---|---|
| One filesystem for resources, memory and skills | our context is six silos (short/long/global memory, lessons, knowledge, skills, docs) with no single way to see or search them | **Adopt as a view** | `ctx://` URIs over the existing files; no migration, no second copy | a `ctx://` node that resolves to nothing, or a fact stored twice |
| Stable URI per item, inspectable and editable | a fact found in one command cannot be cited or re-read from another | **Adopt** | `ctx://project/knowledge/K-0001`, `ctx://role/<role>/lessons/L-0001`, ... | a search result with no resolvable URI |
| L0 abstract / L1 overview / L2 detail | `load` shows one line but there is no middle layer between the summary and the whole file | **Adopt, computed** | `context read <uri> --level 0\|1\|2`; L0/L1 derived from the record or Markdown structure at read time | an L0/L1 that needs a model or a generated sidecar to exist |
| Directory-scoped retrieval | `recall` searches all memory, `knowledge search` all knowledge; nothing searches "this role" or "this store" | **Adopt** | `context find <query> --scope ctx://role/developer` | a scope that returns a node outside it |
| Session commit -> extracted memories | our close-out writes lessons/knowledge by hand, and a task that ends without either loses what it learned | **Adapt** | `context digest <T-id>` prints candidate lesson/knowledge templates from the task's findings and evidence; the agent writes them | a digest that writes records, or a candidate with no evidence |
| Vector index + rerank | semantic recall is better on fuzzy queries | **Reject** | deterministic keyword/tag scoring in `context find` | a query that only a vector index could answer, and no keyword match exists |
| Server, multi-tenant, ACL, encryption, RAGFS | one operator, one repository, one local tree | **Reject** | the Markdown tree and the hash-chained ledger | a second process or a network service becomes required |
| Generated semantic sidecars (VLM) | sidecars make scanning cheap | **Reject** | L0/L1 computed at read time | a stale sidecar contradicts its source |
| Vendoring the implementation | - | **Reject** | design patterns only; no AGPL code copied | an AGPL header or a copied module in this tree |

**Vendor claims, not reproduced here.** The README reports LoCoMo memory
accuracy of 80-83% versus 24-57% for the three native memories, input-token
reductions of 34.3-91.0%, query-latency reductions of 58.45-66.10%, and
tau2-bench task-success gains of +6.87pp (retail) and +11.87pp (airline) from
experience memory (README, accessed 2026-11-03). Those numbers are the vendor's
own benchmark on their models; this team has not reproduced them and does not
rely on them.

**Why the split is the right one.** This skill ships as a stdlib-only bundle that
runs offline from one directory. A vector index, an embedding model, a VLM and a
server would each break that promise, and a generated summary that a model wrote
is not evidence. The parts that transfer are the parts that do not need a model:
one navigable tree, stable URIs, three levels of detail and scoped retrieval. The
parts we keep are the ones this team already does better for its purpose: every
record carries evidence and a revision, the ledger is hash-chained, and the
author writes the lesson.

The frozen contract is `docs/Team/Architecture.md` section 16; the knowledge
record it extends is section 15.

## 14. Agent Autoloop (KKKKhazix): what we adopt, what we reject

The operator asked whether this repository offers useful knowledge and
experience. The answer is **yes, four mechanisms worth adopting or adapting,
and no reason to copy the architecture**.

**What it is.** A local background loop for command-line agents: a deterministic
kernel (about 1,650 lines, zero runtime dependencies, Node 24) surrounded by four
swappable plugin sides - events, agents, channels and delivery. Work arrives as
an event, a rule picks the agent and folder, the agent works one round and exits,
and a sensitive decision becomes a card that resumes the original session when
answered. All state derives from an append-only fact log.
[README.en.md](https://github.com/KKKKhazix/agent-autoloop/blob/2730941e85723ca2b8e2b2629fa428832b810ffa/README.en.md) - accessed 2026-11-04.

| Their mechanism | What it fixes for us | Verdict | Surface here | Falsifier |
|---|---|---|---|---|
| **Zero-cost wait**: the agent process exits while a question waits in storage; the answer resumes the original session | our attention record blocks STOP, but nothing resumes a lane after the person answers | **Adapt** | `attention` already names the person question; record the resume hint on the item and name the lane that must pick it up | an answered attention item no lane can resume |
| **Fact log as the only source of truth**: projections rebuild from it, no migrations | our `Ledger.jsonl` is an audit side-log, not authority; a queue can be hand-edited and no projection is rebuilt from it | **Adapt as a warning** | keep the state files authoritative and the ledger tamper-evident; never claim a queue can be rebuilt from it | a doc that calls the ledger the source of truth, or a rebuilt queue that differs from its file |
| **Code/data split**: external text never enters the prompt; only typed ids and links do; an event carrying `cwd`/`agent`/`access` is rejected | our task titles, bodies and evidence enter prompts and packets, where a crafted string tries to redirect a lane | **Adopt** | render task text as an explicit data block with a not-instructions line; prove that `agent: reviewer` or `cwd: /` in a body cannot change routing (T-0041) | such a line changes the lane, folder, model or permissions chosen |
| **Hop circuit breaker**: `MAX_HOPS = 8`, propagated through cards, timers and emitted events, unresetable by the agent | a task can create a task, a review finding another, and the chain has no depth limit | **Adopt** | engine-derived hop depth on the task record, a cap, and an attention blocker at the cap (T-0040) | a chain deeper than the cap still dispatches |
| **Architecture as a test** and **failure-first tests**: `tests/purity.test.ts` fails on a vendor name, an outbound request, a dependency or a UI in the kernel; every test file opens by naming the failure it prevents | our boundaries are policy prose, and not every test module states what it prevents | **Adapt** | a purity guard for the pure state modules and the failure-first line in `references/Engineering.md` (T-0016) | a pure module imports `socket`/`subprocess`, or a test module names no failure |
| **Four explicit plugin sides** (events, agents, channels, delivery) with one protocol | our host operations are listed in `references/Adapters.md` but not named as one contract | **Adapt, no new layer** | name the six host operations as the contract; no server, no second discovery path | a host operation with no adapter, or a second way to register one |
| **One-tap cards in chat channels**, no web dashboard | a person must open the workspace to read an attention item | **Reject for now** | the attention record stays the interface; a channel is an optional view over it | a required external service or account enters the skill |
| **Node 24 + SQLite + HTTP daemon, one-machine hub** | a durable queue and event log are proven at scale | **Reject** | stdlib Python, local files, no daemon, no inbound port | a runtime dependency or a listening service becomes required |
| **Delivery isolation**: settings read only from `main`; PR code never checked out or run on the delivery host; review in a read-only snapshot | a delivery runner with credentials must not execute the code it is about to ship | **Adopt as policy** | the release policy in `docs/Team/Release.md`: settings from the base branch, no PR execution on the release host | a release step executes branch code with release credentials |

**Vendor claims, not reproduced here.** The repository reports 1,942 stars at
access, was created on 2026-11-03, ships a Chinese-first CLI and notifications,
runs on macOS and Linux, and measured its benchmarks on one Apple M5 Pro (1.1
million facts rebuild in 43.1 s, cold start 88.78 ms, 2,394 durable writes/s);
its own README says several plugin templates were checked only against mocks,
not real services. Those are adoption signals and vendor measurements, not this
team's measurements.
[README.en.md](https://github.com/KKKKhazix/agent-autoloop/blob/2730941e85723ca2b8e2b2629fa428832b810ffa/README.en.md) - accessed 2026-11-04.

**Adoption work.** T-0040 caps follow-up chains (hop depth); T-0041 makes task
text data and proves routing cannot be steered by it; T-0016 adapts the
failure-first and purity guards. The delivery-isolation line is a release-policy
change with no task yet, recorded here so the Release Engineer's next edit to
`docs/Team/Release.md` carries it.
The rest is rejected because this skill ships as one stdlib-only directory that
runs offline - a daemon, a SQLite hub, a chat channel or a web UI would each
break that promise, and none of the adopted mechanisms needs one.

**Sources.**

- [KKKKhazix/agent-autoloop](https://github.com/KKKKhazix/agent-autoloop) - accessed 2026-11-04
- [kernel/decide.ts at 2730941](https://github.com/KKKKhazix/agent-autoloop/blob/2730941e85723ca2b8e2b2629fa428832b810ffa/kernel/decide.ts) - accessed 2026-11-04 (`MAX_HOPS`, hop propagation, cap notice)
- [protocol/validate.ts at 2730941](https://github.com/KKKKhazix/agent-autoloop/blob/2730941e85723ca2b8e2b2629fa428832b810ffa/protocol/validate.ts) - accessed 2026-11-04 (event field allowlist, subject and link constraints)
- [tests/purity.test.ts at 2730941](https://github.com/KKKKhazix/agent-autoloop/blob/2730941e85723ca2b8e2b2629fa428832b810ffa/tests/purity.test.ts) - accessed 2026-11-04 (the architecture as a test)
- [AGENTS.md at 2730941](https://github.com/KKKKhazix/agent-autoloop/blob/2730941e85723ca2b8e2b2629fa428832b810ffa/AGENTS.md) - accessed 2026-11-04 (principles, tests first, delivery boundaries)
- [LICENSE (MIT)](https://github.com/KKKKhazix/agent-autoloop/blob/2730941e85723ca2b8e2b2629fa428832b810ffa/LICENSE) - accessed 2026-11-04

## M22 - memory components re-verified (2026-11-09)

Owner: Product Manager. Related: [Plan](Plan.md) · [Architecture](Architecture.md) ·
[Design](Design.md) · [Risks](Risks.md)

The memory milestone (M22, AC-M22-5) rests on an outside article. Rather than
carry forward a summary of it, every claim the milestone leans on was re-checked
against the live page on 2026-11-09 and is recorded here with the fragment it
rests on. Fetch evidence: HTTP 200, 242,698 bytes of HTML, 24,861 characters of
extracted text; all six claim areas located in that text.

| claim | what the page says (quote) | status | what it changes here |
|---|---|---|---|
| C1 dreaming = reflecting on logs to fix mistakes and produce notes/representations | "reflecting on logs to fix mistakes or produce new notes and representations. This process is often called dreaming" | verified | Dreaming is a maintenance pass over logs we already keep, not a new subsystem. It needs no daemon and no vector store. |
| C2 a note is trustworthy when it carries the rule AND how the agent knew the rule was true | "Most of its entries included a rule (and also how it knew the rule was true)" | verified | Our memory records must carry their own evidence, not just the conclusion. A rule without its warrant is a note we cannot re-check later. |
| C3 too much memory is worse than too little | "413 memory files across 225 folders and earned one badge" · "Fable 5, by comparison, wrote nine files in two folders ... and earned four badges" | verified (numbers only) | The numbers hold. The page's reason is stale-state cost, not volume as such; "worse than too little" is our inference, not its wording. |
| C4 a wiki helps most combined with search, and a wiki can outgrow the corpus it abstracts | "the wiki helped Claude the most when we also gave it access to a search tool" · "the wiki grew larger than the documents themselves" | verified, with a correction | The task brief said 53% -> 61%. The page says the aggregate score rose from 54% to 61% with search plus wiki as the wiki grew, against 53% for search alone, and 48% for the wiki alone. Corrected here. |
| C5 injected memory costs tokens, a wrong note is carried into every session, and Claude Code loads only the first 200 lines / 25 KB of MEMORY.md as an index | "Injected memories use up valuable tokens, and an incorrect note can be carried into every session." · "It loads only the first 200 lines or 25 KB of MEMORY.md." | verified | Our injected memory file is an index with a hard size ceiling, not a store. Everything else stays on disk and is searched on demand. |
| C6 "it's reasonable to consider transcript search as the foundation" of memory | "It's also reasonable to consider transcript search as the foundation of Claude's memory." | verified | Search is the baseline we build first and measure against; representations are the optional layer above it. |

Two further fragments bear directly on the decision below and are quoted for that
reason: "could be retrieved with a text search from a single document, and the
wiki showed no clear gain in performance relative to search", and "Using search
and the wiki also saved about 20,000 tokens per question."

### Why no wiki yet

The CEO's decision, recorded here on 2026-11-09, is to **defer** any wiki
representation of our memory store. This is a recorded decision with a falsifier,
not an omission.

The reasoning is C4 read honestly. A wiki paid off only when it was combined with
search, and only on questions that needed synthesis across a corpus; where a
single record answered, the page found no clear gain. A wiki also has an unbounded
failure mode - it grew larger than the raw files and abstracted nothing, which the
page compares to Borges's map at the scale of the empire. Building one now would
add a maintained artifact, and a maintained artifact can drift and be wrong in the
way C2 warns about, to buy a gain we have no evidence we need at our size.

**Falsifier - build the wiki when either trigger fires:**

1. the active memory store exceeds **200 active records**; or
2. real questions **require synthesis across records**, so that search over single
   records demonstrably cannot answer them.

When a trigger fires, the wiki is built behind a measurement, not on fashion: an
A/B on our own questions showing search-plus-wiki above search alone, and a size
check showing the representation stays smaller than the store it abstracts. If the
measurement shows no gain, the decision stands and the trigger is re-recorded.

**Sources.**

- [The components of agent memory](https://www.anthropic.com/research/components-of-agent-memory) - accessed 2026-11-09
