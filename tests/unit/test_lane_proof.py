"""The lane proof measures the engine's fan-out instead of claiming it.

Why these tests exist: the operator asked how we know the team parallelises without
``pi-subagents`` and uses the maximum lane count. ``scripts/lane_proof.py`` is the answer
and it is a verifier, so the verifier itself must be proved: it must refuse a declared
plugin, compute the capacity from the records, measure a real peak, and fail a lane that
did not exit cleanly. ``TEAMWORK_LANE_CMD`` keeps every case offline.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from teamwork.config import DEFAULT_PROVIDER_LIMITS
from teamwork.portable import pid_alive

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "lane_proof.py"
CLI = REPO / "scripts" / "teamwork.py"
PROVIDER_CAPS = {name: cap for name, cap in DEFAULT_PROVIDER_LIMITS.items() if name != "default"}


def team(project: Path, agents: str, lane_max: int = 3, caps: dict | None = None) -> Path:
    project.mkdir(parents=True, exist_ok=True)
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("TEAMWORK_LANE_CMD", "TEAMWORK_ROOT")
    }
    init = subprocess.run(
        [sys.executable, str(CLI), "init", "--agents", agents, "--no-git"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(project),
    )
    assert init.returncode == 0, init.stdout + init.stderr
    teams = project / ".pi" / "Teamwork" / "Teams"
    root = sorted(path for path in teams.iterdir() if path.is_dir())[0]
    path = root / "Settings.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    data.update({"LaneMax": lane_max, "default": 32, "ollama-cloud": 64, **(caps or {})})
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return project


def launcher(tmp_path: Path, body: str, sleep: str = "2.0") -> str:
    fake = tmp_path / "fake_lane.py"
    fake.write_text(
        f"import sys, time\ntime.sleep({sleep})\n" + body,
        encoding="utf-8",
    )
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(fake))}"


def proof(project: Path, env: dict, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project", str(project), "--timeout", "60", *flags],
        capture_output=True,
        text=True,
        env={key: value for key, value in {**os.environ, **env}.items() if key != "TEAMWORK_ROOT"},
        timeout=180,
    )


def test_the_proof_measures_the_peak_concurrency_offline(tmp_path: Path) -> None:
    project = team(tmp_path / "clean", "developer-1,developer-2,tester-1")
    done = proof(project, {"TEAMWORK_LANE_CMD": launcher(tmp_path, "print('LANE-RESULT: ok')\n")})
    assert done.returncode == 0, done.stdout + done.stderr
    assert "peak: records=3 pids=3 required=3" in done.stdout
    assert "exits: 3/3 ok" in done.stdout
    assert "PASS 3 lanes ran at once" in done.stdout


def test_the_peak_probe_is_the_portable_seam_not_a_local_copy() -> None:
    spec = importlib.util.spec_from_file_location("lane_proof_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.pid_alive is pid_alive


def test_the_peak_is_the_capacity_not_the_agent_count(tmp_path: Path) -> None:
    project = team(tmp_path / "mutant", "developer-1,developer-2,developer-3", lane_max=1)
    done = proof(project, {"TEAMWORK_LANE_CMD": launcher(tmp_path, "print('LANE-RESULT: ok')\n")})
    assert done.returncode == 0, done.stdout + done.stderr
    assert "idle_instances=3 -> lanes=1" in done.stdout
    assert "peak: records=1 pids=1 required=1" in done.stdout
    assert "records=3" not in done.stdout


def test_capacity_is_capped_by_the_idle_instances(tmp_path: Path) -> None:
    project = team(tmp_path / "small", "developer-1,developer-2", lane_max=8)
    done = proof(project, {"TEAMWORK_LANE_CMD": launcher(tmp_path, "print('LANE-RESULT: ok')\n")})
    assert done.returncode == 0, done.stdout + done.stderr
    assert "idle_instances=2 -> lanes=2" in done.stdout
    assert "peak: records=2 pids=2 required=2" in done.stdout


def test_the_capacity_line_counts_the_default_bucket_and_no_other_setting(
    tmp_path: Path,
) -> None:
    project = team(tmp_path / "buckets", "developer-1,developer-2,developer-3", lane_max=8)
    done = proof(project, {"TEAMWORK_LANE_CMD": launcher(tmp_path, "print('LANE-RESULT: ok')\n")})
    assert done.returncode == 0, done.stdout + done.stderr
    factors = " ".join(
        f"{name}={cap}" for name, cap in sorted({**PROVIDER_CAPS, "default": 32}.items())
    )
    assert f"provider_free={factors} idle_instances=3 -> lanes=3" in done.stdout
    assert "provider_free=LaneMax" not in done.stdout


def test_the_proof_repeats_at_the_lane_maximum(tmp_path: Path) -> None:
    names = ",".join(f"developer-{n}" for n in range(1, 7))
    project = team(tmp_path / "atcap", names, lane_max=6, caps={"default": 6})
    env = {"TEAMWORK_LANE_CMD": launcher(tmp_path, "print('LANE-RESULT: ok')\n", sleep="5.0")}
    first = proof(project, env)
    assert first.returncode == 0, first.stdout + first.stderr
    factors = " ".join(
        f"{name}={cap}" for name, cap in sorted({**PROVIDER_CAPS, "default": 6}.items())
    )
    assert f"provider_free={factors} idle_instances=6 -> lanes=6" in first.stdout
    assert "idle_instances=6 -> lanes=6" in first.stdout
    assert "peak: records=6 pids=6 required=6" in first.stdout
    root = sorted(path for path in (project / ".pi" / "Teamwork" / "Teams").iterdir())[0]
    assert not list((root / "Runtime" / "Slots" / "default").glob("*.slot"))
    agents = sorted(path.name for path in (root / "Agents").iterdir())
    second = proof(project, env)
    assert second.returncode == 0, second.stdout + second.stderr
    capacity = [line for line in first.stdout.splitlines() if line.startswith("# capacity:")]
    assert capacity and capacity[0] in second.stdout.splitlines()
    assert "peak: records=6 pids=6 required=6" in second.stdout
    assert "PASS 6 lanes ran at once" in second.stdout
    assert sorted(path.name for path in (root / "Agents").iterdir()) == agents


def test_the_proof_repeats_on_the_same_project(tmp_path: Path) -> None:
    project = team(tmp_path / "twice", "developer-1,developer-2,developer-3")
    env = {"TEAMWORK_LANE_CMD": launcher(tmp_path, "print('LANE-RESULT: ok')\n", sleep="4.0")}
    first = proof(project, env)
    second = proof(project, env)
    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    capacity = [line for line in first.stdout.splitlines() if line.startswith("# capacity:")]
    assert capacity and capacity[0] in second.stdout.splitlines()
    assert "idle_instances=3 -> lanes=3" in second.stdout
    assert "peak: records=3 pids=3 required=3" in second.stdout
    assert "PASS 3 lanes ran at once" in second.stdout
    root = sorted(path for path in (project / ".pi" / "Teamwork" / "Teams").iterdir())[0]
    assert not list((root / "Runtime" / "Slots" / "default").glob("*.slot"))


def test_no_free_provider_slot_stops_before_any_lane_starts(tmp_path: Path) -> None:
    project = team(
        tmp_path / "noslot",
        "developer-1",
        caps={name: 0 for name in PROVIDER_CAPS} | {"default": 0},
    )
    done = proof(project, {"TEAMWORK_LANE_CMD": launcher(tmp_path, "print('LANE-RESULT: ok')\n")})
    assert done.returncode == 2, done.stdout + done.stderr
    assert "provider_free=anthropic=0" in done.stdout
    assert "# no lane can start" in done.stdout
    assert "# started" not in done.stdout


def test_a_lane_that_exits_nonzero_fails_the_proof(tmp_path: Path) -> None:
    project = team(tmp_path / "red", "developer-1,developer-2", lane_max=2)
    done = proof(
        project,
        {"TEAMWORK_LANE_CMD": launcher(tmp_path, "sys.exit(3)\n")},
    )
    assert done.returncode == 1, done.stdout + done.stderr
    assert "exits: 0/2 ok" in done.stdout


def test_a_declared_plugin_fails_before_any_lane_starts(tmp_path: Path) -> None:
    project = team(tmp_path / "plugin", "developer-1")
    manifest = tmp_path / "package.json"
    manifest.write_text('{"dependencies": {"pi-subagents": "^1.0.0"}}\n', encoding="utf-8")
    done = proof(
        project,
        {
            "TEAMWORK_PI_MANIFEST": str(manifest),
            "TEAMWORK_LANE_CMD": launcher(tmp_path, "print('LANE-RESULT: ok')\n"),
        },
    )
    assert done.returncode == 2, done.stdout + done.stderr
    assert "plugin gate: FAIL" in done.stdout
    assert "installed in" in done.stdout
    assert "# started" not in done.stdout
