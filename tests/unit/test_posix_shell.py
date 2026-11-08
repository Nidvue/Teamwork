"""Unit: the Windows branch of the POSIX shell resolver must reject the WSL launcher.

Every test that executes a workflow ``run:`` block needs a real shell, and on a
Windows runner a bare ``bash`` is the System32 WSL launcher. These two cases were
carried by the deleted classifier module; the resolver now lives in
``tests/posix_shell.py`` and is still proved by mutation, not by the absence of a
``C:\\`` path on a POSIX host.

Owner: team-leader. Task: T-0001.
"""

from __future__ import annotations

import sys

import pytest
from tests.posix_shell import posix_bash


def test_posix_bash_rejects_the_wsl_launcher_on_windows() -> None:
    """The Windows branch must refuse the launcher and say what it tried.

    Both shapes are exercised: the System32 shim and the Store alias under
    ``WindowsApps``, which a plain ``startswith("C:/Windows/System32")`` guard
    would accept.
    """
    for launcher in (
        "C:\\Windows\\System32\\bash.exe",
        "C:\\Users\\runner\\AppData\\Local\\Microsoft\\WindowsApps\\bash.exe",
    ):

        def on_path(_name: str, hit: str = launcher) -> str:
            """``which`` for a host whose only bash is this launcher."""
            return hit

        with pytest.raises(AssertionError, match="no usable POSIX bash"):
            posix_bash(
                os_name="nt",
                which=on_path,
                git_shells=lambda: [],
                exists=lambda _p: True,
            )


def test_posix_bash_prefers_a_git_install_shell_on_windows() -> None:
    """A real shell derived from ``git --exec-path`` wins over the launcher.

    ``sys.executable`` stands in for the Git-for-Windows ``bash.exe``: the point
    is which candidate is chosen, and that the launcher on PATH is never it.
    """
    real = sys.executable
    launcher = "C:\\Windows\\System32\\bash.exe"

    assert (
        posix_bash(
            os_name="nt",
            which=lambda _: launcher,
            git_shells=lambda: [real],
            exists=lambda _p: True,
        )
        == real
    ), "a Git install shell must win over the launcher on PATH"

    with pytest.raises(AssertionError, match="no usable POSIX bash"):
        posix_bash(
            os_name="nt",
            which=lambda _: launcher,
            git_shells=lambda: [],
            exists=lambda _p: True,
        )
