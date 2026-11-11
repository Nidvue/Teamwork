"""Unit tests for low-level I/O: atomic_write and the exclusive lock."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import pytest

from teamwork import engine, io


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


def test_two_stale_waiters_never_hold_the_lock_at_the_same_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M19 S-1: the stale steal was check-then-unlink, so both waiters entered.

    A dead owner's lock is stolen by whoever sees it first. With two waiters on
    one abandoned lock, a non-atomic steal lets the second remove the lock the
    first has just created, and both then sit in the critical section at once.
    The invariant is measured directly: every entrant appends to ``inside`` and
    the peak is asserted to be one, so two holders fail whatever the timing. The
    old shape raced eight processes and widened the window with a 50 ms sleep
    inside the staleness verdict - a wall-clock assumption that timed out on
    Windows (T-0120) - and the same seam is what the two waiters drive here.
    The second half is the case that decides it: a lock whose owner is alive is
    never stolen, so a waiter that finds it must time out with exit 4 instead of
    entering. A steal that ignores the owner enters, which is what the mutant
    test below pins.
    """
    monkeypatch.setattr(io, "LOCK_STALE_SECONDS", 0.0)
    lock_path = tmp_path / "x.lock"
    _abandoned_lock(lock_path)
    inside: list = []
    peak = [0]
    start = threading.Barrier(2)

    def waiter() -> None:
        start.wait()
        with engine.lock(lock_path, timeout=60):
            inside.append(1)
            peak[0] = max(peak[0], len(inside))
            assert len(inside) == 1, "two waiters held the lock at once"
            inside.pop()

    threads = [threading.Thread(target=waiter) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    assert [thread.is_alive() for thread in threads] == [False, False]
    assert peak[0] == 1
    assert not lock_path.exists()
    assert list(tmp_path.glob("x.lock.*")) == []

    entered: list = []
    codes: list = []

    def second_waiter() -> None:
        try:
            with engine.lock(lock_path, timeout=0.2):
                entered.append(1)
        except SystemExit as exc:
            codes.append(exc.code)

    with engine.lock(lock_path, timeout=5):
        blocked = threading.Thread(target=second_waiter)
        blocked.start()
        blocked.join(timeout=120)
        assert not blocked.is_alive()
    assert entered == [], "a waiter entered while the lock had a live owner"
    assert codes == [4]


def test_a_lock_that_ignores_the_owner_is_caught_by_the_two_waiter_invariant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mutant: a steal that never asks whether the owner is alive fails it.

    Without this the invariant above would also hold for a lock that never
    steals at all, so the assertion would not be about the owner check.
    """
    monkeypatch.setattr(io, "LOCK_STALE_SECONDS", 0.0)
    monkeypatch.setattr(io, "_lock_owner_stale", lambda _path: True)
    lock_path = tmp_path / "x.lock"
    _abandoned_lock(lock_path)
    inside: list = []
    peak = [0]
    start = threading.Barrier(2)
    held = threading.Event()
    entered = threading.Event()

    def waiter() -> None:
        start.wait()
        with engine.lock(lock_path, timeout=5):
            inside.append(1)
            peak[0] = max(peak[0], len(inside))
            if len(inside) == 1:
                held.set()
                entered.wait(timeout=5)
            else:
                entered.set()
            inside.pop()

    threads = [threading.Thread(target=waiter) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert held.is_set() and entered.is_set()
    assert peak[0] == 2, "the mutant did not produce two holders, so it proves nothing"


def test_a_release_retries_a_sharing_violation_on_its_own_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Windows sharing violation on our own lock must not orphan it.

    An orphaned lock still names a live pid, so no waiter may steal it and every
    waiter times out (CI run 43114375543: six of eight waiters exited 4).
    """
    lock_path = tmp_path / "x.lock"
    real_unlink = Path.unlink
    calls = []

    def flaky_unlink(self: Path, *args, **kwargs):
        calls.append(self)
        if len(calls) == 1:
            raise PermissionError(13, "sharing violation", str(self))
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    with engine.lock(lock_path, timeout=5):
        assert lock_path.exists()
    assert not lock_path.exists()
    assert calls


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
