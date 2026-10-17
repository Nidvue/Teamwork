"""Unit tests for the portable OS seam (teamwork.portable)."""

from __future__ import annotations

import os
import subprocess
import sys

from teamwork import portable


def test_pid_alive_current_process() -> None:
    assert portable.pid_alive(os.getpid()) is True


def test_pid_alive_rejects_nonpositive_pids() -> None:
    assert portable.pid_alive(0) is False
    assert portable.pid_alive(-5) is False


def test_pid_alive_dead_child_is_false() -> None:
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    # After wait() the process has been reaped, so its pid is gone.
    assert portable.pid_alive(child.pid) is False


def test_pid_alive_unknown_pid_is_false() -> None:
    # Far above any plausible live pid on any supported platform.
    assert portable.pid_alive(2**30) is False


def test_newline_for_is_always_lf() -> None:
    assert portable.newline_for() == "\n"
    assert portable.newline_for(False) == ""


def test_python_executable_is_nonempty() -> None:
    assert isinstance(portable.python_executable(), str)
    assert portable.python_executable()
