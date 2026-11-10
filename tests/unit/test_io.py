"""Unit tests for low-level I/O: atomic_write and the exclusive lock."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from teamwork import engine

# --------------------------------------------------------------------------- #
# atomic_write
# --------------------------------------------------------------------------- #


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

    # The original file is untouched and the temp file was cleaned up.
    assert path.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.glob("out.txt.*")) == []


# --------------------------------------------------------------------------- #
# lock
# --------------------------------------------------------------------------- #


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
    monkeypatch.setattr(engine, "LOCK_STALE_SECONDS", 0.0)

    with pytest.raises(SystemExit) as excinfo:
        with engine.lock(lock_path, timeout=0.1):
            pass
    assert excinfo.value.code == 4


def test_lock_reclaims_a_stale_dead_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock_path = tmp_path / "x.lock"
    lock_path.write_text("424242.0", encoding="utf-8")
    old = 1.0
    os.utime(lock_path, (old, old))
    monkeypatch.setattr(engine, "LOCK_STALE_SECONDS", 0.0)
    monkeypatch.setattr(engine, "pid_alive", lambda pid: False)

    with engine.lock(lock_path, timeout=0.2):
        assert lock_path.exists()
    assert not lock_path.exists()


def test_lock_owner_stale_ignores_a_fresh_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / "x.lock"
    lock_path.write_text("424242.0", encoding="utf-8")
    monkeypatch.setattr(engine, "LOCK_STALE_SECONDS", 10_000.0)
    assert engine._lock_owner_stale(lock_path) is False


def test_lock_owner_stale_treats_unreadable_lock_as_not_stale(tmp_path: Path) -> None:
    missing = tmp_path / "no.lock"
    assert engine._lock_owner_stale(missing) is False
