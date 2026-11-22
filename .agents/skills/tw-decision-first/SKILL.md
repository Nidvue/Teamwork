---
name: tw-decision-first
description: "a lane is about to decide something small in prose: which record owns a defect, whether an action is destructive, or whether to keep a tool output before compaction"
kind: workflow
---

# tw-decision-first

Owner role: **ceo** (created by CEO on 2026-11-22).

Use this skill when: a lane is about to decide something small in prose: which record owns a defect, whether an action is destructive, or whether to keep a tool output before compaction

Related: [tw-number-vet](../tw-number-vet/SKILL.md) - this skill asks the question
and puts the probability in the record; that one refuses a number that was never
measured. Decision and decision proof are separate gates, and neither excuses the
other. D-20261122-CEO in `docs/Team/Decisions.md` owns the adoption and its falsifier.

## Why this exists

This flow is repetitive, widely reused and must stay consistent across every
ceo instance. Extracted once so it is executed the same way every time.

## Steps

## 1. What this skill does

A judgment that a lane would otherwise make in prose is asked as one typed question
of a classifier (`typesafe` / `jev-latest`), and the record carries the probability,
the threshold and the model id. Writing stays on the chat model; only the decision
moves. Related: K-0004, D-20261122-CEO.

## 2. The three questions, and nothing else

| Judgment | Question | Threshold | Who acts on it |
|---|---|---|---|
| which record owns a defect | `choice`: `task_id` / `test_code` / `engine_code` | confidence >= 0.75 | the lane that found the defect |
| is this action destructive | `bool`: deletes, overwrites data, or rewrites history | probability > 0.5 parks for the CEO | the lane about to act |
| keep or drop a tool output before compaction | `score` 1-5 on "still needed to finish the task" | drop only at <= 1 | the lane compacting |

Any other question - which lane takes a task, whether work is done, whether a
review passes - is refused by this skill: those are decided by the engine's
assignment, by a test record, and by the Reviewer respectively.

## 3. Procedure

1. Build `state` from the facts only, under 2,000 tokens, with no secret,
   credential, personal data, or unredacted path that names one.
2. Ask one call with the questions above that the step actually faces.
   From a codemode script: `models.classify(models.getModelOfType("classifier", "typesafe", "jev-latest"), { state, questions })`.
   From an extension: `ctx.modelRegistry.classify(...)`. Check `stopReason` and
   `errorMessage`; an error result is not a zero.
3. Quote the numbers in the record, never a paraphrase:
   `choice=<x> p=<prob> confidence=<conf> threshold=<n> model=typesafe/jev-latest @<rev>`.
4. Act only above the threshold. Below it, escalate to the CEO or ask the question
   again with a smaller state; a low-confidence answer is a fact about the state,
   not a coin flip.
5. Record the decision with `decision add` or as the task's `evidence`, with the
   falsifier from D-20261122-CEO: a run whose probability for the same state moves
   by more than 0.15 makes this layer noise, and the skill is deleted.

## 4. Pitfalls

| Pitfall | The guard |
|---|---|
| the number approves an action | the red lines and `preflight` still decide; the classifier only informs |
| a probability closes a task | `done` needs a test record and a Reviewer verdict |
| state leaks the machine | the call is an external request: secret-free state or do not call |
| a second routing path | `pulse` and `swarm` already assign work; do not add a classifier route |
| paraphrasing the answer | quote `p=` and `confidence=` verbatim |
| meter says zero cost | the direct provider reports tokens at no cost; the vendor rate is $0.042 per Mtok input, output free |

## 5. Verification

`pi --print -ne -e <repo>/.pi/Teamwork/Teams/Teamwork/Agents/CEO/Scratch/jev_probe.ts "say ok"`
then read `jev_probe.out`: it must show `CLASSIFIERS=["typesafe/jev-latest"]`,
`STOP=stop`, an `ANSWER` with `p` and `confidence`, and a `USAGE` token count.
`pi auth check --provider typesafe --json` must print `{"status":"ready"}`.

## Evidence

Every run records command + revision + observed result, as the team requires.

## Guardrails

- This skill does not replace `AGENTS.md`, the red lines, or the quality gates.
  If it conflicts with them, they win and this file must be fixed.
- It never bypasses: self-check, independent review, the PR, or the Reviewer-only
  merge. It may not weaken or skip a test layer.
- Changing this skill is normal work: branch, commit with the fixed message style,
  PR, review, merge. Never edit it on `main`.
