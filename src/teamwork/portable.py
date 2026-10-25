"""Operating-system portability helpers.

Teamwork runs on Linux, macOS and Windows. Anything that behaves differently on
those platforms lives here so it can be unit-tested in isolation and audited as a
single seam (see ``tests/unit/test_portability.py``).
"""

from __future__ import annotations

import os
import sys

IS_WINDOWS = os.name == "nt"
IS_POSIX = os.name == "posix"


def pid_alive(pid: int) -> bool:
    """Return ``True`` only when process ``pid`` is still running.

    Never signals or kills the process; this is a read-only liveness probe used
    to decide whether a stale lock file may be reclaimed.

    * POSIX: ``os.kill(pid, 0)`` is the standard probe.
    * Windows: ``os.kill`` with signal ``0`` is not a portable probe, so the
      process list is queried instead. If it cannot be queried, assume the
      process is alive - refusing to steal a live lock is always the safe
      default.
    """
    if pid <= 0:
        return False
    if IS_WINDOWS:
        return _windows_pid_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists but belongs to another user.
        return True
    except OSError:
        return True
    return True


def _windows_pid_alive(pid: int) -> bool:  # pragma: no cover - Windows only
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return True
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    # ``ctypes.windll`` exists only on Windows, so the attribute access is untyped on
    # every other OS: a ``type: ignore`` here would be reported as *unused* off
    # Windows and keep the typing gate permanently red. ``getattr`` yields ``Any``,
    # which is the honest type for a platform-only attribute; B009 prefers a plain
    # attribute access, which is exactly the form that cannot be typed.
    kernel32 = getattr(ctypes, "windll").kernel32  # noqa: B009 - Windows-only attribute
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # Access denied means the process exists but is protected.
        return kernel32.GetLastError() == 5
    try:
        code = wintypes.DWORD()
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return code.value == STILL_ACTIVE
        return True
    finally:
        kernel32.CloseHandle(handle)


def newline_for(text_mode: bool = True) -> str:
    """The newline convention Teamwork writes.

    Generated markdown and JSON must be byte-identical on every platform, so the
    engine always writes ``\\n`` explicitly instead of relying on the platform
    default (which is ``\\r\\n`` on Windows).
    """
    return "\n" if text_mode else ""


def python_executable() -> str:
    """Absolute path to the interpreter running us (safe to embed in docs)."""
    return sys.executable or "python3"
