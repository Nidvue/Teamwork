# Architecture - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Quickstart](quickstart.md) · [CLI reference](cli.md) · [CI pipeline](ci.md) · [Team architecture](https://github.com/Nidvue/Teamwork/blob/main/docs/Team/Architecture.md)

The frozen interface contract for the engine lives in the team's
[Architecture.md](https://github.com/Nidvue/Teamwork/blob/main/docs/Team/Architecture.md). This page describes the shipped
package and runtime.

## Three faces, one engine

| Face | Entry point | Contents |
|---|---|---|
| Skill | `SKILL.md` at the repository root | `SKILL.md`, `roles/*.md`, `references/*.md`, `templates/` |
| Python package | `python -m teamwork` / `teamwork` console script | `src/teamwork/` |
| Workspace format | `<project>/.pi/Teamwork/Teams/<Team>/` | Markdown + JSON |

The engine is a port of the original skill monolith with behaviour unchanged; the
three faces share it.

## Package layout

```text
src/teamwork/
├── __init__.py     # __version__ re-export only
├── __main__.py     # python -m teamwork -> cli.main()
├── cli.py          # main(argv) -> int, a thin face on engine.main
├── engine.py       # the ported engine and the argparse surface (build_parser)
├── board.py        # docs/Team/Board.md rendered and checked against the queues
├── bundle.py       # the movable skill bundle + the refresh mirror
├── config.py       # workspace paths, record names, caps, scan routing
├── gitutil.py      # git plumbing for branch/PR/merge
├── harness.py      # harness registry, always-on budget, proposal lint
├── hooks.py        # the pre-commit and pre-push git hooks
├── imaging.py      # offline image-model capability probe
├── io.py           # atomic file IO, the exclusive lock, the one error exit
├── layout.py       # the team tree, the committed docs and their links
├── names.py        # names, roles and commit identities
├── records.py      # the markdown record layer: parse, render, find
├── resources.py    # locate the skill bundle (checkout or wheel)
├── portable.py     # Windows-safe process/path helpers
└── version.py      # the package version (__version__)
```

`scripts/teamwork.py` is a thin compatibility shim that adds `src/` to
`sys.path` and calls `teamwork.cli.main`, so the CLI runs from a checkout with
only the standard library. The argument parser is not in `cli.py`: it is
`engine.build_parser()`, and `cli.main` is the same call as `engine.main`.

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
self_invocation() -> str    # how a teammate should invoke the CLI (machine-local)
portable_invocation() -> str  # a command prefix safe to commit
has_asset(name: str) -> bool
```

`self_invocation()` prefers the `teamwork` console script, then
`<sys.executable> <repo>/scripts/teamwork.py` from a checkout, then
`<sys.executable> -m teamwork` - an absolute interpreter path, so it belongs in
`.pi/` state and never in a committed file. `portable_invocation()` returns the
bare `teamwork` for anything that lands in the repository, because a committed
`AGENTS.md` must not embed a home path.

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
record = {n, prev, action, actor, role, target, detail, ts, rev, hash}
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
