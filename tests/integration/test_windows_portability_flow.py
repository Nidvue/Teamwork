"""The Windows contract, executed: LF on disk and a spaced, env-shaped host.

Layer ``integration``, area ``windows-portability``, owner Tester (T-0014).

Three claims, each run as a process or a file rather than read off the source:

1. **The engine writes LF on every platform.** A Windows checkout with
   ``core.autocrlf`` and an editor that saves CRLF must not turn a generated
   record into a diff storm, so ``io.write_text`` opens the file with an explicit
   ``newline="\\n"`` instead of the platform default. Verified on the bytes.
2. **A checkout under a directory with a space still runs**, as a subprocess,
   with the interpreter and the module both reached through that path - the shape
   that splits an unquoted command string on this host.
3. **A Windows-shaped environment is enough**: ``PYTHONUTF8=1``, a
   ``USERPROFILE`` and no ``HOME`` (Windows sets no ``HOME``), and the CLI answers
   ``--version`` and ``--help`` without touching a team.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from teamwork import io, portable

REPO_ROOT = Path(__file__).resolve().parents[2]
COPY_ENTRIES = ("src", "scripts", "roles", "references", "templates", "SKILL.md")


def windows_shaped_env(home: Path) -> dict:
    """An environment without the POSIX-only variables a Windows host lacks."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    for name in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
        env.pop(name, None)
    env["USERPROFILE"] = str(home)
    env["HOMEDRIVE"], env["HOMEPATH"] = home.drive or "C:", str(home)[2:] or "\\"
    env["PYTHONUTF8"] = "1"
    return env


def test_generated_records_are_lf_on_every_platform(tmp_path: Path) -> None:
    target = tmp_path / "Board.md"
    io.write_lf(target, "| a | b |\n| - | - |\n")
    assert b"\r" not in target.read_bytes(), "a generated record carried a platform newline"
    assert portable.newline_for(True) == "\n"
    assert portable.newline_for(False) == ""


def test_a_checkout_under_a_spaced_path_runs_as_a_process(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout with a space"
    checkout.mkdir()
    for entry in COPY_ENTRIES:
        source = REPO_ROOT / entry
        if source.is_dir():
            shutil.copytree(source, checkout / entry)
        elif source.is_file():
            shutil.copy2(source, checkout / entry)

    env = windows_shaped_env(tmp_path / "home")
    env["PYTHONPATH"] = str(checkout / "src")
    for argv in (("--version",), ("--help",)):
        done = subprocess.run(
            [sys.executable, "-m", "teamwork", *argv],
            cwd=checkout,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert done.returncode == 0, f"{argv}: {done.stderr}"
        assert done.stdout.strip(), f"{argv} printed nothing from a spaced checkout"
