"""Unit tests for low-level I/O: atomic_write and the exclusive lock."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from teamwork import engine, io

HOLDER_SCRIPT = """
import os, pathlib, sys, time
sys.path.insert(0, {src!r})
from teamwork import engine, io

real_pid_alive = io.pid_alive


def preempted_pid_alive(pid):
    alive = real_pid_alive(pid)
    time.sleep(0.05)
    return alive


io.pid_alive = preempted_pid_alive
lock_path = pathlib.Path({lock!r})
holder = pathlib.Path({holder!r})
overlap = pathlib.Path({overlap!r})
barrier = pathlib.Path({barrier!r})
while not barrier.exists():
    time.sleep(0.001)
for _ in range({iterations}):
    with engine.lock(lock_path, timeout=120):
        try:
            fd = os.open(str(holder), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            with open(overlap, "a", encoding="utf-8") as stream:
                stream.write(f"{{os.getpid()}} held the lock while another waiter held it\\n")
            continue
        try:
            os.close(fd)
            time.sleep({hold})
        finally:
            os.unlink(str(holder))
"""


def _dead_pid() -> int:
    for _ in range(5):
        process = subprocess.Popen([sys.executable, "-c", "pass"])
        process.wait()
        assert process.returncode == 0
        if not io.pid_alive(process.pid):
            return process.pid
    raise AssertionError("no reaped pid stayed dead")


def _abandoned_lock(path: Path, body: str = "0.0") -> None:
    path.write_text(body, encoding="utf-8")
    old = 1.0
    os.utime(path, (old, old))


def test_atomic_write_is_byte_identical(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"
    engine.atomic_write(path, "line1\nline2\n")
    assert path.read_bytes() == b"line1\nline2\n"


def test_atomic_write_keeps_utf8_bytes(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"
    engine.atomic_write(path, "café\n")
    assert path.read_bytes() == "café\n".encode()


def test_atomic_write_leaves_no_temp_behind(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"
    engine.atomic_write(path, "hello")
    assert list(tmp_path.glob("out.txt.*")) == []


def test_atomic_write_overwrites_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"
    engine.atomic_write(path, "one")
    engine.atomic_write(path, "two")
    assert path.read_text(encoding="utf-8") == "two"
    assert list(tmp_path.glob("out.txt.*")) == []


def test_atomic_write_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "out.txt"
    engine.atomic_write(path, "nested")
    assert path.read_text(encoding="utf-8") == "nested"


def test_atomic_write_never_writes_through_to_target_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "out.txt"
    engine.atomic_write(path, "original")

    def boom(*_args, **_kwargs):
        raise RuntimeError("replace failed")

    monkeypatch.setattr(engine.os, "replace", boom)
    with pytest.raises(RuntimeError):
        engine.atomic_write(path, "new content")

    assert path.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.glob("out.txt.*")) == []


def test_lock_is_exclusive_and_removed_on_exit(tmp_path: Path) -> None:
    lock_path = tmp_path / "x.lock"
    with engine.lock(lock_path):
        assert lock_path.exists()
    assert not lock_path.exists()


def test_lock_can_be_reacquired_after_release(tmp_path: Path) -> None:
    lock_path = tmp_path / "x.lock"
    with engine.lock(lock_path):
        pass
    with engine.lock(lock_path):
        assert lock_path.exists()


def test_lock_contention_times_out_with_code_4(tmp_path: Path) -> None:
    lock_path = tmp_path / "x.lock"
    with engine.lock(lock_path):
        with pytest.raises(SystemExit) as excinfo:
            with engine.lock(lock_path, timeout=0.15):
                pass
    assert excinfo.value.code == 4


def test_lock_does_not_steal_a_live_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock_path = tmp_path / "x.lock"
    lock_path.write_text(f"{os.getpid()}.0", encoding="utf-8")
    old = 1.0
    os.utime(lock_path, (old, old))
    monkeypatch.setattr(io, "LOCK_STALE_SECONDS", 0.0)

    with pytest.raises(SystemExit) as excinfo:
        with engine.lock(lock_path, timeout=0.1):
            pass
    assert excinfo.value.code == 4


def test_lock_reclaims_a_stale_dead_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock_path = tmp_path / "x.lock"
    lock_path.write_text("424242.0", encoding="utf-8")
    old = 1.0
    os.utime(lock_path, (old, old))
    monkeypatch.setattr(io, "LOCK_STALE_SECONDS", 0.0)
    monkeypatch.setattr(io, "pid_alive", lambda pid: False)

    with engine.lock(lock_path, timeout=0.2):
        assert lock_path.exists()
    assert not lock_path.exists()


def test_lock_owner_stale_ignores_a_fresh_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / "x.lock"
    lock_path.write_text("424242.0", encoding="utf-8")
    monkeypatch.setattr(io, "LOCK_STALE_SECONDS", 10_000.0)
    assert io._lock_owner_stale(lock_path) is False


def test_lock_owner_stale_treats_unreadable_lock_as_not_stale(tmp_path: Path) -> None:
    missing = tmp_path / "no.lock"
    assert io._lock_owner_stale(missing) is False


def test_two_stale_waiters_never_hold_the_lock_at_the_same_time(tmp_path: Path) -> None:
    """M19 S-1: the stale steal was check-then-unlink, so both waiters entered.

    A dead owner's lock is stolen by whoever sees it first. With eight processes
    starting together on one abandoned lock, a non-atomic steal lets the second
    waiter remove the lock the first one has just created, and the two then sit in
    the critical section at once (400 ms overlap in the audit). The window between
    the verdict and the unlink is a few microseconds, so each waiter is preempted
    for 50 ms inside it - the audit's own probe, applied to both revisions. The
    detector is an independent marker file: the process inside the lock creates it
    exclusively, so a second holder cannot create it and has to record the
    overlap.
    """
    lock_path = tmp_path / "x.lock"
    holder = tmp_path / "holder"
    overlap = tmp_path / "overlap.log"
    barrier = tmp_path / "go"
    dead_pid = _dead_pid()
    _abandoned_lock(lock_path, f"{dead_pid}.0")
    script = HOLDER_SCRIPT.format(
        src=str(Path(engine.__file__).resolve().parents[1]),
        lock=str(lock_path),
        holder=str(holder),
        overlap=str(overlap),
        barrier=str(barrier),
        iterations=3,
        hold=0.03,
    )
    env = dict(os.environ, TEAMWORK_LOCK_STALE_SECONDS="0", TEAMWORK_LOCK_TIMEOUT="120")
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(8)
    ]
    barrier.write_text("go", encoding="utf-8")
    results = [process.communicate(timeout=300) for process in processes]
    codes = [process.returncode for process in processes]
    seen = overlap.read_text(encoding="utf-8") if overlap.exists() else ""
    assert seen == "", (seen, codes, results)
    assert codes == [0] * len(processes), (codes, results)
    assert not lock_path.exists()
    assert list(tmp_path.glob("x.lock.*")) == []


def test_a_stale_steal_is_claimed_by_one_waiter_at_a_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The unlink may only run under the claim, so exactly one waiter gets it."""
    lock_path = tmp_path / "x.lock"
    _abandoned_lock(lock_path)
    monkeypatch.setattr(io, "LOCK_STALE_SECONDS", 0.0)
    body = io._read_lock_body(lock_path)
    assert body == "0.0"
    assert io._lock_owner_stale(lock_path) is True

    first = io._claim_stale_steal(lock_path, body)
    assert first is not None
    assert io._claim_stale_steal(lock_path, body) is None

    first.unlink()
    second = io._claim_stale_steal(lock_path, body)
    assert second is not None
    second.unlink()


def test_a_steal_claim_held_by_a_live_waiter_is_not_taken_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / "x.lock"
    _abandoned_lock(lock_path)
    monkeypatch.setattr(io, "LOCK_STALE_SECONDS", 0.0)
    claim = io._steal_claim_path(lock_path, "0.0")
    claim.write_text(f"{os.getpid()}.0", encoding="utf-8")
    old = 1.0
    os.utime(claim, (old, old))

    assert io._claim_stale_steal(lock_path, "0.0") is None
    assert claim.exists()


def test_a_steal_claim_abandoned_by_a_dead_waiter_is_taken_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / "x.lock"
    _abandoned_lock(lock_path)
    monkeypatch.setattr(io, "LOCK_STALE_SECONDS", 0.0)
    claim = io._steal_claim_path(lock_path, "0.0")
    claim.write_text("0.0", encoding="utf-8")
    old = 1.0
    os.utime(claim, (old, old))

    taken = io._claim_stale_steal(lock_path, "0.0")
    assert taken == claim
    assert claim.exists()
    assert list(tmp_path.glob("x.lock.steal-*.gone-*")) == []


def test_a_stale_steal_leaves_a_replaced_lock_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The steal is a compare-and-swap: a lock that changed body is not removed."""
    lock_path = tmp_path / "x.lock"
    _abandoned_lock(lock_path)
    monkeypatch.setattr(io, "LOCK_STALE_SECONDS", 0.0)
    replacement = f"{os.getpid()}.0"
    real_claim = io._claim_stale_steal

    def claim_then_replace(path: Path, body: str) -> Path | None:
        claim = real_claim(path, body)
        if claim is not None:
            path.write_text(replacement, encoding="utf-8")
        return claim

    monkeypatch.setattr(io, "_claim_stale_steal", claim_then_replace)

    assert io._steal_stale(lock_path) is False
    assert lock_path.read_text(encoding="utf-8") == replacement
    assert list(tmp_path.glob("x.lock.steal-*")) == []


def test_lock_survives_a_permission_error_while_the_owner_removes_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Windows race: the open() itself raises EACCES and the file then vanishes.

    Run 41935895596 job 126945114504 failed eight concurrent `lesson add`
    processes with `teamwork: PermissionError: [Errno 13] Permission denied:
    '...lessons.lock'`. The OS reports a sharing violation on `open`, not
    `FileExistsError`, so a waiter that only retried the latter aborted a command
    whose lock was about to be free. Acquisition has to treat it as busy.
    """
    lock_path = tmp_path / "x.lock"
    lock_path.write_text(f"{os.getpid()}.0", encoding="utf-8")
    real_open = os.open
    attempts = {"n": 0}

    def racing_open(path, flags, *args, **kwargs):
        if str(path) == str(lock_path) and attempts["n"] == 0:
            attempts["n"] += 1
            os.unlink(str(lock_path))
            raise PermissionError(13, "Permission denied", str(path))
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", racing_open)
    with engine.lock(lock_path, timeout=5):
        assert attempts["n"] == 1, "the probe never reproduced the PermissionError"
        assert lock_path.read_text(encoding="utf-8").startswith(f"{os.getpid()}.")


def test_a_permission_error_that_never_clears_is_a_busy_timeout_not_a_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bounded, and still the lock's own verdict: exit 4, never an uncaught OSError."""
    lock_path = tmp_path / "x.lock"
    lock_path.write_text(f"{os.getpid()}.0", encoding="utf-8")
    real_open = os.open

    def denying_open(path, flags, *args, **kwargs):
        if str(path) == str(lock_path):
            raise PermissionError(13, "Permission denied", str(path))
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", denying_open)
    with pytest.raises(SystemExit) as excinfo:
        with engine.lock(lock_path, timeout=0.2):
            pass
    assert excinfo.value.code == 4
