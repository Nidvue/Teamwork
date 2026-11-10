#!/usr/bin/env python3
"""Prove the native fan-out: the engine runs its maximum lane count with no host plugin.

The operator question is how we know the team parallelises without ``pi-subagents`` and
uses the engine's maximum lane count. This script answers with a measurement, not a
claim: it reads the capacity from the team records, starts that many lanes through the
real ``teamwork lane start`` path, samples the lane records and the live processes while
they run, and exits 0 only when the peak concurrency equals the capacity and every lane
exited cleanly.

Offline mode is the engine's own escape hatch: set ``TEAMWORK_LANE_CMD``, or pass
``--offline``, and the launcher is a fake that sleeps and prints a result, so CI runs the
whole proof with no model and no network.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if Path(_SRC).is_dir():
    while _SRC in sys.path:
        sys.path.remove(_SRC)
    sys.path.insert(0, _SRC)

from teamwork.config import SETTINGS_NON_PROVIDER  # noqa: E402

PLUGIN = "pi-subagents"
LIVE = ("starting", "running")
SKIP_DIRS = {"docs/Team", ".pi", ".git", ".venv", "site", "dist", "node_modules", "__pycache__"}
SELF = {"scripts/lane_proof.py", "tests/unit/test_lane_proof.py"}
SUFFIXES = {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".txt", ".sh"}
MANIFESTS = ("pyproject.toml", "package.json", "mkdocs.yml")
PROMPT = "Reply with exactly one line and nothing else: LANE-RESULT: ok lane proof"
FAKE = (
    "import sys, time\n"
    "time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 2.0)\n"
    "print('LANE-RESULT: ok offline lane proof')\n"
)


def default_project() -> Path:
    root = os.environ.get("TEAMWORK_ROOT", "").strip()
    if root:
        team = Path(root).expanduser().resolve()
        if len(team.parents) > 3 and team.parents[2].name == ".pi":
            return team.parents[3]
    return repo_root()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def cli_path() -> Path:
    return repo_root() / "scripts" / "teamwork.py"


def team_root(project: Path) -> Path:
    teams = project / ".pi" / "Teamwork" / "Teams"
    named = teams / project.name
    if named.is_dir():
        return named
    found = sorted(path for path in teams.iterdir() if path.is_dir()) if teams.is_dir() else []
    return found[0] if len(found) == 1 else named


def settings(root: Path) -> dict:
    try:
        data = json.loads((root / "Settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def lane_max(root: Path) -> int:
    try:
        return max(int(settings(root).get("LaneMax", 32)), 1)
    except (TypeError, ValueError):
        return 32


def free_slots(root: Path) -> tuple[int, dict]:
    """Free capacity per bucket the engine dispatches on, `default` included.

    `default` is a real bucket (engine.cmd_slot: `limits.get(provider, limits.get("default", 8))`),
    so a proof that skips it prints capacity the engine cannot afford.
    """
    rows: dict = {}
    total = 0
    for provider, cap in settings(root).items():
        if provider in SETTINGS_NON_PROVIDER:
            continue
        if not isinstance(cap, int):
            continue
        used = len(list((root / "Runtime" / "Slots" / provider).glob("*.slot")))
        free = max(cap - used, 0)
        rows[provider] = free
        total += free
    return total, rows


def load_runs(root: Path) -> list:
    base = root / "Runtime" / "Lanes"
    runs = []
    for path in sorted(base.glob("L-*.json")) if base.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("id"):
            runs.append(data)
    return runs


def outcome(root: Path, run_id: str) -> dict:
    path = root / "Runtime" / "Lanes" / f"{run_id}.outcome.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def state_of(root: Path, run: dict) -> str:
    result = outcome(root, str(run.get("id")))
    if result:
        state = str(result.get("state") or "")
        if state in ("timeout", "interrupted"):
            return "timeout"
        return "exited" if int(result.get("exit") or 0) == 0 else "failed"
    return str(run.get("state") or "")


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def idle_agents(root: Path, runs: list) -> list:
    busy = {str(run.get("agent") or "") for run in runs if state_of(root, run) in LIVE}
    base = root / "Agents"
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and p.name not in busy)


def slot_leases(root: Path) -> set:
    base = root / "Runtime" / "Slots"
    return {path for path in base.glob("*/*.slot")} if base.is_dir() else set()


def agent_dirs(root: Path) -> set:
    base = root / "Agents"
    return {path for path in base.iterdir() if path.is_dir()} if base.is_dir() else set()


def drop_own_scratch(root: Path, leases: set, dirs: set) -> tuple[int, int]:
    """Release what this run created, so the next run sees the same capacity.

    A lane exit leaves its slot lease behind and `lane start` creates an agent directory
    for the instance it runs, so an uncleaned run shrinks the capacity of every run after
    it. Only leases and empty directories absent before the run are touched: a live lane's
    lease and any pre-existing agent directory are never removed.
    """
    released = 0
    for path in slot_leases(root) - leases:
        path.unlink(missing_ok=True)
        released += 1
    removed = 0
    for path in agent_dirs(root) - dirs:
        try:
            path.rmdir()
        except OSError:
            continue
        removed += 1
    return released, removed


def tracked_files(project: Path) -> list:
    try:
        done = subprocess.run(
            ["git", "-C", str(project), "ls-files", "-z"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if done.returncode != 0:
        return []
    return [name for name in done.stdout.split("\0") if name]


def plugin_findings(project: Path, host_manifest: Path) -> list:
    """A plugin fails the proof when it is declared, installed, or named in a shipped file.

    The shipped surface is the tracked tree: a host plugin is not a dependency of this
    repository, so no tracked file may name it. Team records under ``docs/Team`` and the
    local ``.pi`` state are history, not surfaces, and the proof's own two files must name
    the plugin to check it.
    """
    findings = []
    for name in MANIFESTS:
        path = project / name
        if path.is_file() and PLUGIN in path.read_text(encoding="utf-8", errors="replace"):
            findings.append(f"declared in {name}")
    if host_manifest.is_file():
        text = host_manifest.read_text(encoding="utf-8", errors="replace")
        if PLUGIN in text:
            findings.append(f"installed in {host_manifest}")
    for rel in tracked_files(project):
        if rel in SELF or Path(rel).suffix not in SUFFIXES:
            continue
        if any(rel == skip or rel.startswith(skip + "/") for skip in SKIP_DIRS):
            continue
        try:
            text = (project / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if PLUGIN in text:
            findings.append(f"named in {rel}")
    return findings


def start_lane(project: Path, agent: str) -> tuple[int, str, str]:
    argv = [
        sys.executable,
        str(cli_path()),
        "--project",
        str(project),
        "lane",
        "start",
        "--agent",
        agent,
        "--prompt",
        PROMPT,
    ]
    env = {**os.environ, "TEAMWORK_ROOT": str(team_root(project))}
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=300, env=env)
    except subprocess.TimeoutExpired:
        return 1, "", "lane start timed out"
    text = done.stdout + done.stderr
    run_id = ""
    for token in text.split():
        if token.startswith("L-") and token[2:].isdigit():
            run_id = token
            break
    return done.returncode, run_id, text


def wait(root: Path, ids: list, timeout: float, poll: float) -> tuple[int, int]:
    peak_records = 0
    peak_pids = 0
    deadline = time.monotonic() + timeout
    while True:
        runs = [run for run in load_runs(root) if str(run.get("id")) in ids]
        live = [run for run in runs if state_of(root, run) in LIVE]
        alive = [run for run in live if pid_alive(int(run.get("pid") or 0))]
        peak_records = max(peak_records, len(live))
        peak_pids = max(peak_pids, len(alive))
        ended = (
            all(state_of(root, run) not in LIVE for run in runs) if len(runs) == len(ids) else False
        )
        if ended or time.monotonic() > deadline:
            return peak_records, peak_pids
        time.sleep(poll)


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--project",
        default=str(default_project()),
        help="project root (default: this checkout, or the team's project)",
    )
    parser.add_argument("--lanes", type=int, default=0, help="cap on lanes (default: the capacity)")
    parser.add_argument(
        "--timeout", type=float, default=180.0, help="seconds to wait for the lanes"
    )
    parser.add_argument("--poll", type=float, default=0.05, help="seconds between samples")
    parser.add_argument("--offline", action="store_true", help="use a fake launcher, no model")
    args = parser.parse_args(argv)
    project = Path(args.project).resolve()
    root = team_root(project)
    if not root.is_dir():
        print(f"# no team at {root}: run `teamwork init` first")
        return 2
    host_manifest = Path(
        os.environ.get(
            "TEAMWORK_PI_MANIFEST", str(Path.home() / ".pi" / "agent" / "npm" / "package.json")
        )
    )
    findings = plugin_findings(project, host_manifest)
    if findings:
        print("# plugin gate: FAIL")
        for finding in findings:
            print(f"- {PLUGIN} {finding}")
        return 2
    print(f"# plugin gate: PASS ({PLUGIN} is neither declared, installed, nor named)")
    with tempfile.TemporaryDirectory() as scratch:
        if args.offline and not os.environ.get("TEAMWORK_LANE_CMD"):
            fake = Path(scratch) / "fake_lane.py"
            fake.write_text(FAKE, encoding="utf-8")
            os.environ["TEAMWORK_LANE_CMD"] = (
                f"{shlex.quote(sys.executable)} {shlex.quote(str(fake))} 3"
            )
        os.environ.setdefault("TEAMWORK_LANE_POLL", "0.05")
        runs = load_runs(root)
        idle = idle_agents(root, runs)
        free, rows = free_slots(root)
        cap = lane_max(root)
        lanes = min(cap, free, len(idle))
        if args.lanes:
            lanes = min(lanes, args.lanes)
        factors = " ".join(f"{name}={value}" for name, value in sorted(rows.items()))
        print(
            f"# capacity: LaneMax={cap} provider_free={factors} idle_instances={len(idle)} -> lanes={lanes}"
        )
        if lanes < 1:
            print("# no lane can start: a factor above is zero")
            return 2
        leases, dirs = slot_leases(root), agent_dirs(root)
        ids: list[str] = []
        refused = []
        for agent in idle:
            if len(ids) >= lanes:
                break
            code, run_id, text = start_lane(project, agent)
            if code == 0 and run_id:
                ids.append(run_id)
            else:
                refused.append(
                    f"{agent}: {text.strip().splitlines()[-1] if text.strip() else code}"
                )
        print(f"# started {len(ids)}/{lanes} lane(s) through `lane start`: {' '.join(ids) or '-'}")
        for line in refused:
            print(f"- refused {line}")
        if len(ids) != lanes:
            print("# FAIL the engine did not start the lanes the records say it can afford")
            return 1
        peak_records, peak_pids = wait(root, ids, args.timeout, args.poll)
        released, removed = drop_own_scratch(root, leases, dirs)
        print(f"# cleaned: released {released} slot lease(s), removed {removed} agent dir(s)")
        states = {run_id: state_of(root, {"id": run_id}) for run_id in ids}
        ok = sum(1 for state in states.values() if state == "exited")
        print(f"# peak: records={peak_records} pids={peak_pids} required={lanes}")
        print(f"# exits: {ok}/{lanes} ok ({' '.join(f'{k}={v}' for k, v in states.items())})")
        if peak_records != lanes or peak_pids != lanes or ok != lanes:
            print("# FAIL the peak concurrency or an exit did not match the capacity")
            return 1
        print(f"# PASS {lanes} lanes ran at once with no host plugin")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
