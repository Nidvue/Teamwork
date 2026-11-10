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

STEAL_CLAIM_ATTEMPTS = 3


def _read_lock_body(path: Path) -> str | None:
    """Return the trimmed body of a lock file, or ``None`` when it cannot be read."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _lock_owner_stale(path: Path) -> bool:
    """True only when the lock is clearly abandoned: old AND its owner is gone."""
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return False
    body = _read_lock_body(path)
    if body is None or age < LOCK_STALE_SECONDS:
        return False
    head = body.split(".", 1)[0]
    pid = int(head) if head.isdigit() else 0
    if pid <= 0:
        return True
    return not pid_alive(pid)


def _steal_claim_path(path: Path, body: str) -> Path:
    """Name of the claim file that serialises the thieves of one lock body."""
    key = "".join(char if char.isalnum() or char in ".-" else "_" for char in body)
    return path.with_name(f"{path.name}.steal-{key[:80] or 'empty'}")


def _claim_stale_steal(path: Path, body: str) -> Path | None:
    """Take the right to remove the abandoned lock whose body is ``body``.

    ``os.unlink`` cannot be conditioned on the file it removes, so two waiters
    that judged the same lock abandoned both removed it, and the second one deleted
    the live lock the first had just created: both then ran inside the critical
    section (M19 S-1, 400 ms of overlap). The claim file is created with
    ``O_EXCL`` and named after the body that was judged, so exactly one waiter can
    hold it for that body; the lock name cannot be recreated while it still
    exists, and therefore the claim holder is the only process that removes it. A
    claim left behind by a killed waiter is taken over by an atomic rename under
    the same staleness rule the lock itself uses.
    """
    claim = _steal_claim_path(path, body)
    for _ in range(STEAL_CLAIM_ATTEMPTS):
        try:
            fd = os.open(str(claim), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if not _lock_owner_stale(claim):
                return None
            abandoned = claim.with_name(f"{claim.name}.gone-{os.getpid()}-{time.time_ns()}")
            try:
                os.rename(str(claim), str(abandoned))
            except OSError:
                return None
            with contextlib.suppress(OSError):
                os.unlink(str(abandoned))
            continue
        except OSError:
            return None
        try:
            with contextlib.suppress(OSError):
                os.write(fd, f"{os.getpid()}.{time.time():.6f}".encode())
        finally:
            os.close(fd)
        return claim
    return None


def _steal_stale(path: Path) -> bool:
    """Remove the abandoned lock at ``path``; report whether it was removed.

    Both halves of the old check-then-act window are closed: the claim serialises
    the waiters that judged the same body, and the body is re-read while the claim
    is held, so a waiter that lost the race cannot unlink the lock that has
    already replaced the abandoned one.
    """
    body = _read_lock_body(path)
    if body is None or not _lock_owner_stale(path):
        return False
    claim = _claim_stale_steal(path, body)
    if claim is None:
        return False
    try:
        if _read_lock_body(path) != body:
            return False
        try:
            os.unlink(str(path))
        except OSError:
            return False
        return True
    finally:
        with contextlib.suppress(OSError):
            os.unlink(str(claim))


@contextlib.contextmanager
def lock(path: Path, timeout: float | None = None):
    """Exclusive lock via O_CREAT|O_EXCL. Never steals a live lock, and only
    removes the lock file if this process owns it.

    The abandoned-lock steal is atomic in two steps: a claim file names the body
    that was judged stale so exactly one waiter may remove it, and the body is
    re-read under that claim so a lock that replaced the stale one is left alone.

    A Windows waiter can see ``PermissionError`` instead of ``FileExistsError``
    while another process creates, replaces or removes the file: the sharing
    violation and the lost race carry the same errno as a locked file, and the
    OS reports it on the ``open`` itself. It is the busy state, so it retries
    inside the same timeout budget and never aborts the command - a lock that
    was never acquired is still reported as a timeout with exit 4, not as a
    crash.
    """
    if timeout is None:
        timeout = LOCK_TIMEOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}.{time.time():.6f}"
    deadline = time.monotonic() + max(timeout, 0.0)
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if _steal_stale(path):
                continue
        except PermissionError:
            pass
        else:
            os.write(fd, token.encode())
            os.close(fd)
            break
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
    """Write ``text`` with LF newlines and UTF-8 on every supported platform.

    ``Path.write_text(..., newline=...)`` would work on the 3.11 floor, but the
    helper opens the file explicitly so the encoding, the newline and the atomic
    write path are stated in one place. On Windows the default text mode would
    translate ``\n`` to CRLF and a clone would no longer be byte-identical.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="\n") as handle:
        handle.write(text)


def die(msg: str, code: int = 1) -> NoReturn:
    print(f"teamwork: {msg}", file=sys.stderr)
    raise SystemExit(code)
