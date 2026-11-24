"""Hard bounds on code-level operations: a hung step fails, it cannot park a lane.

Layer ``unit``, area ``hard-timeouts``. The audit found an empty search value that
spun forever, a launcher that waited without a clock, and reads with no ceiling.
Each test here proves one of those bounds on its own seam.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from teamwork import engine, gitutil, hooks, lanerun, lanes

REPO_ROOT = Path(__file__).resolve().parents[2]

CHECKER_PATH = REPO_ROOT / "scripts" / "check_release_consistency.py"


def make_root(project: Path) -> Path:
    root = project / ".pi" / "Teamwork" / "Teams" / "Sample"
    root.mkdir(parents=True)
    return root


def test_an_empty_search_value_terminates() -> None:
    seen: list[bool] = []

    def call() -> None:
        seen.append(engine._every_occurrence_is_a_path("x" * 200, ""))

    worker = threading.Thread(target=call, daemon=True)
    worker.start()
    worker.join(timeout=5)

    assert not worker.is_alive(), "an empty value must not spin forever"
    assert seen == [True]


def test_an_exact_path_value_still_terminates() -> None:
    assert engine._every_occurrence_is_a_path("a path: /home/agent and /home/agent", "/home/agent")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def test_a_hung_launcher_is_killed_and_reported_as_a_timeout(tmp_path: Path) -> None:
    pid_file = tmp_path / "child.pid"
    script = (
        "import os, pathlib, sys, time; "
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(30)"
    )
    run_path = tmp_path / "hung.run"
    started = time.monotonic()

    code = lanerun.run(run_path, 0.3, [sys.executable, "-c", script, str(pid_file)])

    elapsed = time.monotonic() - started
    outcome = lanerun.outcome_path(run_path).read_text(encoding="utf-8")
    pid = int(pid_file.read_text(encoding="utf-8").strip())

    assert code == lanerun.TIMEOUT_EXIT
    assert '"state": "timeout"' in outcome
    assert elapsed < 10, f"the hung launcher outlived its bound: {elapsed:.1f}s"
    for _ in range(100):
        if not _alive(pid):
            break
        time.sleep(0.05)
    assert not _alive(pid), f"the hung launcher survived: pid {pid}"


class RecordingChild:
    pid = 0

    def __init__(self, seen: dict[str, object]) -> None:
        self.seen = seen

    def wait(self, timeout: float | None = None) -> int:
        self.seen["timeout"] = timeout
        return 0

    def terminate(self) -> None:
        pass

    def kill(self) -> None:
        pass


@pytest.mark.parametrize(
    ("budget", "expected"),
    [
        (0.0, lanerun.DEFAULT_LANE_TIMEOUT),
        (-1.0, None),
    ],
)
def test_the_launcher_wait_is_bounded_unless_explicitly_unbounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, budget: float, expected: float | None
) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(lanerun.subprocess, "Popen", lambda *args, **kwargs: RecordingChild(seen))

    lanerun.run(tmp_path / "rec.run", budget, ["launcher"])

    assert seen["timeout"] == expected


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ([], lanerun.DEFAULT_LANE_TIMEOUT),
        (["--timeout", "-1"], -1.0),
    ],
)
def test_the_launcher_cli_defaults_to_the_lane_budget(
    monkeypatch: pytest.MonkeyPatch, args: list[str], expected: float
) -> None:
    seen: dict[str, object] = {}

    def fake_run(run_path, timeout, argv):
        seen["timeout"] = timeout
        return 0

    monkeypatch.setattr(lanerun, "run", fake_run)

    assert lanerun.main(["--run", "lane.run", *args, "--", "launcher"]) == 0
    assert seen["timeout"] == expected
    assert lanerun.DEFAULT_LANE_TIMEOUT == 25 * 60


def test_refresh_derives_a_deadline_from_a_legacy_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lanes, "pid_alive", lambda pid: True)
    monkeypatch.setattr(lanes, "terminate", lambda pid: None)
    monkeypatch.setattr(lanes, "read_outcome", lambda root, run: None)
    monkeypatch.setattr(lanes, "transcript_aborted", lambda log: False)
    monkeypatch.setattr(lanes, "activity", lambda run, finished: (finished, None))
    monkeypatch.setattr(lanes, "write_run", lambda root, run: None)
    run = {
        "id": "run-1",
        "state": lanes.RUNNING,
        "pid": 424242,
        "created": time.time() - 3600,
        "minutes": 1,
        "log": "",
    }

    out = lanes.refresh(Path("."), run)

    assert out["state"] == lanes.TIMEOUT
    assert out["cause"] == "budget"


def test_an_oversized_artifact_fails_instead_of_reading_forever(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "SampleProject"
    root = make_root(project)
    artifact = project / "big.log"
    artifact.write_bytes(b"x" * 16)
    monkeypatch.setattr(engine, "MAX_ARTIFACT_BYTES", 8)

    with pytest.raises(SystemExit) as exc:
        engine.artifact_digest(root, "big.log")

    assert exc.value.code == 1
    assert "larger than 8 bytes" in capsys.readouterr().err


def test_a_small_artifact_still_hashes_under_the_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "SampleProject"
    root = make_root(project)
    (project / "small.log").write_bytes(b"ok")
    monkeypatch.setattr(engine, "MAX_ARTIFACT_BYTES", 8)

    assert engine.artifact_digest(root, "small.log").endswith(":2")


def test_the_artifact_cap_is_64_mib() -> None:
    assert engine.MAX_ARTIFACT_BYTES == 64 * 1024 * 1024


def test_a_bare_git_commit_call_passes_a_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(argv, 1, "", "")

    monkeypatch.setattr(engine.subprocess, "run", fake_run)

    assert engine._git_author(tmp_path, {}) == ("", "")
    assert seen["timeout"] == gitutil.git_timeout()
    assert gitutil.git_timeout() == gitutil.GIT_TIMEOUT_SECONDS


def test_cat_file_calls_are_bounded_and_keep_binary_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple] = []

    def fake_run(argv, **kwargs):
        seen.append((tuple(argv), kwargs["timeout"]))
        payload = b"12\n" if "-s" in argv else b"\x00binary"
        return subprocess.CompletedProcess(argv, 0, payload, b"")

    monkeypatch.setattr(gitutil.subprocess, "run", fake_run)

    assert gitutil.staged_blob_meta(tmp_path, "f.txt") == (12, b"\x00binary")
    assert seen == [
        (("git", "-C", str(tmp_path), "cat-file", "-s", ":f.txt"), gitutil.git_timeout()),
        (("git", "-C", str(tmp_path), "cat-file", "blob", ":f.txt"), gitutil.git_timeout()),
    ]


def test_every_shim_hook_is_bounded() -> None:
    for stage in ("pre-commit", "pre-push"):
        for chained in (False, True):
            body = hooks.shim(stage, chain=chained)
            assert "run_bounded() {" in body
            assert "timeout 300" in body
            assert "exec python3" not in body


def test_an_oversized_refspec_list_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hooks, "MAX_REFSPEC_BYTES", 16)
    monkeypatch.setattr(sys, "stdin", io.StringIO("refs " + "x" * 100 + "\n"))

    with pytest.raises(hooks.RefspecTooLarge):
        hooks.pushed_refspecs()


def _checker():
    spec = importlib.util.spec_from_file_location("check_release_consistency_bounds", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DripResponse:
    status = 200

    def __init__(self, total: int) -> None:
        self.remaining = total

    def __enter__(self) -> DripResponse:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self, size: int = -1) -> bytes:
        take = min(size if size > 0 else self.remaining, self.remaining, 1024)
        self.remaining -= take
        return b"x" * take


def test_an_oversized_http_response_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    checker = _checker()
    monkeypatch.setattr(checker, "HTTP_RESPONSE_MAX_BYTES", 4096)
    monkeypatch.setattr(checker, "_request_headers", lambda url: {})
    monkeypatch.setattr(
        checker.urllib.request, "urlopen", lambda request, timeout: DripResponse(8192)
    )

    with pytest.raises(checker.InputError, match="larger than 4096 bytes"):
        checker._http_get("https://example.invalid/blob")


def test_a_slow_drip_is_bounded_by_a_total_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    checker = _checker()
    monkeypatch.setattr(checker, "HTTP_TOTAL_DEADLINE", 0.05)
    monkeypatch.setattr(checker, "_request_headers", lambda url: {})

    class Drip:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc_info: object) -> bool:
            return False

        def read(self, size: int = -1) -> bytes:
            time.sleep(0.01)
            return b"x"

    monkeypatch.setattr(checker.urllib.request, "urlopen", lambda request, timeout: Drip())

    with pytest.raises(checker.InputError, match="exceeded 0.05s"):
        checker._http_get("https://example.invalid/slow")
