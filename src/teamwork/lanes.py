"""The lane runtime: the engine's own supervisor for parallel agent lanes.

Why this exists: the team protocol never needed a host plugin to run lanes - it
needed six operations (spawn, one-shot, message, inspect, pulse, close). Every
host mapped them onto its private tool, which made the skill depend on that tool:
no ``subagent`` extension, no parallelism. This module owns the six operations in
the engine itself, so the only thing a host must provide is a headless CLI that
takes a prompt.

The mechanism is a process table on disk, not a live object:

* a **lane** is one child process (``teamwork.lanerun`` wrapping the host CLI) plus
  a JSON record under ``Runtime/Lanes/`` and a prompt packet under
  ``Agents/<Instance>/Runs/``;
* the **board** decides who works: a lane takes its work with ``task next`` or a
  review claim, so two lanes cannot silently take the same deliverable;
* the **supervisor** decides who runs: ``swarm run`` computes each wave from the
  current records (ready tasks, review queue, free provider slots, unfinished
  assignments), starts the lanes it can afford, waits for one to end, and computes
  the next wave again. A wave is a fact about the board at that moment, never a
  plan written in advance - that is the dynamic part.

Nothing here is host-specific beyond :data:`HOST_BINARIES` (how to call a CLI
headlessly) and one escape hatch, ``TEAMWORK_LANE_CMD``, which is a template split
without a shell so a test, a wrapper or a new host can supply its own launcher.

State survives the supervisor: a lane keeps running when the CLI exits, the record
carries its pid, budget and outcome, and ``lane reap`` reconciles a lane that died
without writing an outcome. A re-entered supervisor resumes from the records.
"""

from __future__ import annotations

import datetime
import io
import json
import os
import re
import shlex
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from . import bundle, engine, gitutil, lanerun, messages
from .config import DIR_LOCKS, DIR_RUNTIME, F_SETTINGS, F_SHORT, PRIORITY_ORDER
from .io import die, lock, write_lf
from .layout import (
    agent_dir,
    list_agents,
    list_roles,
    project_of,
    project_root,
    role_dir,
    shown_path,
    task_file,
)
from .names import pascal, resolve_role, safe_component
from .portable import IS_WINDOWS, pid_alive
from .records import (
    executable,
    find_task,
    local_dep_map,
    new_entry,
    parse_memory,
    parse_tasks,
    today_iso,
    write_memory,
    write_tasks,
)

STARTING = "starting"
RUNNING = "running"
EXITED = "exited"
FAILED = "failed"
TIMEOUT = "timeout"
STOPPED = "stopped"
LOST = "lost"

LIVE = (STARTING, RUNNING)
TERMINAL = (EXITED, FAILED, TIMEOUT, STOPPED, LOST)

RESULT_MARKER = "LANE-RESULT:"
RESULT_RE = re.compile(
    r"^LANE-RESULT:[ \t]*(ok|blocked|failed)\b[:,\s-]*(.*)$", re.IGNORECASE | re.MULTILINE
)
RUN_ID_RE = re.compile(r"^L-(\d{4,})$")
LOG_TAIL_BYTES = 65536
MAX_PROMPT_BYTES = 16000

DEFAULT_LANE_MINUTES = 25
DEFAULT_SWARM_MINUTES = 60
DEFAULT_ATTEMPTS = 2
DEFAULT_POLL_SECONDS = 2.0
DEFAULT_TOOL_BUDGET = 16

DEFAULT_LANE_MAX = 8

PROFILE_WEIGHT = {"fast": 1, "standard": 2, "deep": 3}

STALE_WAVE_LIMIT = 3

PROFILE_MINUTES_FACTOR = {"fast": 0.4, "standard": 1.0, "deep": 1.6}

PROFILE_TOOL_BUDGET = {"fast": 10, "standard": 16, "deep": 24}

WEIGHT_PER_LANE = 3

COMPLEXITY_BANDS = (
    (1, "trivial"),
    (3, "simple"),
    (7, "moderate"),
    (13, "complex"),
    (10**6, "large"),
)

REVIEW_BACKLOG_RATIO = 2

STARTING_GRACE_SECONDS = 120

PLACEHOLDERS = ("prompt", "packet", "log", "agent", "model", "provider", "cwd", "run")

PLACEHOLDER_TOKENS = frozenset("{" + name + "}" for name in PLACEHOLDERS)

HOST_BINARIES = {
    "pi": "pi",
    "claude": "claude",
    "codex": "codex",
    "opencode": "opencode",
    "gemini": "gemini",
    "cursor": "cursor-agent",
}


def lanes_dir(root: Path) -> Path:
    return root / DIR_RUNTIME / "Lanes"


def run_path(root: Path, run_id: str) -> Path:
    return lanes_dir(root) / f"{safe_component(run_id)}.json"


def packet_path(root: Path, agent: str, run_id: str) -> Path:
    return agent_dir(root, agent) / "Runs" / f"{run_id}.md"


def log_path(root: Path, agent: str, run_id: str) -> Path:
    return agent_dir(root, agent) / "Runs" / f"{run_id}.log"


def _settings(root: Path) -> dict:
    try:
        data = json.loads((root / F_SETTINGS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _setting(root: Path, key: str, default, env: str = ""):
    raw = os.environ.get(env, "").strip() if env else ""
    if raw:
        return raw
    value = _settings(root).get(key, default)
    return default if value in (None, "") else value


def _setting_int(root: Path, key: str, default: int, env: str = "") -> int:
    try:
        return int(_setting(root, key, default, env))
    except (TypeError, ValueError):
        return default


def lane_minutes(root: Path) -> int:
    return max(_setting_int(root, "LaneMinutes", DEFAULT_LANE_MINUTES, "TEAMWORK_LANE_MINUTES"), 1)


def lane_attempts(root: Path) -> int:
    return max(_setting_int(root, "LaneAttempts", DEFAULT_ATTEMPTS), 1)


def lane_tool_budget(root: Path) -> int:
    return max(_setting_int(root, "LaneToolBudget", DEFAULT_TOOL_BUDGET), 1)


def lane_poll(root: Path) -> float:
    try:
        raw = _setting(root, "LanePollSeconds", DEFAULT_POLL_SECONDS, "TEAMWORK_LANE_POLL")
        return max(float(raw), 0.05)
    except (TypeError, ValueError):
        return DEFAULT_POLL_SECONDS


def swarm_minutes(root: Path) -> int:
    return max(_setting_int(root, "SwarmMinutes", DEFAULT_SWARM_MINUTES), 0)


def lane_command(root: Path) -> str:
    return str(_setting(root, "LaneCommand", "", "TEAMWORK_LANE_CMD")).strip()


def lane_host(root: Path, override: str = "") -> str:
    host = (override or str(_setting(root, "LaneHost", "", "TEAMWORK_LANE_HOST"))).strip().lower()
    return host or engine.detect_agent_host()


def _short_head(path: Path) -> str:
    """The short revision a checkout is at, or ``""`` when it is not a checkout."""
    if not bundle.is_checkout(path):
        return ""
    got = gitutil.run_git(path, "rev-parse", "--short", "HEAD")
    return got.stdout.strip() if got.returncode == 0 else ""


def stale_bundle_line(root: Path, host: str = "", dest: str = "") -> str:
    """One line naming a stale installed skill, or ``""`` when the lane is current.

    A lane is launched by the **installed copy** in the skills directory, not by
    the checkout (K-0005): when the copy lags, every lane silently runs the old
    protocol and a merged behaviour cannot fire. Comparing the bundle instead of
    a timestamp is the only check that survives a rewritten history, and naming
    both revisions makes the gap a measurement rather than an impression.
    """
    if len(root.parents) < 4:
        return ""
    project = project_of(root)
    if not bundle.is_checkout(project):
        return ""
    target = bundle.resolve_dest(host or lane_host(root), dest)
    if not target.is_dir():
        return ""
    added, updated, removed = bundle.plan(project, target)
    if not (added or updated or removed):
        return ""
    installed = _short_head(bundle.default_mirror_path(target)) or "unknown"
    return (
        f"# installed skill {target} is behind the checkout {project} "
        f"({installed} vs {_short_head(project)}): {len(added)} missing, "
        f"{len(updated)} stale, {len(removed)} extra - run `teamwork.py refresh` "
        "so this lane does not run stale code"
    )


def _stamp() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def next_run_id(root: Path) -> str:
    top = 0
    base = lanes_dir(root)
    if base.is_dir():
        for path in base.glob("L-*.json"):
            match = RUN_ID_RE.match(path.stem)
            if match:
                top = max(top, int(match.group(1)))
    return f"L-{top + 1:04d}"


def write_run(root: Path, run: dict) -> None:
    write_lf(run_path(root, run["id"]), json.dumps(run, indent=2, sort_keys=True) + "\n")


def load_runs(root: Path) -> list:
    base = lanes_dir(root)
    if not base.is_dir():
        return []
    runs = []
    for path in sorted(base.glob("L-*.json")):
        if not RUN_ID_RE.match(path.stem):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("id"):
            runs.append(data)
    runs.sort(key=lambda run: str(run.get("id")))
    return runs


def find_run(root: Path, handle: str) -> dict:
    wanted = (handle or "").strip()
    runs = load_runs(root)
    for run in runs:
        if str(run.get("id")).lower() == wanted.lower():
            return run
    mine = [run for run in runs if pascal(str(run.get("agent") or "")) == pascal(wanted)]
    if mine:
        return mine[-1]
    die(f"no lane run matches {handle!r}. `teamwork lane list --all` shows them.", 2)


def live_runs(root: Path) -> list:
    """Runs that are still working: the record says so and no outcome file has landed.

    The wrapper writes ``<id>.outcome.json`` at exit and never rewrites the record, so a
    finished lane keeps ``state: running`` forever. The outcome file is the authority.
    """
    return [
        run for run in load_runs(root) if run.get("state") in LIVE and not read_outcome(root, run)
    ]


def read_outcome(root: Path, run: dict) -> dict:
    path = run_path(root, str(run.get("id"))).with_suffix(".outcome.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def read_result(path: Path) -> dict:
    """The lane's own last word: the ``LANE-RESULT:`` line from its log."""
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(size - LOG_TAIL_BYTES, 0))
            text = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return {}
    matches = RESULT_RE.findall(text)
    if not matches:
        return {}
    verdict, note = matches[-1]
    return {"verdict": verdict.lower(), "note": note.strip()}


def tail(path: Path, lines: int = 40) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-max(lines, 1) :])


def cli_command() -> str:
    override = os.environ.get("TEAMWORK_CLI", "").strip()
    if override:
        return override
    script = Path(__file__).resolve().parents[2] / "scripts" / "teamwork.py"
    if script.is_file():
        if IS_WINDOWS:
            return f'"{sys.executable}" "{script}"'
        return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"
    return "teamwork"


def child_env(root: Path, agent: str, run_id: str) -> dict:
    env = dict(os.environ)
    env["TEAMWORK_ROOT"] = str(root)
    env["TEAMWORK_TEAM"] = root.name
    env["TEAMWORK_LANE"] = run_id
    env["TEAMWORK_LANE_AGENT"] = agent
    src = Path(__file__).resolve().parents[1]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src) + (os.pathsep + existing if existing else "")
    return env


def _builtin_argv(
    host: str, binary: str, prompt: str, model: str, provider: str, session: str
) -> list:
    """The launcher command line for a host CLI, with the host's own rules applied.

    Pi refuses `--provider` on its own ("--provider requires --model"), so the
    provider is only passed when a model is configured; with no model the lane
    runs on the host's default and the provider stays a lease bucket, not a flag.
    A lane that dies in the first second on a rejected argument is the failure this
    rule prevents.
    """
    if host == "pi":
        argv = [binary, "-p"]
        argv += ["--session-id", session] if session else ["--no-session"]
        if model:
            if provider:
                argv += ["--provider", provider]
            argv += ["--model", model]
        return argv + [prompt]
    if host == "claude":
        argv = [binary, "-p"]
        if model:
            argv += ["--model", model]
        return argv + [prompt]
    if host == "codex":
        argv = [binary, "exec"]
        if model:
            argv += ["--model", model]
        return argv + [prompt]
    if host == "opencode":
        argv = [binary, "run"]
        if model:
            argv += ["--model", model]
        return argv + [prompt]
    argv = [binary, "-p"]
    if model:
        argv += ["--model", model]
    return argv + [prompt]


def _template_argv(
    template: str,
    prompt: str,
    packet: Path,
    log: Path,
    agent: str,
    model: str,
    provider: str,
    run_id: str,
    cwd: Path,
) -> list:
    values = {
        "prompt": prompt,
        "packet": str(packet),
        "log": str(log),
        "agent": agent,
        "model": model,
        "provider": provider,
        "cwd": str(cwd),
        "run": run_id,
    }
    argv = []
    used = False
    for token in shlex.split(template):
        if token in PLACEHOLDER_TOKENS:
            argv.append(values[token[1:-1]])
            used = True
        else:
            argv.append(token)
    if not used:
        argv.append(prompt)
    return argv


def launcher_argv(
    root: Path,
    agent: str,
    prompt: str,
    packet: Path,
    log: Path,
    run_id: str,
    model: str,
    provider: str,
    session: str,
    host: str,
    print_only: bool = False,
) -> list:
    """The launcher argv, or a refusal naming the escape hatch.

    ``print_only`` builds the command without starting anything, so a missing host
    binary is not a refusal there: a dry run must be able to show what it would
    run on a machine that does not have the CLI (a CI runner, a reviewer's host).
    """
    template = lane_command(root)
    if template:
        return _template_argv(
            template, prompt, packet, log, agent, model, provider, run_id, project_of(root)
        )
    host = lane_host(root, host)
    if host not in HOST_BINARIES:
        if print_only:
            return _template_argv(
                "{prompt}", prompt, packet, log, agent, model, provider, run_id, project_of(root)
            )
        die(
            f"no launcher for host {host!r}: it is not one of "
            f"{', '.join(sorted(HOST_BINARIES))}. Set TEAMWORK_LANE_CMD to a command "
            "template (placeholders: {prompt} {packet} {log} {agent} {model} {provider} "
            "{cwd} {run}), or set LaneHost/TEAMWORK_AGENT_HOST to a supported host.",
            2,
        )
    found = shutil.which(HOST_BINARIES[host])
    if not found and print_only:
        return _builtin_argv(host, HOST_BINARIES[host], prompt, model, provider, session)
    if not found:
        die(
            f"host {host!r} needs {HOST_BINARIES[host]!r} on PATH and it is not there. "
            "Install it, set TEAMWORK_LANE_CMD to a launcher template, or set LaneHost to "
            "the host you do have.",
            2,
        )
    return _builtin_argv(host, found, prompt, model, provider, session)


@dataclass(frozen=True)
class Assignment:
    """One unit of work handed to one lane: a task, or a review of a deliverable."""

    instance: str
    role: str
    task: str = ""
    title: str = ""
    review_owner: str = ""
    attempt: int = 1
    source_run: str = ""
    profile: str = "standard"
    adopted: bool = False

    @property
    def handle(self) -> str:
        return f"{self.review_owner}/{self.task}" if self.review_owner else self.task


def _assignment_lines(assignments: list) -> list:
    lines = []
    for index, item in enumerate(assignments, start=1):
        if item.review_owner:
            lines.append(f"{index}. review `{item.review_owner}/{item.task}` - {item.title}")
        else:
            lines.append(f"{index}. task `{item.task}` - {item.title}")
    return lines


def build_packet(
    root: Path,
    assignments: list,
    run_id: str,
    attempt: int,
    attempts: int,
    minutes: int,
    tool_budget: int,
    host: str,
    model: str,
    provider: str,
) -> str:
    """The prompt a lane actually executes: identity, work, commands, budget, result."""
    first = assignments[0]
    instance, role = first.instance, first.role
    cli = cli_command()
    project = project_of(root)
    task = first.task or "<T-id>"
    out = [
        f"# Lane packet · {run_id} · {instance} ({role})",
        engine.memory_dream_line(root),
        "",
        f"You are the lane **{instance}**, acting as the **{role}** role of the **{root.name}**",
        f"team. Workspace: `{shown_path(root)}`. Project: `{shown_path(project)}`.",
        f"Host: `{host}`. Model: `{model or '(host default)'}`. Provider: `{provider}`.",
        "",
        "This is a bounded run: finish the assignments below, record the evidence, and exit.",
        f"The CLI for every command is `{cli}`; this packet calls it `tw`.",
        "",
        f"## Assignments (attempt {attempt} of {attempts})",
        *_assignment_lines(assignments),
        "",
        *(
            [*messages.packet_lines(root, instance), ""]
            if messages.packet_lines(root, instance)
            else []
        ),
        "## Read first, in this order",
        f"- `tw load {instance} --task {task}` - your role memory plus the memory pack for",
        "  this assignment (docs/Team/Memory.md 4.1/4.5): lessons and knowledge ranked for the",
        "  task, inside a byte budget, instead of the same static top-10 for every lane.",
        "  The pack is also injected below, so the first read is a re-read, not a discovery.",
        f"- `{shown_path(role_dir(root, role) / 'Role.md')}` - your charter (read it, do not skim it).",
        f"- `{shown_path(agent_dir(root, instance) / 'StartHere.md')}` - your lane directory.",
        "- Anchor-first reading: `rg -n '<anchor>' <path>` then about 30 lines around it.",
        "  Never read a whole document, a whole log or the archive.",
        "",
    ]
    if first.review_owner:
        owner = first.review_owner
        out += [
            "## Review the deliverable",
            "```sh",
            f"tw review {owner} {task} --claim --by {instance}",
            f"tw review {owner} {task} --packet",
            f"tw review {owner} {task} --by {instance} --result pass \\",
            "    --evidence '<cmd @<sha> -> result>'",
            f"tw review {owner} {task} --by {instance} --result fail \\",
            "    --findings '<defect + the command that shows it>' \\",
            "    --detects '<the failure this finding catches>'",
            "# a pass merges at once; a fail returns the task with findings -",
            "# and you never review, merge or credit your own work.",
            "```",
            "",
            "Judge the requirement and the acceptance layer, not the diff style: the",
            "author's self-check answers the boundary, the contract surface, concurrency",
            "and the exact scope. Cite a peer's passing record for a check already green",
            "at this revision instead of re-running it.",
            "",
        ]
    else:
        out += [
            "## Produce",
            "```sh",
            f"tw branch start --agent {instance} --task {task} --worktree",
            "# your own worktree under Runtime/Worktrees: two lanes never share one",
            "# checkout, so a parallel wave cannot check out over another lane.",
            "# ... the work: one coherent change-set, the test first where a defect is proved ...",
            f"tw commit --role {role} --task {task} --type feat --area <area> \\",
            "    --goal '<what and why, one line>' --deliverable '<the files or behaviour>' \\",
            "    --why '<the reason the task exists>' --status '<what is true now>' \\",
            "    --result '<cmd @<sha> -> observed result>' --paths <path>,<path>",
            f"tw selfcheck {role} {task} --by {instance} \\",
            "    --note '<what you proved: boundary, contract, concurrency, scope>' \\",
            "    --test '<exact command @<sha> -> observed result>'",
            f"tw pr open --agent {instance} --task {task} --title '<one line>'",
            "```",
            "",
            "The self-check note is what the Reviewer reads first: answer the empty,",
            "duplicate and second-call case, the contract surface, the shared writes,",
            "and the exact scope you did and did not touch.",
            "",
        ]
    short, pack = engine.memory_injected_layer(
        root, role, task, engine.memorypack.injected_budget(root, role, task), instance
    )
    injected = [
        engine.memorypack.index_block(root, role, task),
        *([short] if short else []),
        pack,
    ]
    out += [
        "## Memory pack for this assignment (injected)",
        "```",
        *injected,
        "```",
        "",
        "## Rules that are not negotiable",
        "- One task, one branch; never commit on the default branch.",
        "- Evidence is a command and its observed result at a revision:",
        "  `<cmd> @<sha> -> <result>`. A claim you cannot reproduce is not evidence.",
        "- Never merge your own work, never weaken or delete a test, never force-push,",
        "  never touch another lane's files or uncommitted work.",
        "- A fact only the CEO or a person holds is not yours to invent: record it with",
        f"  `tw attention add --by {instance} --topic '<blocker>' --ask '<what you need>'`,",
        "  leave the task `blocked`, and stop.",
        "",
        "## Budget",
        f"- at most {tool_budget} tool calls and {minutes} minutes: the supervisor kills this",
        "  run at the minute budget, so stop early rather than rush the end.",
        "- re-running a gate another role already recorded green at this revision is waste:",
        "  cite that record instead.",
        "",
        "## Report back",
        "End with exactly one line, no leading space:",
        f"`{RESULT_MARKER} <ok|blocked|failed> <one sentence naming the revision or the blocker>`",
        "",
        "- `ok` - the assignment is on the board: self-checked + PR open, or a verdict recorded.",
        "- `blocked` - a named fact outside your authority; name it and its attention item.",
        "- `failed` - the work does not hold; name the check that fails.",
        "",
    ]
    return "\n".join(out)


def slot_cap(root: Path, provider: str) -> int:
    limits = engine.load_providers(root)
    return int(limits.get(provider, limits.get("default", 8)))


def acquire_slot(root: Path, agent: str, provider: str, task: str) -> tuple:
    """Take the provider lease this lane will run under; ``(ok, cap)``."""
    cap = slot_cap(root, provider)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"slots-{provider}.lock"):
        engine.reap_slots(root, provider)
        used = engine.used_slots(root, provider)
        name = safe_component(agent)
        now = f"{time.time():.3f}"
        if name in used:
            path = engine.slot_file(root, provider, agent)
            parts = path.read_text(encoding="utf-8").strip().split("|")
            while len(parts) < 4:
                parts.append("-")
            parts[2] = now
            write_lf(path, "|".join(parts) + "\n")
            return True, cap
        if len(used) >= cap:
            return False, cap
        write_lf(
            engine.slot_file(root, provider, agent),
            f"{name}|{now}|{now}|{task or '-'}\n",
        )
        return True, cap


def release_slot(root: Path, provider: str, agent: str, finished: float) -> bool:
    """Hand the lease back, unless a newer one was taken in the same second."""
    if not provider:
        return False
    path = engine.slot_file(root, provider, agent)
    if not path.exists():
        return False
    renewed = engine.slot_renewed(root, provider, agent)
    if renewed and finished and renewed > finished + 1:
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return True


def slot_holders(root: Path, provider: str = "") -> list:
    """Agents currently holding a lease: one provider, or every provider."""
    limits = engine.load_providers(root)
    providers = [provider] if provider else [p for p in sorted(limits) if p != "default"]
    out = []
    for prov in providers:
        out.extend(engine.used_slots(root, prov))
    return out


def terminate(pid: int) -> bool:
    """Signal the lane and its process group; the wrapper made itself the leader."""
    if not pid_alive(pid):
        return False
    if hasattr(os, "killpg"):
        try:
            os.killpg(pid, signal.SIGTERM)
            return True
        except OSError:
            return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    return True


def spawn(
    root: Path,
    assignments: list,
    *,
    model: str = "",
    provider: str = "",
    minutes: int = 0,
    attempt: int = 1,
    attempts: int = 0,
    resume: bool = False,
    tool_budget: int = 0,
    prompt: str = "",
    host: str = "",
    print_only: bool = False,
) -> dict:
    """Start one lane for ``assignments``; return its record, or ``{}`` when not started."""
    first = assignments[0]
    agent = first.instance
    for live in live_runs(root):
        if pascal(str(live.get("agent") or "")) == pascal(agent):
            print(
                f"# {agent} already runs lane {live['id']} - one lane per instance; "
                f"wait for it (`lane wait {live['id']}`) or stop it first"
            )
            return {}
    run_id = next_run_id(root)
    stale = stale_bundle_line(root, host)
    if stale:
        print(stale)
    packet = packet_path(root, agent, run_id)
    log = log_path(root, agent, run_id)
    host = lane_host(root, host)
    profile = first.profile if first.profile in PROFILE_WEIGHT else "standard"
    minutes = minutes or unit_minutes(root, profile)
    attempts = attempts or lane_attempts(root)
    tool_budget = tool_budget or unit_tool_budget(root, profile)
    resolved = engine.resolved_model(root, agent)
    model = model or str(resolved.get("model") or "")
    provider = (
        provider
        or str(resolved.get("provider") or "")
        or os.environ.get("TEAMWORK_PROVIDER", "")
        or "default"
    )
    session = f"teamwork-{root.name}-{agent}".lower() if resume else ""
    text = prompt or build_packet(
        root, assignments, run_id, attempt, attempts, minutes, tool_budget, host, model, provider
    )
    if len(text) > MAX_PROMPT_BYTES and not prompt:
        text = (
            f"Read the lane packet at {packet} and execute it exactly as written. "
            f"End the run with a `{RESULT_MARKER} <ok|blocked|failed> <sentence>` line."
        )
    write_lf(packet, text if text.endswith("\n") else text + "\n")
    argv = launcher_argv(
        root, agent, text, packet, log, run_id, model, provider, session, host, print_only
    )
    if print_only:
        print(f"# packet: {packet}")
        print(f"# log:    {log}")
        print(f"# argv:   {argv}")
        return {}
    ok, cap = acquire_slot(root, agent, provider, first.task)
    if not ok:
        print(f"# {agent}: no free {provider} slot (cap {cap}) - left queued for the next wave")
        return {}
    wrapper = [
        sys.executable,
        "-m",
        "teamwork.lanerun",
        "--run",
        str(run_path(root, run_id)),
        "--timeout",
        str(minutes * 60),
        "--",
        *argv,
    ]
    run = {
        "id": run_id,
        "agent": pascal(agent),
        "role": first.role,
        "task": first.task,
        "title": first.title,
        "review_owner": first.review_owner,
        "attempt": attempt,
        "attempts": attempts,
        "source_run": first.source_run,
        "profile": profile,
        "state": STARTING,
        "host": host,
        "model": model,
        "provider": provider,
        "argv": argv,
        "packet": str(packet),
        "log": str(log),
        "started": _stamp(),
        "created": time.time(),
        "deadline": time.time() + minutes * 60,
        "minutes": minutes,
        "tool_budget": tool_budget,
    }
    write_run(root, run)
    log.parent.mkdir(parents=True, exist_ok=True)
    handle = io.FileIO(log, "a")
    try:
        pid = lanerun.detach(wrapper, handle, child_env(root, agent, run_id), str(project_of(root)))
    except OSError as exc:
        release_slot(root, provider, agent, time.time())
        run["state"] = FAILED
        run["finished"] = _stamp()
        run["error"] = f"{type(exc).__name__}: {exc}"
        write_run(root, run)
        die(f"could not start lane {run_id} ({agent}): {exc}", 2)
    finally:
        handle.close()
    run["pid"] = pid
    run["state"] = RUNNING
    run["heartbeat"] = _stamp()
    write_run(root, run)
    engine.ledger_append(
        root,
        "lane.start",
        agent,
        run_id,
        f"{first.handle or 'lane'} attempt {attempt}/{attempts} on {provider} "
        f"({minutes}m, host {host})",
        "",
        first.role,
    )
    return run


def _task_branch_head(root: Path, role: str, task_id: str) -> str:
    """The revision a task's own branch is at, or ``""`` when it has no branch yet."""
    tasks = parse_tasks(task_file(root, role))
    index = find_task(tasks, task_id)
    if index is None:
        return ""
    branch = str(tasks[index].get("branch") or "")
    if not branch:
        return ""
    result = gitutil.run_git(root, "rev-parse", "--verify", "--quiet", branch)
    return result.stdout.strip() if result.returncode == 0 else ""


def capture_short_layer(root: Path, run: dict) -> dict:
    """The harness writer of the short layer: one note per finished lane (Memory.md 15.1).

    A lane that recorded nothing still leaves its experience behind: the entry names
    the task, the lane's own outcome word and the sentence from its last
    ``LANE-RESULT`` line, at the branch head it exited on. Three cases write
    nothing - a lane that ended without a ``LANE-RESULT`` line (its ``lane.finish``
    record already carries ``exit``/``result``, so nothing is invented), a task whose
    store already holds an entry with ``src`` = that task (the agent wrote its own
    note, so the harness does not echo it), and a second reconcile of the same run.
    """
    task = str(run.get("task") or "")
    role = str(run.get("role") or "")
    instance = str(run.get("agent") or "")
    result = run.get("result") or {}
    verdict = str(result.get("verdict") or "")
    if not (task and role and instance and verdict):
        return {}
    note = " ".join(str(result.get("note") or "").split())
    body = f"{task} {verdict}: {note}" if note else f"{task} {verdict}"
    path = role_dir(root, role) / F_SHORT
    with engine.memory_session(
        root, role, instance, reason=f"lane exit {task}", strict=False
    ) as claim:
        if claim is None:
            return {}
        entries = parse_memory(path)
        if any(str(entry.get("src") or "") == task for entry in entries):
            return {}
        entry = new_entry(
            body,
            f"lane:{task}",
            2,
            by=instance,
            src=task,
            rev=_task_branch_head(root, role, task),
        )
        entries.append(entry)
        write_memory(path, entries, F_SHORT, role)
        engine.ledger_append(
            root,
            "memory.add",
            instance,
            f"lane:{task}",
            f"lane exit note: {task} {verdict}",
            entry["rev"],
            role,
        )
        return parse_memory(path)[-1]


def refresh(root: Path, run: dict) -> dict:
    """Reconcile one record with its process, its outcome file and its budget."""
    if run.get("state") not in LIVE:
        return run
    outcome = read_outcome(root, run)
    finished = time.time()
    if outcome:
        state = str(outcome.get("state") or "")
        if state in ("timeout", "interrupted"):
            run["state"] = TIMEOUT if state == "timeout" else STOPPED
        else:
            run["state"] = EXITED if int(outcome.get("exit") or 0) == 0 else FAILED
        run["exit"] = outcome.get("exit")
        run["finished"] = outcome.get("at") or _stamp()
        run["seconds"] = outcome.get("seconds")
        if outcome.get("error"):
            run["error"] = outcome["error"]
    elif not int(run.get("pid") or 0) and run.get("state") == STARTING:
        created = float(run.get("created") or 0)
        if not created or time.time() - created < STARTING_GRACE_SECONDS:
            run["heartbeat"] = _stamp()
            write_run(root, run)
            return run
        run["state"] = LOST
        run["finished"] = _stamp()
        run["error"] = "never produced a pid inside the start grace window"
    elif not pid_alive(int(run.get("pid") or 0)):
        run["state"] = LOST
        run["finished"] = _stamp()
        run["error"] = "the process ended without writing an outcome file (crash or kill -9)"
    else:
        deadline = float(run.get("deadline") or 0)
        if deadline and finished > deadline:
            terminate(int(run.get("pid") or 0))
            run["state"] = TIMEOUT
            run["finished"] = _stamp()
            run["error"] = "the supervisor killed it at the minute budget"
        else:
            run["heartbeat"] = _stamp()
            write_run(root, run)
            return run
    run["result"] = read_result(Path(str(run.get("log") or "")))
    capture_short_layer(root, run)
    if release_slot(root, str(run.get("provider") or ""), str(run.get("agent") or ""), finished):
        run["slot_released"] = True
    engine.ledger_append(
        root,
        "lane.finish",
        str(run.get("agent") or ""),
        str(run.get("id") or ""),
        f"{run.get('state')} exit={run.get('exit', '-')} "
        f"result={(run.get('result') or {}).get('verdict', '-')} "
        f"task={run.get('task') or run.get('review_owner') or '-'}",
        "",
        str(run.get("role") or ""),
    )
    write_run(root, run)
    return run


def settle(root: Path) -> list:
    """Reconcile every live record. Cheap enough to call before each wave."""
    return [refresh(root, run) for run in load_runs(root)]


def wait_any(root: Path, live: list, poll: float, deadline: float) -> bool:
    """Sleep until one live lane ends (or the deadline). True when something ended."""
    while True:
        for run in live:
            if refresh(root, run).get("state") not in LIVE:
                return True
        if deadline and time.monotonic() > deadline:
            return False
        time.sleep(poll)


def work_handle(run: dict) -> str:
    """What this lane was handed, in the one form every listing prints."""
    task = str(run.get("task") or "")
    owner = str(run.get("review_owner") or "")
    if owner and task:
        return f"{owner}/{task}"
    return task or "packet"


def format_run(run: dict, full: bool = False) -> str:
    result = run.get("result") or {}
    bits = [
        f"{run.get('id')}",
        f"{str(run.get('agent') or ''):14s}",
        f"{str(run.get('state') or ''):9s}",
        f"task={work_handle(run)}",
        f"attempt={run.get('attempt')}/{run.get('attempts')}",
        f"pid={run.get('pid', '-')}",
    ]
    if result.get("verdict"):
        bits.append(f"result={result['verdict']}")
    if full:
        bits.append(f"log={run.get('log')}")
    return " ".join(bits)


def _claim_task(root: Path, assignment: Assignment) -> bool:
    path = task_file(root, assignment.role)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{assignment.role}.lock"):
        tasks = parse_tasks(path)
        index = find_task(tasks, assignment.task)
        if index is None:
            return False
        task = tasks[index]
        raw_holder = str(task.get("claimed_by") or "").strip()
        holder = pascal(raw_holder) if raw_holder else ""
        if holder and holder != pascal(assignment.instance):
            return False
        if task["status"] not in ("todo", "doing"):
            return False
        task["status"] = "doing"
        task["claimed_by"] = assignment.instance
        task["updated"] = today_iso()
        write_tasks(path, tasks, assignment.role)
    engine.ledger_append(
        root,
        "task.claim",
        assignment.instance,
        assignment.task,
        f"lane dispatch: {assignment.title}",
        "",
        assignment.role,
    )
    return True


def ready_tasks(root: Path, role: str) -> list:
    tasks = parse_tasks(task_file(root, role))
    lookup = local_dep_map(tasks)
    cache: dict = {}
    mode, _source = engine.load_pulse_mode(root)
    ready = [task for task in tasks if executable(task, lookup, cache, root)]
    if mode != "auto":
        ready = [task for task in ready if not engine.task_is_inferred(task)]
    ready.sort(
        key=lambda task: (PRIORITY_ORDER.get(task["priority"], 9), task["created"], task["id"])
    )
    return ready


@dataclass(frozen=True)
class Measurement:
    """How much work is in hand, measured from records, and what it justifies.

    ``score`` is a unit weight, not a count: a prose unit is 1, a code unit 2 and a
    security/release/data unit 3, plus one for a bug fix (proving the failure costs
    a cycle). The lane count is ``ceil(score / WEIGHT_PER_LANE)`` bounded by the
    free provider slots and ``LaneMax``, so a single prose task runs one lane and a
    board full of code fans out - the swarm is sized by the work, never by a number
    a caller had to guess.
    """

    score: int
    band: str
    lanes: int
    ready: int
    reviews: int
    adopted: int
    profiles: dict
    profile_minutes: dict
    open_tasks: int
    queues: int
    features: int
    deps: int
    in_flight: int
    free_slots: int
    lane_max: int
    capped_by: str
    tool_budget_override: int

    def lines(self) -> list:
        profiles = (
            ", ".join(f"{name} {count}" for name, count in sorted(self.profiles.items()) if count)
            or "none"
        )
        return [
            f"## complexity (score {self.score} -> {self.band})",
            f"- ready: {self.ready} task unit(s) ({profiles}) from {self.queues} queue(s)",
            f"- reviews: {self.reviews} unclaimed deliverable(s)",
            f"- assigned: {self.adopted} unit(s) claimed with no live lane",
            f"- queue: {self.open_tasks} open task(s), {self.features} open feature(s), "
            f"{self.deps} dependency edge(s)",
            f"- in flight: {self.in_flight} lane(s), {self.free_slots} free provider slot(s)",
            f"- policy: up to {self.lanes} lane(s) this wave, bound by {self.capped_by} "
            f"(LaneMax {self.lane_max}); " + self.budget_text(),
        ]

    def budget_text(self) -> str:
        if self.tool_budget_override:
            return (
                f"budget per unit: {self.tool_budget_override} call(s) "
                "(LaneToolBudget overrides the profile table)"
            )
        used = [name for name in ("fast", "standard", "deep") if self.profiles.get(name)]
        if not used:
            return "no unit to budget"
        return "budget per unit: " + ", ".join(
            f"{name} {PROFILE_TOOL_BUDGET[name]} call(s)/{self.profile_minutes[name]}m"
            for name in used
        )


def unit_minutes(root: Path, profile: str) -> int:
    """The wall clock a unit of this profile gets, scaled from ``LaneMinutes``."""
    factor = PROFILE_MINUTES_FACTOR.get(profile, 1.0)
    return max(int(round(lane_minutes(root) * factor)), 5)


def unit_tool_budget(root: Path, profile: str) -> int:
    """Tool calls a unit of this profile gets; ``LaneToolBudget`` overrides the table."""
    if "LaneToolBudget" in _settings(root):
        return lane_tool_budget(root)
    return PROFILE_TOOL_BUDGET.get(profile, DEFAULT_TOOL_BUDGET)


def complexity_band(score: int) -> str:
    for ceiling, name in COMPLEXITY_BANDS:
        if score <= ceiling:
            return name
    return COMPLEXITY_BANDS[-1][1]


def lane_max(root: Path) -> int:
    return max(_setting_int(root, "LaneMax", DEFAULT_LANE_MAX), 1)


def measure(root: Path, limit: int = 0) -> Measurement:
    """Read the board and decide how many lanes this wave justifies."""
    open_reviews = list(engine.open_review_items(root))
    units = []
    profiles = {"fast": 0, "standard": 0, "deep": 0}
    ready_count = 0
    open_tasks = 0
    queues = 0
    deps = 0
    for role in list_roles(root):
        tasks = parse_tasks(task_file(root, role))
        open_tasks += sum(1 for task in tasks if task["status"] in ("todo", "doing", "selfcheck"))
        deps += sum(
            len([part for part in (task.get("deps") or "").split(",") if part.strip()])
            for task in tasks
        )
        ready = ready_tasks(root, role)
        if ready:
            queues += 1
        for task in ready:
            profile, _reason = engine.review_profile_for(root, role, task)
            units.append((profile, task))
            ready_count += 1
    for owner, task in open_reviews:
        profile, _reason = engine.review_profile_for(root, owner, task)
        units.append((profile, task))
    adopted = adopted_plan(root)
    for item in adopted:
        units.append((item.profile, {"kind": ""}))
    for profile, _task in units:
        profiles[profile] = profiles.get(profile, 0) + 1
    score = sum(
        PROFILE_WEIGHT.get(profile, 2) + (1 if task.get("kind") == "bug" else 0)
        for profile, task in units
    )
    limits = engine.load_providers(root)
    free_slots = sum(
        max(cap - len(engine.used_slots(root, prov)), 0)
        for prov, cap in limits.items()
        if prov != "default"
    )
    ceiling = lane_max(root)
    capped_by = "the complexity score"
    lanes = 0 if not units else max(1, -(-score // WEIGHT_PER_LANE))
    if limit and lanes > limit:
        lanes = limit
        capped_by = "--lanes"
    if lanes > ceiling:
        lanes = ceiling
        capped_by = "LaneMax"
    if lanes > free_slots:
        lanes = free_slots
        capped_by = "free provider slots"
    features = sum(
        1 for record in engine.visible_feature_records(root) if record.get("state") != "done"
    )
    return Measurement(
        score=score,
        band=complexity_band(score),
        lanes=max(lanes, 0),
        ready=ready_count,
        reviews=len(open_reviews),
        adopted=len(adopted),
        profiles=profiles,
        profile_minutes={name: unit_minutes(root, name) for name in PROFILE_WEIGHT},
        open_tasks=open_tasks,
        queues=queues,
        features=features,
        deps=deps,
        in_flight=len(live_runs(root)),
        free_slots=free_slots,
        lane_max=ceiling,
        capped_by=capped_by,
        tool_budget_override=(lane_tool_budget(root) if "LaneToolBudget" in _settings(root) else 0),
    )


def _capacity(root: Path) -> dict:
    """One lane, one assignment: which instances may take work in this wave.

    A lane is a process with its own context, so a wave hands it exactly one unit
    and lets the other idle instances take the rest - that is where the parallelism
    comes from. ``LANE_WIP`` stays the pulse's rule: one lane may hold two tasks in
    one run it starts itself, which is a different shape from a supervised wave.
    """
    claims = engine.held_review_items(root)
    claim_holders = {
        pascal(lane) for _owner, task, lane, _age in claims if engine.review_is_held(task)
    }
    out: dict = {}
    for agent in list_agents(root):
        role = resolve_role(agent)
        if role == "reviewer":
            out[agent] = 0 if pascal(agent) in claim_holders else 1
            continue
        held = sum(
            1
            for task in parse_tasks(task_file(root, role))
            if task["status"] in ("doing", "selfcheck")
            and str(task.get("claimed_by") or "").strip()
            and pascal(str(task.get("claimed_by"))) == pascal(agent)
        )
        out[agent] = 0 if held else 1
    return out


def _profile_of(root: Path, role: str, task: dict) -> str:
    profile, _reason = engine.review_profile_for(root, role, task)
    return profile if profile in PROFILE_WEIGHT else "standard"


def _attempts_used(runs: list, agent: str, task: str) -> int:
    """The highest attempt any run of this lane already spent on this task."""
    used = 0
    for run in runs:
        if str(run.get("task") or "") != task:
            continue
        if pascal(str(run.get("agent") or "")) != pascal(agent):
            continue
        used = max(used, int(run.get("attempt") or 1))
    return used


def adopted_plan(root: Path, attempts: int = 0) -> list:
    """Work the board already assigned to a lane that is not running.

    ``pulse --commit`` claims tasks and review claims before any process exists, and
    a lane can die after claiming. Both leave the same shape: a record saying an
    instance owns the work, and no live process behind it. The supervisor adopts
    that work instead of planning around it, which is what lets one command
    ("pulse --commit --spawn") hand the dispatch to the lanes without losing it.

    Only a claim with no run history is adopted: once a lane has spent an attempt,
    the retry path owns that task. Without that split, adopting a stalled claim
    re-planned the same task forever - measured at 783 waves in one run before the
    bound existed. An exhausted assignment stays claimed and the CEO decides.
    """
    limit = attempts or lane_attempts(root)
    live = {pascal(str(run.get("agent") or "")) for run in live_runs(root)}
    runs = load_runs(root)
    out: list = []
    for role in list_roles(root):
        for task in parse_tasks(task_file(root, role)):
            if task["status"] not in ("doing", "selfcheck"):
                continue
            holder = str(task.get("claimed_by") or "").strip()
            if not holder or pascal(holder) in live:
                continue
            used = _attempts_used(runs, holder, task["id"])
            if used >= 1 or used >= limit:
                continue
            out.append(
                Assignment(
                    holder,
                    role,
                    task["id"],
                    task["title"],
                    attempt=1,
                    profile=_profile_of(root, role, task),
                    adopted=True,
                )
            )
    for owner, task, claim, _age in engine.held_review_items(root):
        lane = str(claim or task.get("review_claim") or "").strip()
        if not lane or pascal(lane) in live:
            continue
        used = _attempts_used(runs, lane, task["id"])
        if used >= 1 or used >= limit:
            continue
        out.append(
            Assignment(
                lane,
                resolve_role(lane),
                task["id"],
                task["title"],
                owner,
                attempt=1,
                profile=_profile_of(root, owner, task),
                adopted=True,
            )
        )
    return out


def dispatch_plan(root: Path, limit: int = 0) -> list:
    """The next wave, computed from the board: ready tasks, then unclaimed reviews."""
    mode, _source = engine.load_pulse_mode(root)
    if mode != "auto":
        return []
    capacity = _capacity(root)
    records = engine.visible_feature_records(root)
    open_reviews = list(engine.open_review_items(root))
    plan: list = []
    by_role: dict = {}
    for agent in sorted(capacity):
        by_role.setdefault(resolve_role(agent), []).append(agent)
    for role, instances in sorted(by_role.items()):
        if role == "reviewer":
            for instance in instances:
                if not open_reviews or capacity[instance] <= 0:
                    continue
                owner, task = open_reviews.pop(0)
                plan.append(
                    Assignment(
                        instance,
                        role,
                        task["id"],
                        task["title"],
                        owner,
                        profile=_profile_of(root, owner, task),
                    )
                )
                capacity[instance] -= 1
            continue
        items = ready_tasks(root, role)
        for instance in instances:
            while items and capacity[instance] > 0:
                index = next(
                    (
                        at
                        for at, candidate in enumerate(items)
                        if engine.feature_executable_by(root, instance, candidate, records)
                    ),
                    None,
                )
                if index is None:
                    break
                item = items.pop(index)
                plan.append(
                    Assignment(
                        instance,
                        role,
                        item["id"],
                        item["title"],
                        profile=_profile_of(root, role, item),
                    )
                )
                capacity[instance] -= 1
    if _review_backlogged(root, open_reviews):
        plan.sort(key=lambda item: 0 if item.review_owner else 1)
    return plan[:limit] if limit else plan


def _review_backlogged(root: Path, unclaimed: list) -> bool:
    """The documented fan-out trigger: more unclaimed reviews than 2x the lanes."""
    lanes = max(len(engine.instances_of(root, "reviewer")), 1)
    return len(unclaimed) > REVIEW_BACKLOG_RATIO * lanes


def retry_plan(root: Path, attempts: int = 0) -> list:
    """Assignments a finished lane did not progress, inside the attempt budget.

    A retry is decided from the record, never from an exit code: a lane that exits
    0 having claimed nothing, and a lane that crashes after claiming, both leave the
    same board state and get the same second attempt.
    """
    limit = attempts or lane_attempts(root)
    out: list = []
    for run in load_runs(root):
        if run.get("retried") or run.get("state") not in TERMINAL:
            continue
        if not run.get("task") or run.get("review_owner"):
            continue
        attempt = int(run.get("attempt") or 1)
        if attempt >= limit:
            continue
        agent = str(run.get("agent") or "")
        role = resolve_role(agent)
        tasks = parse_tasks(task_file(root, role))
        index = find_task(tasks, str(run.get("task")))
        if index is None:
            continue
        task = tasks[index]
        raw_holder = str(task.get("claimed_by") or "").strip()
        holder = pascal(raw_holder) if raw_holder else ""
        progressed = (
            task.get("self_check") == "passed"
            or task.get("pr")
            or task["status"] in ("review", "done", "dropped", "blocked")
            or (holder and holder != pascal(agent))
        )
        if progressed:
            continue
        out.append(
            Assignment(
                agent,
                role,
                task["id"],
                task["title"],
                attempt=attempt + 1,
                source_run=str(run.get("id") or ""),
                profile=str(run.get("profile") or _profile_of(root, role, task)),
            )
        )
    return out


def release_assignment(root: Path, assignment: Assignment) -> bool:
    """Undo a claim this supervisor made when the lane could not start.

    A claim with no process behind it is worse than no claim: the instance looks
    busy, the task never becomes ready again, and the next wave plans around work
    nobody is doing. Only the fields this dispatcher wrote are cleared.
    """
    if assignment.review_owner:
        path = task_file(root, assignment.review_owner)
        with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{assignment.review_owner}.lock"):
            tasks = parse_tasks(path)
            index = find_task(tasks, assignment.task)
            if index is None:
                return False
            task = tasks[index]
            if pascal(str(task.get("review_claim") or "")) != pascal(assignment.instance):
                return False
            for field in (
                "review_claim",
                "review_claim_ts",
                "review_claim_profile",
                "review_claim_lease",
            ):
                task.pop(field, None)
            write_tasks(path, tasks, assignment.review_owner)
        return True
    path = task_file(root, assignment.role)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{assignment.role}.lock"):
        tasks = parse_tasks(path)
        index = find_task(tasks, assignment.task)
        if index is None:
            return False
        task = tasks[index]
        holder = pascal(str(task.get("claimed_by") or ""))
        if holder != pascal(assignment.instance) or task["status"] != "doing":
            return False
        if task.get("self_check") == "passed" or task.get("pr"):
            return False
        task["status"] = "todo"
        task["claimed_by"] = ""
        task["updated"] = today_iso()
        write_tasks(path, tasks, assignment.role)
    return True


def _claim(root: Path, assignment: Assignment) -> bool:
    if assignment.review_owner:
        return engine._pulse_review_claim(
            root, assignment.review_owner, assignment.task, assignment.instance
        )
    return _claim_task(root, assignment)


def cmd_lane(args) -> int:
    root = project_root(args)
    verb = args.lane_cmd
    if verb == "list":
        runs = load_runs(root)
        if not args.all:
            runs = [run for run in runs if run.get("state") in LIVE]
        if args.limit:
            runs = runs[-args.limit :]
        print(f"# Lane runs ({len(runs)}) @ {root}")
        if not runs:
            print("- none")
            return 3
        for run in runs:
            print("- " + format_run(refresh(root, run), full=args.full))
        return 0
    if verb == "logs":
        run = find_run(root, args.handle)
        refresh(root, run)
        body = tail(Path(str(run.get("log") or "")), args.lines)
        print(f"# {run['id']} {run['agent']} [{run['state']}] {run.get('log')}")
        print(body or "# (no output yet)")
        return 0
    if verb == "status":
        if args.handle:
            runs = [refresh(root, find_run(root, args.handle))]
        else:
            runs = settle(root)
        if args.live:
            runs = [run for run in runs if run.get("state") in LIVE]
        print(f"# Lane status ({len(runs)})")
        if not runs:
            print("- no lane record")
            return 3
        for run in runs:
            result = run.get("result") or {}
            print(f"- {format_run(run, full=True)}")
            if result.get("note"):
                print(f"    {result.get('verdict')}: {result['note']}")
            if run.get("error"):
                print(f"    error: {run['error']}")
        return 0
    if verb == "wait":
        deadline = time.monotonic() + (args.timeout if args.timeout > 0 else 0)
        pending = [find_run(root, handle) for handle in args.handles]
        while True:
            live = [run for run in pending if refresh(root, run).get("state") in LIVE]
            if not live:
                break
            if args.timeout > 0 and time.monotonic() > deadline:
                print(f"# {len(live)} lane(s) still running after {args.timeout}s")
                return 3
            time.sleep(min(lane_poll(root), 5.0))
        print(f"# {len(pending)} lane(s) ended")
        for run in pending:
            print("- " + format_run(run, full=True))
        return 0 if all(run.get("state") == EXITED for run in pending) else 1
    if verb == "stop":
        run = find_run(root, args.handle)
        refresh(root, run)
        if run.get("state") not in LIVE:
            print(f"# {run['id']} already {run.get('state')}")
            return 0
        reason = (args.reason or "").strip()
        terminate(int(run.get("pid") or 0))
        for _ in range(100):
            if not pid_alive(int(run.get("pid") or 0)):
                break
            time.sleep(0.05)
        run["state"] = STOPPED
        run["finished"] = _stamp()
        run["stopped_by"] = args.by or "operator"
        run["reason"] = reason or "operator stop"
        release_slot(root, str(run.get("provider") or ""), str(run.get("agent") or ""), time.time())
        engine.ledger_append(
            root,
            "lane.stop",
            run["stopped_by"],
            str(run["id"]),
            f"{run['agent']} {run.get('task') or '-'}: {run['reason']}",
            "",
            str(run.get("role") or ""),
        )
        write_run(root, run)
        print(f"# stopped {run['id']} ({run['agent']}): {run['reason']}")
        return 0
    if verb == "reap":
        touched = 0
        for run in load_runs(root):
            before = run.get("state")
            after = refresh(root, run).get("state")
            if before in LIVE and after not in LIVE:
                touched += 1
                print(f"- reaped {run['id']} ({run['agent']}) -> {after}")
        for path in lanes_dir(root).glob("*.tmp"):
            try:
                path.unlink()
            except OSError:
                pass
        print(f"# reaped {touched} lane(s); {len(live_runs(root))} still running")
        return 0
    if verb == "preempt":
        return _lane_preempt(root, args)
    if verb == "resume":
        return _lane_resume(root, args)
    return _lane_start(root, args)


def _lane_preempt(root: Path, args) -> int:
    """Stop a lane for an urgent message and pause the task it was working on.

    Preemption is the supervisor's action, never a peer's: one process cannot
    interrupt another agent mid-turn, so the lane is stopped, its task is marked
    ``paused`` with the message that displaced it, and the next wave runs the
    urgent work. ``lane resume`` puts the task back on the queue.
    """
    run = find_run(root, args.handle)
    refresh(root, run)
    message_id = (args.message or "").strip()
    agent = str(run.get("agent") or "")
    task_id = str(run.get("task") or "")
    if run.get("state") not in LIVE:
        print(f"# {run['id']} already {run.get('state')}; nothing to preempt")
        return 0
    reason = (args.reason or "").strip() or f"urgent message {message_id or '(unnamed)'}"
    terminate(int(run.get("pid") or 0))
    for _ in range(100):
        if not pid_alive(int(run.get("pid") or 0)):
            break
        time.sleep(0.05)
    run["state"] = STOPPED
    run["finished"] = _stamp()
    run["stopped_by"] = args.by or "supervisor"
    run["reason"] = reason
    run["preempted_by"] = message_id
    release_slot(root, str(run.get("provider") or ""), agent, time.time())
    write_run(root, run)
    paused = None
    if task_id:
        note = f"paused for {message_id} ({reason})" if message_id else f"paused ({reason})"
        paused = engine.set_task_status(
            root, task_id, "paused", note=note, by=run["stopped_by"], paused_by=message_id
        )
    engine.ledger_append(
        root,
        "lane.preempt",
        str(run["stopped_by"]),
        str(run["id"]),
        f"{agent} {task_id or '-'} paused for {message_id or reason}",
        "",
        str(run.get("role") or ""),
    )
    print(f"# {run['id']} stopped; {agent}" + (f" task {task_id} paused" if paused else " freed"))
    print(f"#   next: run the urgent message, then `tw lane resume {task_id}`")
    return 0


def _lane_resume(root: Path, args) -> int:
    """Put a paused task back on its queue at `doing`, which is where preemption found it."""
    task = engine.set_task_status(root, args.task, "doing", note="", by=args.by or "supervisor")
    if task is None:
        print(f"# no task '{args.task}' on any queue")
        return 2
    print(f"# {args.task} resumed: doing ({task.get('claimed_by') or 'unclaimed'})")
    return 0


def _lane_start(root: Path, args) -> int:
    agent = engine.validate_actor(root, args.agent, "lane")[0]
    role = resolve_role(agent)
    if args.prompt_file and args.prompt:
        die("pass --prompt or --prompt-file, not both", 2)
    prompt = args.prompt or ""
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    claimed_here = False
    if args.review_owner:
        if not args.task:
            die("--review-owner needs --task <T-id> (the deliverable to review)", 2)
        owner = resolve_role(args.review_owner)
        tasks = parse_tasks(task_file(root, owner))
        index = find_task(tasks, args.task)
        if index is None:
            die(f"no task {args.task} on the {owner} queue", 2)
        assignment = Assignment(
            agent,
            role,
            args.task,
            tasks[index]["title"],
            owner,
            args.attempt,
            profile=_profile_of(root, owner, tasks[index]),
        )
        if not args.print and not engine._pulse_review_claim(root, owner, args.task, agent):
            die(
                f"{owner}/{args.task} is not reviewable for {agent}: it is already "
                "passed, held by another lane, or not in review",
                2,
            )
    elif args.task:
        matches = engine.matching_tasks(root, args.task, role)
        if not matches:
            die(f"no task {args.task} on the {role} queue", 2)
        task = matches[0][0]
        claimed_here = task["status"] == "todo"
        assignment = Assignment(
            agent,
            role,
            task["id"],
            task["title"],
            attempt=args.attempt,
            profile=_profile_of(root, role, task),
        )
        if not args.print and not _claim_task(root, assignment):
            die(
                f"{task['id']} is not claimable by {agent}: it is done, blocked, or held "
                f"by {task.get('claimed_by') or 'another lane'}",
                2,
            )
    else:
        assignment = Assignment(agent, role, attempt=args.attempt)
    assignments = [assignment]
    run = spawn(
        root,
        assignments,
        model=args.model,
        provider=args.provider,
        minutes=args.minutes if args.minutes is not None else 0,
        attempt=args.attempt,
        attempts=args.attempts or lane_attempts(root),
        resume=args.resume,
        tool_budget=args.tool_budget or 0,
        prompt=prompt,
        host=args.host,
        print_only=args.print,
    )
    if not run:
        if claimed_here and not args.print:
            release_assignment(root, assignment)
        return 0 if args.print else 3
    print(
        f"# lane {run['id']} started: {run['agent']} ({run['role']})"
        f" <- {assignment.handle or 'packet'} on {run['provider']}"
        f" for {run['minutes']}m (pid {run['pid']})"
    )
    print(f"# packet {run['packet']}")
    print(f"# log    {run['log']}")
    print(f"# follow `teamwork lane status {run['id']}` / `teamwork lane logs {run['id']}`")
    return 0


def _swarm_dry_run(root: Path, measurement, cap: int, fixed: bool, attempts: int) -> int:
    retries = retry_plan(root, attempts)
    target = cap if fixed else max(measurement.lanes, min(len(retries), measurement.lane_max))
    target = min(target, measurement.lane_max, measurement.free_slots or target)
    taken = {pascal(item.instance) for item in retries}
    fresh = dispatch_plan(root, max(target - len(retries), 0)) if target > len(retries) else []
    next_wave = list(retries) + [item for item in fresh if pascal(item.instance) not in taken]
    next_wave = next_wave[:target] if target else []
    print(f"## wave 1 (dry run, {len(next_wave)} lane(s) would start)")
    for item in next_wave:
        origin = f"retry of {item.source_run}" if item.source_run else "ready"
        print(
            f"- {item.instance:14s} <- {item.handle or 'packet'}"
            f" attempt {item.attempt}/{attempts} profile {item.profile} ({origin})"
        )
    if not next_wave:
        print("- nothing runnable: no ready task, no unclaimed review, no retry")
        return 3
    return 0


def group_launches(launches: list) -> list:
    """One lane per instance: at most two units, retry-first, no duplicate handle.

    The packet already allows two assignments, so a lane that owns two claimed units
    takes both in one run instead of being refused a second process. A retry and the
    adopted copy of the same task are one unit: the retry wins, because it carries
    the attempt number.
    """
    groups: dict = {}
    seen: set = set()
    for item in launches:
        key = (pascal(item.instance), item.handle)
        if key in seen:
            continue
        seen.add(key)
        bucket = groups.setdefault(pascal(item.instance), [])
        if len(bucket) >= 2:
            continue
        bucket.append(item)
    return list(groups.values())


def _wave_target(measurement, retries: int, cap: int, fixed: bool) -> int:
    """Lanes this wave: the policy, or the caller's fixed count, never over the caps."""
    if fixed:
        target = cap
    else:
        target = max(measurement.lanes, min(retries, measurement.lane_max))
    target = min(target, measurement.lane_max)
    if measurement.free_slots:
        target = min(target, measurement.free_slots)
    return max(target, 0)


def cmd_swarm(args) -> int:
    root = project_root(args)
    if not (root / DIR_RUNTIME).is_dir() and not (root / "Roles").is_dir():
        die(f"no workspace at {root}: run `teamwork.py init` first (or fix TEAMWORK_ROOT)")
    mode, source = engine.load_pulse_mode(root, args.mode or "")
    minutes = args.minutes if args.minutes is not None else swarm_minutes(root)
    poll = args.poll if args.poll else lane_poll(root)
    attempts = lane_attempts(root)
    cap = max(int(args.lanes or 0), 0)
    fixed = bool(getattr(args, "fixed", False))
    if fixed and not cap:
        die("--fixed needs --lanes N: it turns the complexity policy off", 2)
    measurement = measure(root, cap)
    print(f"# Swarm ({root})")
    print(
        f"# accept mode: {mode} (from {source}) | attempts {attempts}"
        f" | swarm budget {minutes or 'none'}m | sizing: " + ("fixed" if fixed else "complexity")
    )
    for line in measurement.lines():
        print(line)
    print(engine.memory_dream_line(root))
    if getattr(args, "scale", True):
        scale_plan = engine._scale_plan(root)
        if scale_plan:
            print(
                "## scale plan ("
                + ", ".join(f"{role} +{count}" for role, count in scale_plan)
                + ")"
            )
            if not args.dry_run:
                added = engine._apply_scale(root, scale_plan, args.by or "ceo")
                if added:
                    print(f"# scaled to the work: added {', '.join(added)}")
                    measurement = measure(root, cap)
                    for line in measurement.lines():
                        print(line)
        print()
    if args.dry_run:
        return _swarm_dry_run(root, measurement, cap, fixed, attempts)
    if mode != "auto":
        die(
            f"swarm dispatch needs the accept mode auto, and it is {mode} (from {source}). "
            "Set PulseMode to auto in Settings.json or pass --mode auto when you mean it.",
            2,
        )
    engine.reap_slots(root)
    actor = engine.validate_actor(root, args.by or "ceo", "lane supervisor")[0]
    deadline = time.monotonic() + minutes * 60 if minutes else 0.0
    engine.ledger_append(
        root,
        "swarm.start",
        actor,
        "-",
        f"complexity={measurement.score}/{measurement.band} "
        f"lanes<={cap or measurement.lanes} attempts={attempts} budget={minutes or 'none'}m"
        f" sizing={'fixed' if fixed else 'complexity'}",
    )
    started: list = []
    wave = 0
    previous = -1
    stalled = 0
    last_signature = None
    while True:
        if deadline and time.monotonic() > deadline:
            print(f"# swarm budget of {minutes}m reached")
            break
        if args.waves and wave >= args.waves:
            break
        settle(root)
        preempt_urgent(root, actor)
        busy_now = {
            pascal(str(run.get("agent") or ""))
            for run in live_runs(root)
            if run.get("state") in LIVE
        }
        for name in urgent_instances(root):
            if pascal(name) in busy_now:
                continue
            role = resolve_role(name)
            started_message = spawn(
                root,
                [
                    Assignment(
                        instance=name,
                        role=role,
                        task="",
                        title="drain the urgent mailbox",
                        profile="standard",
                    )
                ],
                prompt=message_packet(root, name, unit_minutes(root, "standard")),
                minutes=unit_minutes(root, "standard"),
            )
            if started_message:
                print(f"- {name:14s} <- urgent mailbox ({started_message['id']})")
        measurement = measure(root, cap)
        retries = retry_plan(root, attempts)
        target = _wave_target(measurement, len(retries), cap, fixed)
        if previous >= 0 and target != previous:
            rising = "up" if target > previous else "down"
            print(
                f"# scale {rising}: {previous} -> {target} lane(s) "
                f"(score {measurement.score} -> {measurement.band}, "
                f"bound by {measurement.capped_by})"
            )
            engine.ledger_append(
                root,
                "swarm.scale",
                actor,
                "-",
                f"{previous} -> {target} lane(s) at score {measurement.score} ({measurement.band})",
            )
        previous = target
        launches = list(retries) + adopted_plan(root)
        taken = {pascal(item.instance) for item in launches}
        need = target - len(taken)
        if need > 0:
            for item in dispatch_plan(root, need):
                if pascal(item.instance) in taken:
                    continue
                taken.add(pascal(item.instance))
                launches.append(item)
        groups = group_launches(launches)[:target] if target else []
        launches = [item for group in groups for item in group]
        signature = (
            tuple(sorted(item.handle for item in launches)),
            tuple(sorted(f"{item.instance}:{item.attempt}" for item in launches)),
        )
        stalled = stalled + 1 if signature == last_signature else 0
        last_signature = signature
        if stalled >= STALE_WAVE_LIMIT:
            print(
                "# three waves planned the same assignments: the board did not move, "
                "so the swarm stops and leaves them to the CEO"
            )
            break
        if not launches:
            if not live_runs(root):
                print("# no runnable work and no live lane: swarm idle - stopping")
                break
            wait_any(root, live_runs(root), poll, deadline)
            continue
        wave += 1
        print(
            f"## wave {wave}: {len(groups)} lane(s), {len(launches)} unit(s)"
            f" [score {measurement.score} -> {measurement.band}, target {target} lane(s)]"
        )
        started_now = []
        for group in groups:
            fresh = [item for item in group if not item.source_run and not item.adopted]
            claimed = []
            lost = False
            for item in fresh:
                if _claim(root, item):
                    claimed.append(item)
                else:
                    print(f"- {item.instance:14s} <- {item.handle}: claim lost, skipped")
                    lost = True
            if lost and not claimed:
                continue
            units = sorted(
                [item for item in group if item not in fresh] + claimed,
                key=lambda item: -PROFILE_WEIGHT.get(item.profile, 2),
            )
            run = spawn(
                root,
                units,
                minutes=args.lane_minutes if args.lane_minutes is not None else 0,
                attempt=max(item.attempt for item in units),
                attempts=attempts,
                host=args.host,
            )
            if not run:
                for item in claimed:
                    release_assignment(root, item)
                continue
            started_now.append(run)
            started.append(run)
            for item in units:
                if item.source_run:
                    source_run = find_run(root, item.source_run)
                    source_run["retried"] = True
                    write_run(root, source_run)
                origin = (
                    f"retry {item.source_run}"
                    if item.source_run
                    else ("adopted" if item.adopted else "ready")
                )
                print(
                    f"- {run['id']} {run['agent']:14s} <- {item.handle or 'packet'}"
                    f" attempt {item.attempt}/{attempts} profile {item.profile}"
                    f" ({origin})"
                )
            print(
                f"  {run['minutes']}m, {run['tool_budget']} call(s), pid {run['pid']},"
                f" packet {run['packet']}"
            )
        engine.ledger_append(
            root,
            "swarm.wave",
            actor,
            "-",
            f"wave {wave}: started {len(started_now)} lane(s) at score "
            f"{measurement.score} ({measurement.band}), target {target}: "
            + ", ".join(str(run["id"]) for run in started_now),
        )
        live = live_runs(root)
        if live:
            wait_any(root, live, poll, deadline)
    settled = {str(run.get("id")): run for run in settle(root)}
    started = [settled.get(str(run.get("id")), run) for run in started]
    print()
    print(f"## swarm summary ({len(started)} lane(s) started in {wave} wave(s))")
    if not started:
        print("- nothing ran")
    for run in started:
        result = run.get("result") or {}
        print(f"- {format_run(run)}" + (f"  {result.get('note', '')}" if result else ""))
    blocked = [run for run in started if (run.get("result") or {}).get("verdict") == "blocked"]
    failed = [run for run in started if run.get("state") in (FAILED, TIMEOUT, LOST)]
    if blocked:
        print(f"# {len(blocked)} lane(s) reported blocked: read `teamwork attention list`")
    if failed:
        print(f"# {len(failed)} lane(s) died without finishing: `teamwork lane logs <id>`")
    engine.ledger_append(
        root,
        "swarm.stop",
        actor,
        "-",
        f"{wave} wave(s), {len(started)} lane(s), blocked={len(blocked)} failed={len(failed)}",
    )
    return 0


def add_parsers(sub, common) -> None:
    """`lane` and `swarm` command surface."""
    s = sub.add_parser("lane", parents=[common], help="start/inspect/stop one agent lane")
    lsub = s.add_subparsers(dest="lane_cmd", required=True)
    p = lsub.add_parser("start", parents=[common], help="start one lane process")
    p.add_argument("--agent", required=True, help="the instance that will act (developer-1)")
    p.add_argument("--task", default="", help="task to claim and hand to the lane")
    p.add_argument("--review-owner", default="", help="role whose task this lane reviews")
    p.add_argument("--prompt", default="", help="override the generated packet")
    p.add_argument("--prompt-file", default="", help="read the packet from a file")
    p.add_argument("--model", default="", help="model override (default: the agent's)")
    p.add_argument("--provider", default="", help="provider whose slot this lane leases")
    p.add_argument("--minutes", type=int, default=None, help="wall-clock budget in minutes")
    p.add_argument("--tool-budget", type=int, default=0, help="tool calls the packet allows")
    p.add_argument("--attempt", type=int, default=1, help="attempt number, for the packet")
    p.add_argument("--attempts", type=int, default=0, help="attempt budget, for the packet")
    p.add_argument("--resume", action="store_true", help="reuse the lane's host session")
    p.add_argument("--host", default="", help="host CLI to launch (default: detected)")
    p.add_argument("--print", action="store_true", help="print packet and argv, start nothing")
    p.set_defaults(func=cmd_lane)
    p = lsub.add_parser("list", parents=[common], help="live lane records (--all: history)")
    p.add_argument("--all", action="store_true", help="include ended lanes")
    p.add_argument("--limit", type=int, default=0, help="show the last N records")
    p.add_argument("--full", action="store_true", help="include the log path")
    p.set_defaults(func=cmd_lane)
    p = lsub.add_parser("status", parents=[common], help="reconcile and print lane state")
    p.add_argument("handle", nargs="?", default="", help="run id or instance name")
    p.add_argument("--live", action="store_true", help="only lanes still running")
    p.set_defaults(func=cmd_lane)
    p = lsub.add_parser("logs", parents=[common], help="tail a lane's log")
    p.add_argument("handle")
    p.add_argument("--lines", type=int, default=40)
    p.set_defaults(func=cmd_lane)
    p = lsub.add_parser("wait", parents=[common], help="block until lanes end")
    p.add_argument("handles", nargs="+")
    p.add_argument("--timeout", type=int, default=0, help="seconds to wait, 0 = forever")
    p.set_defaults(func=cmd_lane)
    p = lsub.add_parser("stop", parents=[common], help="stop a live lane and free its slot")
    p.add_argument("handle")
    p.add_argument("--reason", default="", help="why it is stopped (recorded)")
    p.add_argument("--by", default="", help="who stopped it")
    p.set_defaults(func=cmd_lane)
    p = lsub.add_parser("reap", parents=[common], help="reconcile dead lanes and free slots")
    p.set_defaults(func=cmd_lane)
    p = lsub.add_parser(
        "preempt",
        parents=[common],
        help="stop a lane for an urgent message and pause the task it was working on",
    )
    p.add_argument("handle")
    p.add_argument("--message", default="", help="the urgent message id that displaces it")
    p.add_argument("--reason", default="", help="why (recorded)")
    p.add_argument("--by", default="", help="who preempted it")
    p.set_defaults(func=cmd_lane)
    p = lsub.add_parser(
        "resume", parents=[common], help="put a paused task back on its queue at doing"
    )
    p.add_argument("task")
    p.add_argument("--by", default="", help="who resumed it")
    p.set_defaults(func=cmd_lane)

    s = sub.add_parser(
        "swarm",
        parents=[common],
        help="dynamic wave supervisor: dispatch, spawn, retry, review, stop",
    )
    ssub = s.add_subparsers(dest="swarm_cmd", required=True)
    p = ssub.add_parser("run", parents=[common], help="run waves until nothing is runnable")
    p.add_argument(
        "--lanes",
        type=int,
        default=0,
        help="cap on lanes per wave (default: the complexity policy, LaneMax)",
    )
    p.add_argument(
        "--fixed",
        action="store_true",
        help="turn the complexity policy off and run exactly --lanes every wave",
    )
    p.add_argument("--waves", type=int, default=0, help="max waves, 0 = until idle")
    p.add_argument("--minutes", type=int, default=None, help="swarm budget, 0 = none")
    p.add_argument("--lane-minutes", type=int, default=None, help="per-lane budget override")
    p.add_argument("--poll", type=float, default=0.0, help="seconds between supervisor polls")
    p.add_argument("--mode", default="", help="accept mode override for this run")
    p.add_argument("--host", default="", help="host CLI to launch (default: detected)")
    p.add_argument("--by", default="", help="supervisor identity (default: ceo)")
    p.add_argument("--dry-run", action="store_true", help="print the next wave only")
    p.add_argument(
        "--no-scale",
        dest="scale",
        action="store_false",
        help="dispatch to the current roster only; never add instances for the wave",
    )
    p.set_defaults(func=cmd_swarm)


def urgent_instances(root: Path) -> list:
    """Instances holding a pending urgent message: they preempt, then run."""
    out = []
    for name in engine.list_agents(root):
        if messages.urgent_for(root, name):
            out.append(name)
    return out


def preempt_urgent(root: Path, actor: str) -> list:
    """Stop the live lane of every instance with an urgent message; pause its task.

    Returns the instances that were preempted. The caller starts their lanes for
    the message, so the paused task resumes only after the urgent work is closed.
    """
    freed = []
    for name in urgent_instances(root):
        live = [
            run for run in live_runs(root) if pascal(str(run.get("agent") or "")) == pascal(name)
        ]
        if not live:
            continue
        run = live[0]
        message = messages.urgent_for(root, name)[0]
        print(
            f"# preempt: {name} is on {run['id']} ({run.get('task') or '-'}) and holds "
            f"{message['id']} [urgent] {message['subject']}"
        )
        terminate(int(run.get("pid") or 0))
        for _ in range(100):
            if not pid_alive(int(run.get("pid") or 0)):
                break
            time.sleep(0.05)
        run["state"] = STOPPED
        run["finished"] = _stamp()
        run["stopped_by"] = actor
        run["reason"] = f"preempted by {message['id']} [urgent]"
        run["preempted_by"] = message["id"]
        release_slot(root, str(run.get("provider") or ""), name, time.time())
        write_run(root, run)
        if run.get("task"):
            engine.set_task_status(
                root,
                str(run["task"]),
                "paused",
                note=f"paused for {message['id']} [urgent]: {message['subject']}",
                by=actor,
                paused_by=message["id"],
            )
        engine.ledger_append(
            root,
            "lane.preempt",
            actor,
            str(run["id"]),
            f"{name} {run.get('task') or '-'} paused for {message['id']} [urgent]",
            "",
            str(run.get("role") or ""),
        )
        freed.append(name)
    return freed


def message_packet(root: Path, instance: str, minutes: int) -> str:
    """The packet for a lane that exists only to drain an urgent mailbox."""
    role = resolve_role(instance)
    pending = messages.urgent_for(root, instance)
    cli = cli_command()
    lines = [
        f"# Mailbox lane · {instance} ({role})",
        "",
        f"You are **{instance}** of the **{root.name}** team. The supervisor stopped your "
        "previous assignment because an urgent message arrived; that task is `paused` and "
        "resumes when this mailbox is empty.",
        "",
        f"The CLI is `{cli}`; this packet calls it `tw`.",
        "",
        "## Do this, in priority order",
    ]
    for message in pending:
        lines.append(
            f"1. `tw message take {message['id']} --for {instance} --by {instance}` - "
            f"from {message['from']}, task {message['task'] or '-'}: {message['subject']}"
        )
        if message.get("body"):
            lines.append(f"   body: {message['body']}")
    lines += [
        "",
        "Do the work each message asks for, then close it:",
        f"`tw message done <id> --for {instance} --by {instance} --result '<what you did + evidence>'`",
        "",
        "If a message needs a code change, do it on a task branch as usual "
        "(`tw branch start --agent {0} --task <T-id>`, commit, self-check, PR). "
        "A message that asks for a fact is answered with `tw message send` back to its sender.",
        "",
        "When the mailbox is empty, print the result line and exit; the supervisor resumes the "
        "paused task on its next wave.",
        "",
        f"## Budget\n- at most 10 tool calls and {minutes} minutes.",
        "",
        "## Report back",
        f"`{RESULT_MARKER} <ok|blocked|failed> <one sentence naming the messages you closed>`",
        "",
    ]
    return "\n".join(lines)
