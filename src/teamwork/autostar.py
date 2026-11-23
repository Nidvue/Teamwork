"""Silent, best-effort auto-star of the project repository.

Project initialization fires ``star_async`` exactly once: it returns at once and
spawns a detached worker, whether or not the host has any usable credentials.
Nothing is printed and nothing blocks the caller. The worker never probes login
state; it asks GitHub directly whether the repository is already starred and only
issues the PUT when it is not, so the GitHub-side state is the idempotency source.

The worker never creates a scratch ``HOME`` or ``XDG_CONFIG_HOME``: that would
hide stored credentials. Prompting is disabled at the environment level and no
browser flag is passed, so a failed call can never turn into an interactive login.
A timestamp marker under ``<root>/Runtime`` rate-limits repeated init calls,
mirroring ``Runtime/Starred.json`` used by the explicit ``star`` command. An
expired marker never suppresses a star: the worker still checks GitHub first.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

from .config import DIR_RUNTIME
from .io import write_lf

STAR_REPO = "Nidvue/Teamwork"
MARKER = "AutoStar.json"
SETTINGS_KEY = "AutoStar"
SETTINGS_FILE = "Settings.json"
OFF = ("0", "off", "no", "false")
TTL_SECONDS = 24 * 60 * 60
GH_TIMEOUT = 15


def _setting_enabled(root: Path) -> bool:
    """Read the team Settings.json flag; default enabled, like ``load_pulse_mode``."""
    try:
        data = json.loads((root / SETTINGS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    if not isinstance(data, dict) or SETTINGS_KEY not in data:
        return True
    raw = data[SETTINGS_KEY]
    if isinstance(raw, str):
        return raw.strip().lower() not in OFF
    return bool(raw)


def _marker_path(root: Path) -> Path:
    return root / DIR_RUNTIME / MARKER


def _fresh(root: Path) -> bool:
    try:
        data = json.loads(_marker_path(root).read_text(encoding="utf-8"))
        at = datetime.datetime.fromisoformat(data["at"])
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return (datetime.datetime.now() - at).total_seconds() < TTL_SECONDS


def _should_spawn(root: Path) -> bool:
    if (os.environ.get("TEAMWORK_STAR_ONCE") or "auto").strip().lower() in OFF:
        return False
    if os.environ.get("CI", "").strip():
        return False
    if not _setting_enabled(root):
        return False
    return not _fresh(root)


def star_async(root: Path) -> None:
    """Fire a detached worker and return immediately, never raising or printing."""
    try:
        if not _should_spawn(root):
            return
        proc = subprocess.Popen(
            [sys.executable, "-m", "teamwork.autostar", "--worker", str(root)],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=os.environ.copy(),
            cwd=str(root),
        )
        proc.returncode = 0
    except Exception:
        pass


def _gh_env() -> dict:
    env = os.environ.copy()
    env["GH_PROMPT_DISABLED"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _run(argv: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=GH_TIMEOUT,
        check=False,
        env=env,
    )


def _mark(root: Path) -> None:
    payload = {
        "repo": STAR_REPO,
        "at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    try:
        write_lf(_marker_path(root), json.dumps(payload, indent=2) + "\n")
    except OSError:
        pass


def worker(root: Path) -> None:
    """Check the star state, star only when absent, record the attempt; never print or raise."""
    env = _gh_env()
    try:
        probe = _run(["gh", "api", f"/user/starred/{STAR_REPO}"], env)
        if probe.returncode != 0:
            _run(
                [
                    "gh",
                    "api",
                    "-X",
                    "PUT",
                    "-H",
                    "Content-Length: 0",
                    f"/user/starred/{STAR_REPO}",
                ],
                env,
            )
    except Exception:
        pass
    _mark(root)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m teamwork.autostar")
    parser.add_argument("--worker")
    args = parser.parse_args(argv)
    if args.worker:
        worker(Path(args.worker))


if __name__ == "__main__":
    main()
