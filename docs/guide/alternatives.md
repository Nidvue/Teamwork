# Alternatives - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Features](features.md) · [Usage patterns](usage.md) · [Roadmap](roadmap.md) · [How it works](how-it-works.md)

A reader evaluating multi-agent tooling asks one question first: what is
structurally different here? This page answers it with a comparison, then explains
how to read the table and what it does not claim.

## 1. Comparison

| Project | Orchestration model | Evidence gate | Audit trail | Coding-agent skill | Zero runtime deps | License |
|---|---|---|---|---|---|---|
| **Nidvue Teamwork** | Persistent role org: shared role memory, priority queues, parallel lanes, CEO pulse | **Enforced** - `loop` blocks `STOP` until every criterion and required test layer has evidence | **Hash-chained** `Ledger.jsonl`, `ledger verify`, `trace`, `ledger export` | **Yes** - ships `SKILL.md`, `roles/`, `references/`, `templates/` | **Yes** - standard library only | AGPL-3.0-or-later |
| CrewAI | Role-based crews, sequential or hierarchical process | No | Task output and logs, not tamper-evident | No - Python library | No | MIT |
| AutoGen | Event-driven multi-agent conversations | No | Conversation logs, not tamper-evident | No - Python library | No | CC-BY-4.0 (archived) |
| MetaGPT | SOP-driven "software company" pipeline | No | Artifact files, not tamper-evident | No - Python library | No | MIT |
| LangGraph | Stateful graph / state machine over LLM agents | No | Checkpointing, not hash-chained | No - Python library | No | MIT |
| Aider | Single AI pair programmer in the terminal, git-aware | No | Git commits | No - terminal CLI | No | Apache-2.0 |

## 2. How to read the columns

- **Orchestration model** is the shape of the work, not a quality ranking. A crew,
  a conversation graph and a persistent role org solve different problems; pick
  the shape that matches how your project already assigns responsibility.
- **Evidence gate** asks whether the tool refuses to call work finished without a
  recorded command and result. A tool that reports task output still lets an agent
  declare victory; a gate does not.
- **Audit trail** asks whether the history is tamper-evident. Logs and git commits
  are useful records, but they are not hash-chained: anyone with write access can
  rewrite them without leaving a trace.
- **Coding-agent skill** distinguishes a directory an agent host can load from a
  Python library the host must import and wire up.
- **Zero runtime deps** is about what `pip install` drags in, not about whether the
  tool is useful.

## 3. What this table does not claim

It does not claim the other projects are worse; several are excellent at what
they are built for. It does not compare output quality, latency or price, because
those depend on the model behind the orchestration. And it does not treat "no
evidence gate" as a defect in a library: a framework leaves the process to you.

The one claim Teamwork makes that the others do not is the combination: a skill
an agent host loads, an org that persists between sessions, and a gate plus a
ledger that make "done" a verifiable record.

## 4. Sources

Competitor facts were checked against each upstream repository and its GitHub
licence metadata on 2026-10-17:

- [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) - accessed 2026-10-17
- [microsoft/autogen (archived)](https://github.com/microsoft/autogen) - accessed 2026-10-17
- [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) - accessed 2026-10-17
- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) - accessed 2026-10-17
- [Aider-AI/aider](https://github.com/Aider-AI/aider) - accessed 2026-10-17

If a row is wrong, the source above is what should be re-measured; the table is
revisited rather than assumed to stay true. The licence column is the upstream
repository's declared licence, not legal advice.

## 5. Choosing between them

| If you need | Consider |
|---|---|
| a run that stops only when the work is proven | Nidvue Teamwork |
| a Python library to embed in your own product | LangGraph, CrewAI or MetaGPT |
| one pair-programmer in a terminal today | Aider |
| an event bus for agents you already built | AutoGen |
| a skill your coding agent loads with no package manager | Nidvue Teamwork |

The honest answer for many teams is more than one: a framework inside the product
and a skill-driven org around the repository are not mutually exclusive.
