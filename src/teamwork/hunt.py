"""A bounded discovery loop: run a round, count what is new, stop when nothing is.

Why this exists: "keep going until it is good" has no end, and an agent will spend
another hour polishing. The team already bounded a lane by minutes and tool calls,
and a retry by attempts - but a *discovery* task (a bug hunt, a research sweep, an
audit) has no such unit: its value is the set of findings, and the honest stop
condition is "two rounds in a row produced nothing this loop had not already
seen", not "the attempt budget ran out". Without a seen set the same dead end is
rediscovered and paid for every round, and without a dry counter the loop cannot
tell progress from thrashing.

So one command owns that loop, with the five things a cycle needs:

* a test that says done - a round that adds no fresh finding is dry;
* a round limit - ``--rounds`` (default 6);
* a budget - ``--timeout`` seconds per round, and the round limit itself;
* memory of past attempts - ``Runtime/Hunt/<slug>.json`` keeps every key ever
  reported *and* every key rejected, so a re-run continues instead of restarting;
* a person who gets paged if it stalls - a loop that exhausts its rounds still
  finding things, or whose command fails twice, opens an attention item and exits 1.

The command prints one finding per line; a line is its own dedup key, whitespace
normalised. ``--reject`` marks a dead end (substring match, case-insensitive) so it
is never reported fresh again - a rejected finding stays in the seen set, which is
what stops the loop from rediscovering what it already threw away.

Owner: architect. Layer: system. Area: graph.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

from .config import DIR_RUNTIME
from .io import die, write_lf
from .layout import project_of, project_root
from .names import safe_component, slugify

DEFAULT_ROUNDS = 6
DEFAULT_DRY = 2
DEFAULT_TIMEOUT = 900
MAX_FINDING_CHARS = 200


def hunt_dir(root: Path) -> Path:
    """Where a discovery loop keeps its memory of what it already found and threw away."""
    return root / DIR_RUNTIME / "Hunt"


def state_path(root: Path, topic: str) -> Path:
    return hunt_dir(root) / f"{safe_component(slugify(topic, limit=60))}.json"


def load_state(path: Path, topic: str) -> dict:
    if not path.is_file():
        return {"topic": topic, "seen": [], "rejected": [], "rounds": 0, "dry": 0}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"topic": topic, "seen": [], "rejected": [], "rounds": 0, "dry": 0}
    state.setdefault("topic", topic)
    state.setdefault("seen", [])
    state.setdefault("rejected", [])
    state.setdefault("rounds", 0)
    state.setdefault("dry", 0)
    return state


def save_state(path: Path, state: dict) -> None:
    write_lf(path, json.dumps(state, indent=2, sort_keys=True) + "\n")


def key_of(line: str) -> str:
    """One finding's dedup key: the line with whitespace collapsed."""
    return " ".join(str(line).split())


def is_rejected(key: str, rejected: list) -> bool:
    low = key.lower()
    return any(item.lower() in low for item in rejected if item)


def fresh_keys(lines: list, seen: set, rejected: list) -> list:
    """The lines this loop has not reported before and has not already rejected."""
    out = []
    for line in lines:
        key = key_of(line)
        if not key or key in seen or is_rejected(key, rejected):
            continue
        seen.add(key)
        out.append(key)
    return out


def run_round(command: str, cwd: Path, timeout: int) -> tuple:
    """``(lines, problem)``: what the round printed, or the one reason it did not run."""
    argv = shlex.split(command)
    if not argv:
        return [], "no command"
    try:
        done = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [], f"timed out after {timeout}s"
    except OSError as exc:
        return [], f"{type(exc).__name__}: {exc}"
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    if done.returncode != 0:
        detail = " ".join((done.stderr or done.stdout).split())[:200]
        return lines, f"exit {done.returncode}: {detail or '(no output)'}"
    return lines, ""


def page(root: Path, actor: str, topic: str, reason: str, state_file: Path) -> str:
    """Open the attention item a stalled loop owes a person, and name it."""
    from . import engine
    from .attention import new_attention, parse_attention, write_attention
    from .layout import attention_path

    path = attention_path(root)
    text = f"discovery loop '{topic}' stalled: {reason} (state {state_file.name})"
    items = parse_attention(path)
    items.append(new_attention(text, "blocker", actor))
    write_attention(path, items)
    engine.ledger_append(root, "attention.add", actor, topic, f"[blocker] {text[:90]}")
    return text


def cmd_hunt(args) -> int:
    root = project_root(args)
    topic = (args.topic or "").strip()
    if not topic:
        die("hunt needs a topic: it is the loop's identity and its state file's name", 2)
    from . import engine

    path = state_path(root, topic)
    state: dict = load_state(path, topic)
    command = str(getattr(args, "run", "") or "").strip()
    actor = ""
    if command:
        actor, _role = engine.validate_actor(root, getattr(args, "by", ""), "hunt author")
    if getattr(args, "reset", False):
        state = {"topic": topic, "seen": [], "rejected": [], "rounds": 0, "dry": 0}
        save_state(path, state)
        print(f"# reset {path.name}: the loop forgets every finding and every dead end")
    for item in getattr(args, "reject", []) or []:
        key = key_of(item)
        if key and key not in state["rejected"]:
            state["rejected"].append(key)
        if key and key not in state["seen"]:
            state["seen"].append(key)
    save_state(path, state)

    if not command:
        count = len(state["seen"])
        print(f"# Hunt: {topic}")
        print(f"# state {path}: {count} seen, {len(state['rejected'])} rejected")
        print(f"# last run: {state['rounds']} round(s), {state['dry']} dry in a row")
        if state["rejected"]:
            print("\n## rejected (never reported fresh again)")
            for item in state["rejected"]:
                print(f"- {item}")
        return 0

    rounds = max(int(getattr(args, "rounds", DEFAULT_ROUNDS) or DEFAULT_ROUNDS), 1)
    dry_limit = max(int(getattr(args, "dry", DEFAULT_DRY) or DEFAULT_DRY), 1)
    timeout = max(int(getattr(args, "timeout", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT), 1)
    seen = set(state["seen"])
    cwd = project_of(root)
    report = [f"# Hunt: {topic}", f"# state {path.name}: {len(seen)} seen before this run"]
    total_fresh = 0
    failures = 0
    dry = 0
    reason = ""
    for index in range(1, rounds + 1):
        lines, problem = run_round(command, cwd, timeout)
        fresh = fresh_keys(lines, seen, state["rejected"])
        state["rounds"] = index
        if problem:
            failures += 1
            report += [f"## round {index}: failed ({failures}/2)", f"- {problem}"]
            save_state(path, state)
            if failures >= 2:
                reason = f"the round command failed twice: {problem}"
                break
            continue
        failures = 0
        dry = dry + 1 if not fresh else 0
        state["dry"] = dry
        state["seen"] = sorted(seen)
        save_state(path, state)
        total_fresh += len(fresh)
        report.append(f"## round {index}: {len(fresh)} fresh")
        for item in fresh[:40]:
            report.append(f"- {item[:MAX_FINDING_CHARS]}")
        if len(fresh) > 40:
            report.append(f"+{len(fresh) - 40} more in {path.name}")
        if dry >= dry_limit:
            reason = f"converged after {index} round(s): {dry} dry round(s) in a row"
            break
    else:
        reason = (
            f"budget spent: {rounds} round(s), the last still found fresh findings "
            f"({total_fresh} in this run)"
        )
    converged = reason.startswith("converged")
    state["seen"] = sorted(seen)
    state["dry"] = dry
    save_state(path, state)
    report += ["", f"> {'STOP' if converged else 'STALLED'} - {reason}"]
    if not converged:
        report.append(f"  ! paged a person: {page(root, actor, topic, reason, path)}")
    report.append(f"# {len(seen)} seen, {total_fresh} fresh this run; rerun to continue")
    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "topic": topic,
                    "state": str(path),
                    "converged": converged,
                    "fresh": total_fresh,
                    "seen": len(seen),
                    "rejected": len(state["rejected"]),
                    "reason": reason,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print("\n".join(report))
    return 0 if converged else 1


def add_parsers(sub, common) -> None:
    s = sub.add_parser(
        "hunt",
        parents=[common],
        help="bounded discovery loop: stop after two dry rounds, and remember dead ends",
    )
    s.add_argument("topic", help="what is being discovered; names the state file")
    s.add_argument(
        "--run",
        default="",
        help="the round command: it prints one finding per line (omit to print the state)",
    )
    s.add_argument(
        "--rounds", type=int, default=DEFAULT_ROUNDS, help=f"round limit (default {DEFAULT_ROUNDS})"
    )
    s.add_argument(
        "--dry",
        type=int,
        default=DEFAULT_DRY,
        help=f"dry rounds in a row that end the loop (default {DEFAULT_DRY})",
    )
    s.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT, help="seconds one round may take"
    )
    s.add_argument(
        "--reject",
        action="append",
        metavar="TEXT",
        help="a dead end: never reported fresh again (substring, repeatable)",
    )
    s.add_argument("--reset", action="store_true", help="forget every finding and dead end first")
    s.add_argument("--json", action="store_true", help="machine-readable verdict")
    s.add_argument("--by", default="", help="who runs the loop (recorded on a stall)")
    s.set_defaults(func=cmd_hunt)
