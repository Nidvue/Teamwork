"""Resolve a real POSIX ``bash`` for the tests that execute a workflow run block.

A bare ``bash`` on a Windows runner is the System32 WSL launcher, not a shell, so
every candidate is checked and the launcher is never accepted. Each seam is
injectable so the Windows branch is testable on any host.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

WSL_LAUNCHER_DIRS = ("c:/windows/system32",)
WSL_LAUNCHER_SUFFIXES = ("/windowsapps/bash.exe",)


def normalised(path: str) -> str:
    """Lower-case, forward-slash form so Windows paths compare reliably."""
    return path.replace("\\", "/").rstrip("/").lower()


def is_wsl_launcher(path: str) -> bool:
    """True for a ``bash.exe`` that is the WSL launcher rather than a shell.

    Covers the System32 shim and the Store alias under ``WindowsApps``, in both
    the given form and the form ``Path.resolve()`` reports, so a shim that is a
    link into ``WindowsApps`` cannot slip through.
    """
    forms = {normalised(path)}
    try:
        forms.add(normalised(str(Path(path).resolve())))
    except OSError:
        pass
    for form in forms:
        if any(form.startswith(directory + "/") for directory in WSL_LAUNCHER_DIRS):
            return True
        if form.endswith(WSL_LAUNCHER_SUFFIXES):
            return True
    return False


def git_install_bash() -> list[str]:
    """Real Git-for-Windows shells derived from ``git --exec-path``.

    On Windows ``git --exec-path`` returns e.g.
    ``C:/Program Files/Git/mingw64/libexec/git-core``. Walking up from that
    directory to the install root gives ``C:/Program Files/Git``, whose
    ``bin/bash.exe`` and ``usr/bin/bash.exe`` are genuine POSIX shells.
    """
    result = subprocess.run(["git", "--exec-path"], capture_output=True, text=True, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    exec_path = Path(result.stdout.strip())
    candidates: list[str] = []
    for root in list(exec_path.parents)[:4]:
        candidates.append(str(root / "bin" / "bash.exe"))
        candidates.append(str(root / "usr" / "bin" / "bash.exe"))
    return candidates


def posix_bash(
    os_name: str | None = None,
    which: Callable[[str], str | None] | None = None,
    git_shells: Callable[[], list[str]] | None = None,
    exists: Callable[[str], bool] | None = None,
) -> str:
    """Return the path of a real POSIX ``bash`` to run a workflow block with.

    On POSIX this is simply ``shutil.which("bash")``. On Windows a bare
    ``"bash"`` is resolved by the OS to ``C:\\Windows\\System32\\bash.exe``, the
    WSL launcher - not a shell - so it is never accepted: Git-for-Windows
    ``bash.exe`` candidates are derived from ``git --exec-path`` and the PATH
    lookup is only used when it does not land on the WSL launcher.

    Every seam (``os_name``, ``which``, ``git_shells``, ``exists``) is injectable
    so the Windows branch is testable on any host, including the rejection path:
    a test that let the real filesystem answer ``exists`` would pass merely
    because a ``C:\\...`` path is absent on POSIX, proving nothing about the
    guard. Raises ``AssertionError`` naming everything tried when no usable
    shell exists, rather than silently running the WSL launcher.
    """
    name = os.name if os_name is None else os_name
    lookup: Callable[[str], str | None] = shutil.which if which is None else which
    if name != "nt":
        bash = lookup("bash")
        if bash is None:
            raise AssertionError(f"no bash on PATH (which bash -> None, os.name={name})")
        return bash

    present: Callable[[str], bool] = (lambda p: Path(p).exists()) if exists is None else exists
    tried: list[str] = []
    on_path = lookup("bash")
    tried.append(f"which bash -> {on_path!r}")
    git_candidates = (git_install_bash if git_shells is None else git_shells)()
    tried.extend(f"git --exec-path -> {c!r}" for c in git_candidates)

    for candidate in [*git_candidates, on_path]:
        if candidate and not is_wsl_launcher(candidate) and present(candidate):
            return candidate
    raise AssertionError(
        "no usable POSIX bash found on Windows - the candidates were the WSL "
        "launcher or absent, neither of which can run the classifier. "
        "Tried: " + "; ".join(tried)
    )


def posix_bash_or_skip() -> str:
    """The shell, or a skip that names ``bash`` and says what was tried."""
    from tests.tooling import skip_message

    try:
        return posix_bash()
    except AssertionError as absent:
        import pytest

        pytest.skip(skip_message("bash", str(absent)))
        raise
