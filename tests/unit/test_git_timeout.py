"""Every git call is bounded: a remote that never answers must not park a lane.

Layer ``unit``, area ``git-timeout``, owner Developer (T-0009, M19-engine-audit
finding 3). ``gitutil.run_git`` is where ``refresh`` (``fetch``/``clone``),
``push`` and every other git call meets the network, and it passed no
``timeout=``: a stalled remote or an unanswerable credential prompt blocked the
lane forever, with no output and nothing for ``teamwork`` to interrupt (the audit
had to kill it from outside: ``timeout 5`` -> exit 124).

The stall is reproduced the only way it can be reproduced honestly - a loopback
listener that accepts the connection and then never answers anything, so git
waits on a socket that will not speak. It is not a network test: the peer is a
socket in this process, the port is ephemeral, and nothing leaves the machine.
"""

from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest

from teamwork import gitutil

REPO_ROOT = Path(__file__).resolve().parents[2]


class StalledRemote:
    """A listener that accepts one connection and never sends or closes.

    ``listen(5)`` runs before ``__enter__`` returns, so the port is already
    accepting when git dials it - no sleep, no retry, no readiness race. The
    accepted connection is held open by the worker until ``close``, which is
    exactly the peer a stalling remote presents.
    """

    def __init__(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(5)
        self._server.settimeout(0.2)
        self._accepted: list[socket.socket] = []
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._hold, daemon=True)
        host, port = self._server.getsockname()[:2]
        self.url = f"http://{host}:{port}/stalled.git"

    def _hold(self) -> None:
        while not self._stop.is_set():
            try:
                connection, _ = self._server.accept()
            except OSError:
                continue
            self._accepted.append(connection)
            while not self._stop.is_set():
                self._stop.wait(0.05)

    def __enter__(self) -> StalledRemote:
        self._worker.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._stop.set()
        self._worker.join(timeout=10)
        for connection in self._accepted:
            connection.close()
        self._server.close()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def fetch(repo: Path, url: str, **kwargs) -> subprocess.CompletedProcess:
    """A fetch against a stalling peer, with the caller's http proxy switched off.

    The operator's git config is not the subject of this test, and an inherited
    ``http.proxy`` would send the request somewhere that fails fast instead of
    waiting - which would make the measurement meaningless rather than wrong.
    """
    return gitutil.run_git(repo, "-c", "http.proxy=", "fetch", url, "main", **kwargs)


def test_a_remote_that_never_answers_returns_instead_of_hanging(git_repo: Path) -> None:
    """The defect itself: the call must come back, bounded, on its own.

    On the unfixed seam this raises ``TypeError`` (no ``timeout`` parameter) and,
    without the parameter at all, blocks until something outside kills it - the
    audit's ``timeout 5`` -> exit 124. The verdict is not "it took a second"; it
    is that a ``CompletedProcess`` came back at all, carrying the reason.
    """
    with StalledRemote() as remote:
        started = time.monotonic()
        result = fetch(git_repo, remote.url, timeout=1)
        elapsed = time.monotonic() - started

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == gitutil.GIT_TIMEOUT_EXIT, (result.returncode, result.stderr)
    assert elapsed < 60, f"run_git did not bound the call: {elapsed:.1f}s"


def test_the_timeout_message_is_clear_and_carries_no_url(git_repo: Path) -> None:
    """The operator reads the last line of stderr as the cause; it must say so.

    It names the verb, the limit and the way to raise it, and it names no
    argument: a remote URL carries credentials, and this text is printed and
    archived by the callers.
    """
    with StalledRemote() as remote:
        result = fetch(git_repo, remote.url, timeout=1)

    last = result.stderr.strip().splitlines()[-1]
    assert "git fetch timed out after 1s" in last
    assert gitutil.GIT_TIMEOUT_ENV in last
    assert remote.url not in result.stderr
    assert "127.0.0.1" not in result.stderr


def test_a_timed_out_call_is_a_failed_process_not_an_exception(git_repo: Path) -> None:
    """Callers keep their ``returncode != 0`` handling, so the shape is the contract.

    ``refresh`` reports ``(stderr or stdout).splitlines()[-1]``; a seam that
    raised instead would crash the command with a traceback, and one that
    returned ``None`` would crash the next line.
    """
    with StalledRemote() as remote:
        result = fetch(git_repo, remote.url, timeout=1)

    assert result.returncode != 0
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)
    assert result.args[:2] == ["git", "-C"]


class RecordingProcess:
    """Stands in for a started ``git`` so the bound it is given can be read."""

    pid = 0
    returncode = 0

    def __init__(self, seen: dict[str, object]) -> None:
        self.seen = seen

    def wait(self, timeout: float | None = None) -> int:
        self.seen["timeout"] = timeout
        return 0


def test_the_default_budget_is_applied_to_every_call(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``refresh``/``push``/``clone`` pass no argument, so the default is the fix.

    Spying on the seam is how the default is proved without a stalled peer on
    every call: drop the bound from the real invocation and this goes red even
    though the explicit-timeout tests above stay green.
    """
    seen: dict[str, object] = {}

    def spy(*args: object, **kwargs: object) -> RecordingProcess:
        return RecordingProcess(seen)

    monkeypatch.setattr(gitutil.subprocess, "Popen", spy)
    monkeypatch.setenv(gitutil.GIT_TIMEOUT_ENV, "7")

    gitutil.run_git(git_repo, "rev-parse", "--is-inside-work-tree")

    assert seen["timeout"] == 7.0


def test_an_explicit_timeout_beats_the_configured_default(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller that owns a long operation overrides the seam's default."""
    monkeypatch.setenv(gitutil.GIT_TIMEOUT_ENV, "30")
    with StalledRemote() as remote:
        result = fetch(git_repo, remote.url, timeout=1)

    assert "timed out after 1s" in result.stderr


def test_the_default_is_bounded_and_leaves_the_repository_alone() -> None:
    """The bounds: the documented default is a positive finite number."""
    assert gitutil.GIT_TIMEOUT_SECONDS > 0
    assert gitutil.GIT_TIMEOUT_SECONDS <= 3600
    assert gitutil.GIT_TIMEOUT_ENV == "TEAMWORK_GIT_TIMEOUT"


def test_the_configured_budget_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(gitutil.GIT_TIMEOUT_ENV, "30")
    assert gitutil.git_timeout() == 30.0
    monkeypatch.setenv(gitutil.GIT_TIMEOUT_ENV, "0.5")
    assert gitutil.git_timeout() == 0.5


@pytest.mark.parametrize("raw", ["", "   ", "soon", "0", "-5", "inf", "nan"])
def test_an_unusable_setting_falls_back_instead_of_failing_the_command(
    raw: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A typo in a local variable must not make every command unrunnable.

    The value is read per call, not at import, so it cannot take the whole
    entry point down the way an import-time ``int()`` would.
    """
    monkeypatch.setenv(gitutil.GIT_TIMEOUT_ENV, raw)
    assert gitutil.git_timeout() == gitutil.GIT_TIMEOUT_SECONDS


def test_a_healthy_call_is_unchanged(git_repo: Path) -> None:
    """The fix is a bound, not a policy: normal calls keep git's own result."""
    inside = gitutil.run_git(git_repo, "rev-parse", "--is-inside-work-tree")
    assert inside.returncode == 0
    assert inside.stdout.strip() == "true"
    assert "timed out" not in inside.stderr

    missing = gitutil.run_git(git_repo, "rev-parse", "--verify", "--quiet", "refs/heads/nope")
    assert missing.returncode != 0
    assert "timed out" not in missing.stderr


FAKE_GIT = """#!/bin/sh
sleep 60 &
echo $! > "$FAKE_GIT_GRANDCHILD"
sleep 60
"""


@pytest.mark.skipif(os.name == "nt", reason="the shim is a POSIX shell script")
def test_a_helper_that_outlives_the_leader_cannot_park_the_call(
    git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bound must not depend on the direct child being the only writer.

    ``subprocess.run(..., timeout=...)`` kills the leader and then, on Windows,
    waits on ``communicate()`` again; a helper that inherited the pipe keeps it
    open and the call never returns - the 43-minute CI hang. This shim is that
    shape: a leader that starts a grandchild holding the same output and then
    waits itself. The call has to come back, and the grandchild has to be gone
    with it, so no orphan is left writing to a lane's terminal.
    """
    shim = tmp_path / "shim"
    shim.mkdir()
    fake = shim / "git"
    fake.write_text(FAKE_GIT, encoding="utf-8")
    fake.chmod(0o755)
    grandchild = tmp_path / "grandchild.pid"
    monkeypatch.setenv("PATH", f"{shim}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GIT_GRANDCHILD", str(grandchild))

    started = time.monotonic()
    result = gitutil.run_git(git_repo, "fetch", "origin", timeout=1)
    elapsed = time.monotonic() - started

    assert result.returncode == gitutil.GIT_TIMEOUT_EXIT, result.stderr
    assert elapsed < 30, f"run_git waited on the helper: {elapsed:.1f}s"
    pid = int(grandchild.read_text(encoding="utf-8").strip())
    for _ in range(100):
        if not _alive(pid):
            break
        time.sleep(0.05)
    assert not _alive(pid), f"the helper outlived the bound: pid {pid}"


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_a_timed_out_call_leaves_the_repository_usable(git_repo: Path) -> None:
    """The bound must end the call, not wedge the repository behind it.

    ``git fetch`` execs a remote helper; the killed parent's stdin EOF ends it,
    so the next git call on the same repository is unaffected - the second call
    is also the proof that the seam still works after a timeout.
    """
    with StalledRemote() as remote:
        timed_out = fetch(git_repo, remote.url, timeout=1)
        after = gitutil.run_git(git_repo, "status", "--porcelain", timeout=10)

    assert timed_out.returncode == gitutil.GIT_TIMEOUT_EXIT
    assert after.returncode == 0, after.stderr
