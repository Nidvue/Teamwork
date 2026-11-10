"""Atomic file IO, the exclusive lock and the one error exit."""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from .portable import newline_for, pid_alive

if TYPE_CHECKING:  # pragma: no cover
    from typing import NoReturn


LOCK_TIMEOUT = float(os.environ.get("TEAMWORK_LOCK_TIMEOUT", "60"))

LOCK_STALE_SECONDS = float(os.environ.get("TEAMWORK_LOCK_STALE_SECONDS", "300"))


def _lock_owner_stale(path: Path) -> bool:
    """True only when the lock is clearly abandoned: old AND its owner is gone."""
    try:
        age = time.time() - path.stat().st_mtime
        body = path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    if age < LOCK_STALE_SECONDS:
        return False
    pid = int(body.split(".", 1)[0]) if body.split(".", 1)[0].isdigit() else 0
    if pid <= 0:
        return True
    # Portable liveness probe: on Windows os.kill(pid, 0) is not a probe, so
    # this goes through the audited helper in teamwork.portable.
    return not pid_alive(pid)


@contextlib.contextmanager
def lock(path: Path, timeout: float | None = None):
    """Exclusive lock via O_CREAT|O_EXCL. Never steals a live lock, and only
    removes the lock file if this process owns it."""
    if timeout is None:
        timeout = LOCK_TIMEOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}.{time.time():.6f}"
    deadline = time.monotonic() + max(timeout, 0.0)
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, token.encode())
            os.close(fd)
            break
        except FileExistsError:
            if _lock_owner_stale(path):
                try:
                    os.unlink(str(path))
                    continue
                except OSError:
                    pass
            if time.monotonic() > deadline:
                die(
                    f"timed out after {int(timeout)}s waiting for {path.name}. "
                    "Another agent holds it. Wait, or clear it only if the owner "
                    "is gone. Never delete a lock that is still in use.",
                    4,
                )
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            if path.read_text(encoding="utf-8").strip() == token:
                path.unlink()
        except OSError:
            pass


def atomic_write(path: Path, text: str) -> None:
    """Write via a unique temp file in the same directory, then rename.

    Windows rejects ``os.replace`` while another process has the target open, so
    the rename is retried briefly. The original mode is preserved because
    ``mkstemp`` creates a 0600 file, which would otherwise make a previously
    group-readable workspace file private after the first rewrite.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            mode = path.stat().st_mode & 0o777
        except OSError:
            mode = 0o644
    else:
        # Respect the caller's umask instead of forcing a world-readable file.
        current_umask = os.umask(0)
        os.umask(current_umask)
        mode = 0o666 & ~current_umask
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline_for()) as fh:
            fh.write(text)
        try:
            os.chmod(tmp, mode)
        except OSError:
            pass
        for attempt in range(5):
            try:
                os.replace(tmp, str(path))
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
            except OSError:
                # Windows file-sharing violations are not always PermissionError.
                if os.name != "nt" or attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_lf(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write ``text`` with LF newlines on every platform and every Python >= 3.9.

    ``Path.write_text(..., newline=...)`` only exists from Python 3.10, and this
    package supports 3.9 (CI runs the matrix on 3.9), so the file is opened here
    directly. On Windows the default text mode would translate ``\n`` to CRLF and
    a clone would no longer be byte-identical across platforms.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="\n") as handle:
        handle.write(text)


def die(msg: str, code: int = 1) -> NoReturn:
    print(f"teamwork: {msg}", file=sys.stderr)
    raise SystemExit(code)
