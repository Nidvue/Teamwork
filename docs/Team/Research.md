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

## 6. Sources

- [Agentic Framework Showdown: We Tested 8 AI Agent Frameworks - TELUS Digital](https://www.telusdigital.com/insights/data-and-ai/article/8-agentic-frameworks-tested) - accessed 2026-10-17
- [Orchestrator-Worker Agents: Comparing Agent Frameworks - Arize](https://arize.com/blog/orchestrator-worker-agents-a-practical-comparison-of-common-agent-frameworks/) - accessed 2026-10-17
- [Agentic AI Frameworks: Architectures, Protocols, and Design Challenges - arXiv](https://arxiv.org/html/2508.10146) - accessed 2026-10-17
- [5 tips for promoting your open source project - GitHub Blog](https://github.blog/open-source/maintainers/5-tips-for-promoting-your-open-source-project/) - accessed 2026-10-17
- [How We Got 4.5K+ GitHub Stars on Our Open Source Project in 6 Months - freeCodeCamp](https://www.freecodecamp.org/news/how-to-get-more-engagement-with-your-open-source-project/) - accessed 2026-10-17
- [What We Did to Gain 3,000 GitHub Stars for the Liam Repository - Liam ERD](https://liambx.com/blog/liam-github-3k-stars) - accessed 2026-10-17
- [GitHub SEO Guide 2025 - GitDevTool](https://www.gitdevtool.com/blog/github-seo) - accessed 2026-10-17
- [Multi-agent orchestration visual summary - Bhaskarjit Sarmah](https://bhaskarjsarmah.github.io/visual-summary/52-agent-orchestration/) - accessed 2026-10-17
