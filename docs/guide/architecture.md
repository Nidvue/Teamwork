# Architecture - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Quickstart](quickstart.md) · [CLI reference](cli.md) · [CI pipeline](ci.md) · [Team architecture](../Team/Architecture.md)

The frozen interface contract for the engine lives in the team's
[Architecture.md](../Team/Architecture.md). This page describes the shipped
package and runtime.

## Three faces, one engine

| Face | Entry point | Contents |
|---|---|---|
| Pi skill | `SKILL.md` at the repository root | `SKILL.md`, `roles/*.md`, `references/*.md`, `templates/` |
| Python package | `python -m teamwork` / `teamwork` console script | `src/teamwork/` |
| Workspace format | `<project>/.pi/Teamwork/Teams/<Team>/` | Markdown + JSON |

The engine is a port of the original skill monolith with behaviour unchanged; the
three faces share it.

## Package layout

```text
src/teamwork/
├── __init__.py      # __version__ and lazy re-exports
├── __main__.py      # python -m teamwork -> cli.main()
├── cli.py           # build_parser() + main(argv) -> int
├── engine.py        # the ported engine (single module)
├── resources.py     # locate the skill bundle (checkout or wheel)
├── portable.py      # Windows-safe process/path helpers
└── version.py       # __version__ = "1.0.0"
```

`scripts/teamwork.py` is a thin compatibility shim that adds `src/` to
`sys.path` and calls `teamwork.cli.main`, so the CLI runs from a checkout with
only the standard library.

## Resource resolution

The engine needs `SKILL.md`, `roles/`, `references/`, `templates/` and a runnable
engine path. `resources.skill_root()` resolves them in order, first hit wins:

1. `$TEAMWORK_SKILL_DIR` - explicit override (tests use it).
2. `teamwork/data/` - the packaged bundle inside an installed wheel.
3. `<repo root>/` - a normal git checkout.
4. The package's parent - a flattened copy next to the bundle.

Frozen public API:

```python
skill_root() -> Path        # directory holding SKILL.md + bundle folders
asset(*parts) -> Path       # skill_root() joined with parts
self_invocation() -> str    # how a teammate should invoke the CLI
has_asset(name: str) -> bool
```

`self_invocation()` prefers the `teamwork` console script, then
`python3 scripts/teamwork.py` from a checkout, then `python -m teamwork`.

## Workspace format

A team's own tree is hidden and gitignored; project output is committed.

```text
<project>/
├── AGENTS.md                        # team constitution (managed block)
├── docs/Team/                       # committed project output
└── .pi/Teamwork/Teams/<Team>/       # hidden, gitignored
    ├── TeamMap.md  Settings.json
    ├── Criteria.md  Tests.md  TestPlan.md
    ├── Reviews.md  Disputes.md  Skills.md
    ├── Ledger.jsonl                 # hash-chained audit trail
    ├── Global/                      # CEO-owned shared memory
    ├── Roles/<Role>/                # shared by every instance of the role
    ├── Agents/<Instance>/           # private to one instance
    └── Runtime/                     # ephemeral locks, slots, worktrees
```

Memory and the task queue belong to the ROLE, not the instance. `Role.md` is per
role; only `StartHere.md`, `WorkLog.md`, `Inbox.md`, `Artifacts/`, `Reports/`
and `Scratch/` are private to an instance.

## Ledger

Every mutation is appended to `Ledger.jsonl`. Each record carries the previous
record's digest, so the chain is tamper-evident:

```text
record = {n, prev, action, actor, target, detail, ts, rev, hash}
```

- `teamwork ledger verify` recomputes the chain.
- `teamwork ledger export` writes an externally verifiable manifest.
- `teamwork trace <id>` follows one task, criterion, test or PR end to end.
- A broken chain blocks `loop` from reporting `STOP`.

The record shape and digest function are frozen: changing them invalidates every
existing workspace.

## Portability and packaging

- Runtime: CPython 3.9 - 3.13 on Linux, macOS and Windows.
- No third-party import at runtime; file I/O is UTF-8 with `\n` newlines for
  byte-identical output.
- Forbidden in the runtime path: `fcntl`, `termios`, `pwd`, `grp`, `os.fork`,
  `resource`, `shell=True` and POSIX-only signal use.
- Build backend: `hatchling`; distribution `teamwork-agents`; import name
  `teamwork`; console script `teamwork`.
- The wheel force-includes the bundle at `teamwork/data/`; the release script
  asserts `teamwork/data/SKILL.md` and `teamwork/data/templates/AGENTS.md` exist.
