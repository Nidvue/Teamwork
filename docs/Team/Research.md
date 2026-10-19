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
* The engine keeps a 7k-line module for now; splitting it is a post-1.0
  refactor, listed in the roadmap and in [Decisions](Decisions.md).

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
| A7 | Make the right path the easiest (architecture as constraint) | **Adopt** | split `engine.py` (7,972 lines) into command modules behind an explicit registry; add an import-boundary lint so parallel lanes never edit one file |
| A8 | Guard the context window | **Adopt (cheap)** | `load --brief` and pulse digests that emit facts, not full files |
| A9 | Loop-closure metrics, not volume | **Adopt (cheap)** | `audit --metrics`: verification coverage, reproducibility rate, first-pass evidence completeness, review-fail rate, regression escapes |
| A10 | `reflect` at task close | **Adopt (cheap)** | `teamwork reflect <T-id>` proposes memory / skill / lint entries from findings and review fails |
| A11 | Throwaway prototype lane | **Adopt (cheap)** | `task add --kind prototype --review na`, artifacts in `Scratch/`, decision must cite the prototype path |
| A12 | Explain the number | **Adapt** | `decision add` demands baseline, method and variance for any measured number |
| - | 2,500 PR/month, agent count as maturity | **Reject** | volume is an output; our gate is loop closure |
| - | Agents merge their own code | **Reject** | collides with Reviewer-only merge and independence; sampling (A4) captures most of the speedup |
| - | Dune-specific bans (no `useEffect`, no comments) | **Reject** | project-specific policy, not a principle; our 8 lint suppressions (`src`+`scripts`) each carry a reason |
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
one 8k-line file; measure before/after on review-fail rate and merge conflicts.

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
