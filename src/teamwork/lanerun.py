"""The lane runner: one child process, one wall-clock budget, one outcome file.

A lane outlives the CLI call that starts it - an agent run is minutes long while
``teamwork lane start`` must return at once. So the lane is detached into its own
session (``start_new_session``) and the supervisor that started it can no longer
observe the exit status: the child is reparented away and ``wait`` belongs to
someone else. This module is the small process in between. It starts the real
launcher, enforces the budget, and writes the only fact the supervisor needs:

``<run>.outcome.json`` = ``{"state": ..., "exit": ..., "at": ..., "seconds": ...}``

``state`` is ``exited`` when the launcher returned on its own, ``timeout`` when the
budget killed it and ``interrupted`` when the operator did. A missing outcome file
with a dead pid is read by the supervisor as ``lost`` - a crash the wrapper could
not report. The wrapper never interprets the lane's work: whether the assignment
was finished is a fact about the board, not about an exit code.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

TERMINATE_GRACE = float(os.environ.get("TEAMWORK_LANE_GRACE", "5"))

TIMEOUT_EXIT = 124

INTERRUPTED_EXIT = 130

MISSING_BINARY_EXIT = 127


def outcome_path(run_path: Path) -> Path:
    """Where the wrapper records how the launcher ended."""
    return run_path.with_suffix(".outcome.json")


def _stamp() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def write_outcome(run_path: Path, payload: dict) -> None:
    """Write the outcome so a reader either sees all of it or none of it."""
    path = outcome_path(run_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def detach(argv: list[str], stdout, env: dict, cwd: str) -> int:
    """Start ``argv`` in its own session and return its pid, owning nothing.

    A lane outlives the CLI call by design: the wrapper writes its own outcome and
    the supervisor reaps it from the record. Setting ``returncode`` before the
    handle is dropped is what stops garbage collection from reporting a
    deliberately un-waited process as a leaked resource - the handle was never
    ours to wait on.
    """
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=env,
        cwd=cwd,
    )
    pid = proc.pid
    proc.returncode = 0
    return pid


def run(run_path: Path, timeout: float, argv: list[str]) -> int:
    """Start ``argv``, enforce ``timeout``, and return the launcher's exit code."""
    started = time.time()
    try:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL)
    except OSError as exc:
        write_outcome(
            run_path,
            {
                "state": "failed",
                "exit": MISSING_BINARY_EXIT,
                "at": _stamp(),
                "seconds": round(time.time() - started, 1),
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        print(f"teamwork lane runner: cannot start {argv[0]!r}: {exc}", file=sys.stderr)
        return MISSING_BINARY_EXIT
    state = "exited"
    try:
        code = child.wait(timeout=timeout if timeout > 0 else None)
    except subprocess.TimeoutExpired:
        state = "timeout"
        child.terminate()
        try:
            code = child.wait(timeout=TERMINATE_GRACE)
        except subprocess.TimeoutExpired:
            child.kill()
            code = child.wait()
    except KeyboardInterrupt:
        state = "interrupted"
        child.terminate()
        code = child.wait()
    write_outcome(
        run_path,
        {
            "state": state,
            "exit": code,
            "at": _stamp(),
            "seconds": round(time.time() - started, 1),
        },
    )
    if state == "timeout":
        return TIMEOUT_EXIT
    if state == "interrupted":
        return INTERRUPTED_EXIT
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="teamwork-lanerun", description=__doc__)
    parser.add_argument("--run", required=True, help="run record path")
    parser.add_argument("--timeout", type=float, default=0.0, help="seconds, 0 = none")
    parser.add_argument("launcher", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    launcher = list(args.launcher)
    if launcher and launcher[0] == "--":
        launcher = launcher[1:]
    if not launcher:
        print("teamwork lane runner: no launcher command given", file=sys.stderr)
        return 2
    return run(Path(args.run), args.timeout, launcher)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
