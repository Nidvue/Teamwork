"""The git budget, driven through the command that meets the network.

Layer ``integration``, area ``git-timeout``, owner Tester (T-0013). The unit
layer proves ``gitutil.run_git`` bounds one call; this layer proves the *command*
a lane actually runs is bounded too - ``teamwork refresh --repo <url>`` clones a
mirror checkout, so a remote that accepts the connection and then says nothing
must end the command with a named failure instead of parking the process, and
the budget must not break a healthy clone.

The peer is a loopback listener in this process: no network leaves the host.
"""

from __future__ import annotations

import socket
import subprocess
import threading
import time
from pathlib import Path

from teamwork import bundle

GIT_ENV = ("-c", "user.name=Tester", "-c", "user.email=tester@agents.nidvue.com")


class StalledRemote:
    """A listener that accepts the connection and never answers or closes."""

    def __init__(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(5)
        self._server.settimeout(0.2)
        self._held: list[socket.socket] = []
        self._stop = threading.Event()
        host, port = self._server.getsockname()[:2]
        self.url = f"http://{host}:{port}/stalled.git"
        self._worker = threading.Thread(target=self._hold, daemon=True)
        self._worker.start()

    def _hold(self) -> None:
        while not self._stop.is_set():
            try:
                connection, _ = self._server.accept()
            except OSError:
                continue
            self._held.append(connection)
            while not self._stop.is_set():
                time.sleep(0.05)

    def close(self) -> None:
        self._stop.set()
        for connection in self._held:
            connection.close()
        self._server.close()
        self._worker.join(timeout=2)


def seed_remote(path: Path) -> Path:
    """A local repository shaped like a skill checkout, on branch ``main``."""
    (path / "src" / "teamwork").mkdir(parents=True)
    (path / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    (path / "src" / "teamwork" / "__init__.py").write_text("", encoding="utf-8")
    for argv in (("init", "-q", "-b", "main"), ("add", "-A"), (*GIT_ENV, "commit", "-qm", "seed")):
        done = subprocess.run(["git", *argv], cwd=path, check=False, capture_output=True, text=True)
        assert done.returncode == 0, f"git {argv}: {done.stderr}"
    return path


def test_refresh_on_a_stalled_remote_ends_with_a_named_failure(
    cli, project: Path, capsys, monkeypatch
) -> None:
    monkeypatch.setenv("TEAMWORK_GIT_TIMEOUT", "1")
    dest = project / "skills"
    remote = StalledRemote()
    try:
        started = time.monotonic()
        code = cli("refresh", "--mirror", "--repo", remote.url, "--dest", dest)
        elapsed = time.monotonic() - started
    finally:
        remote.close()

    out = capsys.readouterr()
    assert code != 0, "a stalled remote must fail the command, not report a refresh"
    assert elapsed < 30, f"the 1s budget did not bound the clone: {elapsed:.1f}s"
    assert "TEAMWORK_GIT_TIMEOUT" in out.out + out.err, out.out + out.err
    assert not bundle.is_checkout(bundle.default_mirror_path(dest)), (
        "a timed-out clone left a half-built checkout that the next run would trust"
    )


def test_a_local_remote_still_clones_under_the_same_budget(
    cli, project: Path, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("TEAMWORK_GIT_TIMEOUT", "1")
    source = seed_remote(tmp_path / "origin")

    dest = project / "skills"
    assert cli("refresh", "--mirror", "--repo", str(source), "--dest", dest) == 0
    assert bundle.is_checkout(bundle.default_mirror_path(dest))
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# skill\n"


def test_a_second_refresh_of_an_unchanged_remote_is_a_no_op(
    cli, project: Path, tmp_path: Path
) -> None:
    source = seed_remote(tmp_path / "origin")
    dest = project / "skills"

    assert cli("refresh", "--mirror", "--repo", str(source), "--dest", dest) == 0
    before = sorted(path.relative_to(dest) for path in dest.rglob("*") if path.is_file())
    assert cli("refresh", "--mirror", "--repo", str(source), "--dest", dest) == 0
    after = sorted(path.relative_to(dest) for path in dest.rglob("*") if path.is_file())
    assert before == after, "a second refresh of an unchanged remote changed the installed copy"
