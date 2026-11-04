# Usage patterns - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Installation](install.md) · [Quickstart](quickstart.md) · [Operations](operations.md) · [Features](features.md) · [How it works](how-it-works.md) · [Alternatives](alternatives.md) · [CLI reference](cli.md)

The recurring jobs the team is built for, as trimmed transcripts from a real run
of the engine in this repository (paths elided); the prompts in A-C are
illustrative. Each pattern names the same three things: what you type, what the
team records, and how you check it.

## A. New project from one prompt

```console
$ cd ~/code/url-shortener
> use the teamwork skill: build a URL shortener - a CLI with shorten and expand,
  SQLite storage, a pytest suite and a README. Keep it dependency-free.
```

The CEO writes `AGENTS.md`, records `AC-1..AC-n`, freezes the interfaces and opens
the lanes. You keep working in the host; the team reports through the CEO.

## B. A feature in an existing repository

```console
$ cd existing-repo
$ mkdir -p .agents/skills && git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork && rm -rf .agents/skills/teamwork/.git
> use the teamwork skill: add per-key rate limiting to the public API - 100
  requests/minute, 429 with Retry-After, and tests that prove the boundary.
```

Committing `.agents/skills/teamwork` gives every teammate the same protocol on a
fresh clone. The acceptance criteria become records before any code is written,
so "done" is the same definition in every session.

## C. A bug or a red CI run

```console
$ cd repo
> use the teamwork skill: fix the failing CI job on main, prove the fix with the
  exact test command, and do not touch unrelated files.
```

The protocol degrades the same way everywhere: without a teammate tool one agent
switches hats, and the evidence gates still hold
([references/Coordination.md](https://github.com/Nidvue/Teamwork/blob/main/references/Coordination.md)).
A fix is not accepted until the failing run and the passing run are both recorded
on the task.

## D. Steer the machine yourself

The skill calls these for you; run them when you want to see or change the plan.

```console
$ teamwork init --roster slim          # or: teamwork init --agents ceo,architect,developer-1,tester-1,reviewer-1
$ teamwork criteria add --id AC-1 --text "shorten then expand returns the original URL" --owner developer --by ceo
$ teamwork criteria add --id AC-2 --text "pytest -q passes on the matrix" --owner tester --by ceo
$ teamwork task add developer "Implement shorten/expand with tests" --priority P0
$ teamwork loop

> CONTINUE
  ! 2 acceptance criteria unverified
  ! no layered test records
  ! 1 task(s) not finished
```

`criteria add` is where a human changes what "done" means; `task add` is where
work enters a role's queue. Neither is a suggestion the team may reinterpret:
`loop` reads both records literally.

## E. Keep the lanes full

```console
$ teamwork pulse --interval 5
$ teamwork parallel

## provider slots
- anthropic        used=0    cap=64    free=64
- deepseek         used=0    cap=2500  free=2500
- ollama-cloud     used=0    cap=64    free=64
- openai           used=0    cap=64    free=64
- TOTAL free slots: 2692

## executable work
- developer        1 ready  next: developer/T-0001 [P0] Implement shorten/expand with tests
```

`pulse --commit` dispatches to idle instances. `parallel` shows how many lanes may
start without exceeding a provider cap. `instance add <role> --count N` scales any
role later without touching the shared memory file:

```bash
# any role, at any point: the instances share one memory set and one queue
teamwork instance add architect --count 2
teamwork instance list

# exactly one instance of a role revises that role's memory at a time
teamwork memory claim architect --by Architect-2 --reason "rewrite the contract"
teamwork memory status architect

# and a lease that runs long is contested, not waited out: the CTO rules
teamwork memory contest architect --by Architect-3 --reason "three tasks are blocked"
teamwork memory extend architect --by CTO --ttl 45 --reason "the rewrite is large"
#   or: teamwork memory revoke architect --by CTO --reason "that lane is wedged"
teamwork memory release architect --by Architect-2
```

The caps behind `parallel` and the rules behind the memory pen are explained in
[Operations](operations.md).

## F. Resume after a crash or a new session

```console
$ teamwork load developer-1     # the role's short-term memory
$ teamwork task next developer-1
$ teamwork map                  # roles, instances, open work
```

All state is on disk, so a fresh agent resumes without a handover meeting. The
ledger is the last resort for a question the memory files cannot answer:
`teamwork trace <id>` follows one record end to end.

## G. Prove the audit trail to someone who does not trust the team

```console
$ teamwork ledger verify
# Ledger verify (.../Ledger.jsonl)
# records: 5 | head: a23748ba85cf962f
- chain intact, every digest matches

$ teamwork trace T-0001
## task T-0001 [todo] Implement shorten/expand with tests  (developer)
## ledger events (1)
- #0005 task.add  developer  [P0] Implement shorten/expand with tests
```

`ledger export` writes a manifest that a reviewer can verify without access to
the workspace. The chain, its digest and the manifest format are described in
[How it works](how-it-works.md).

## H. Route the models, not just the roles

```console
$ teamwork model auto
- architect          strong   deepseek-v4.1-flash
- ceo                strong   deepseek-v4.1-flash
- developer          economy  deepseek-v4.1-flash
- product-manager    economy  deepseek-v4.1-flash
- project-manager    economy  deepseek-v4.1-flash
- reviewer           strong   deepseek-v4.1-flash
- tester             economy  deepseek-v4.1-flash
# dry run: rerun with --apply to write these into Settings.json
```

Decision lanes get the strongest model the host exposes; mechanical lanes get the
economy one. `model set <agent>` overrides a single lane. Routing is a dry run
until `--apply`, and it never invents a model the host has not exposed - see
[Operations](operations.md) for the detection order and the override precedence.
