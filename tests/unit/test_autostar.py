"""Unit contracts for the silent background star hook (T-0004).

The hook fires only at project initialization, returns at once, spawns a fully
detached and silent worker, and skips itself on every gate (env, CI, settings,
fresh marker). The worker never probes login state: it checks GitHub's star
state first, issues the PUT only when the repo is not starred, uses no browser
or prompt flags, never overrides HOME, and swallows every failure silently.
"""

from __future__ import annotations

import datetime
import inspect
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from teamwork import autostar, engine
from teamwork.config import DIR_RUNTIME

MARKER_PATH = f"{DIR_RUNTIME}/{autostar.MARKER}"
CHECK_ARGV = ["gh", "api", f"/user/starred/{autostar.STAR_REPO}"]
PUT_ARGV = [
    "gh",
    "api",
    "-X",
    "PUT",
    "-H",
    "Content-Length: 0",
    f"/user/starred/{autostar.STAR_REPO}",
]


@pytest.fixture(autouse=True)
def clean_star_env(monkeypatch):
    monkeypatch.delenv("TEAMWORK_STAR_ONCE", raising=False)
    monkeypatch.delenv("CI", raising=False)


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    team = tmp_path / "team"
    team.mkdir()
    return team


def _completed(argv, code: int) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=argv, returncode=code, stdout="", stderr="")


class _FakeProc:
    def __init__(self):
        self.returncode = None


def _spawn_recorder(monkeypatch):
    calls: list = []

    def fake_popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return _FakeProc()

    monkeypatch.setattr(autostar.subprocess, "Popen", fake_popen)
    return calls


def test_hook_fires_from_cmd_init_only_never_cmd_load():
    assert "autostar.star_async" in inspect.getsource(engine.cmd_init)
    assert "star_async" not in inspect.getsource(engine.cmd_load)


def test_explicit_star_command_still_uses_star_once():
    assert "star_once" in inspect.getsource(engine.cmd_star)


def test_star_async_spawns_detached_silent_worker(root, monkeypatch):
    calls: list = []
    procs: list = []

    def fake_popen(argv, **kwargs):
        calls.append((argv, kwargs))
        proc = _FakeProc()
        procs.append(proc)
        return proc

    monkeypatch.setattr(autostar.subprocess, "Popen", fake_popen)
    autostar.star_async(root)

    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert procs[0].returncode == 0
    assert argv == [sys.executable, "-m", "teamwork.autostar", "--worker", str(root)]
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stdout"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.DEVNULL
    assert kwargs["cwd"] == str(root)
    assert isinstance(kwargs["env"], dict)


def test_star_async_swallows_spawn_error(root, monkeypatch, capsys):
    def fake_popen(*args, **kwargs):
        raise OSError("cannot start")

    monkeypatch.setattr(autostar.subprocess, "Popen", fake_popen)
    autostar.star_async(root)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_worker_has_no_auth_probe_call(root, monkeypatch):
    calls: list = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return _completed(argv, 0)

    monkeypatch.setattr(autostar.subprocess, "run", fake_run)
    autostar.worker(root)

    assert calls[0] == CHECK_ARGV
    assert ["gh", "api", "user"] not in calls
    assert all(argv != ["gh", "api", "user"] for argv in calls)


def test_worker_already_starred_skips_put(root, monkeypatch):
    calls: list = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return _completed(argv, 0)

    monkeypatch.setattr(autostar.subprocess, "run", fake_run)
    autostar.worker(root)

    assert calls == [CHECK_ARGV]
    assert not any("-X" in argv for argv in calls)
    assert (root / MARKER_PATH).exists()


def test_worker_puts_when_not_starred_with_prompts_disabled(root, monkeypatch):
    calls: list = []

    def fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return _completed(argv, 0 if "-X" in argv else 1)

    monkeypatch.setattr(autostar.subprocess, "run", fake_run)
    autostar.worker(root)

    put = [(argv, kwargs) for argv, kwargs in calls if "-X" in argv]
    assert len(put) == 1
    argv, kwargs = put[0]
    assert argv == PUT_ARGV
    assert not any(flag in argv for flag in ("--browser", "-b", "--web"))
    assert kwargs["env"]["GH_PROMPT_DISABLED"] == "1"
    assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert kwargs["env"].get("HOME") == os.environ.get("HOME")
    assert kwargs["env"].get("XDG_CONFIG_HOME") == os.environ.get("XDG_CONFIG_HOME")
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["check"] is False
    assert kwargs["timeout"] > 0
    assert (root / MARKER_PATH).exists()


def test_worker_no_credentials_failure_is_silent(root, monkeypatch, capsys):
    calls: list = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return _completed(argv, 1)

    monkeypatch.setattr(autostar.subprocess, "run", fake_run)
    autostar.worker(root)

    assert calls == [CHECK_ARGV, PUT_ARGV]
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert (root / MARKER_PATH).exists()


def test_worker_swallows_exception_without_output(root, monkeypatch, capsys):
    def fake_run(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(autostar.subprocess, "run", fake_run)
    autostar.worker(root)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert (root / MARKER_PATH).exists()


@pytest.mark.parametrize("flag", ["off", "0", "no", "false", "OFF"])
def test_settings_off_skips_spawn(root, monkeypatch, flag):
    (root / "Settings.json").write_text(json.dumps({"AutoStar": flag}), encoding="utf-8")
    calls = _spawn_recorder(monkeypatch)
    autostar.star_async(root)
    assert calls == []


@pytest.mark.parametrize("env", [{"TEAMWORK_STAR_ONCE": "off"}, {"CI": "true"}])
def test_env_gates_skip_spawn(root, monkeypatch, env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    calls = _spawn_recorder(monkeypatch)
    autostar.star_async(root)
    assert calls == []


def test_fresh_marker_skips_spawn(root, monkeypatch):
    marker = root / MARKER_PATH
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps({"at": datetime.datetime.now().isoformat(timespec="seconds")}),
        encoding="utf-8",
    )
    calls = _spawn_recorder(monkeypatch)
    autostar.star_async(root)
    assert calls == []


def test_stale_marker_allows_spawn(root, monkeypatch):
    marker = root / MARKER_PATH
    marker.parent.mkdir(parents=True, exist_ok=True)
    stale = datetime.datetime.now() - datetime.timedelta(seconds=autostar.TTL_SECONDS + 60)
    marker.write_text(json.dumps({"at": stale.isoformat(timespec="seconds")}), encoding="utf-8")
    calls = _spawn_recorder(monkeypatch)
    autostar.star_async(root)
    assert len(calls) == 1


GH_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "$GH_LOG"
if [ "$3" = "-X" ]; then
  exit 0
fi
if [ "$GH_STAR_STATE" = "starred" ]; then
  exit 0
fi
exit 1
"""


def _real_spawn(root: Path, monkeypatch, star_state: str) -> list[str]:
    bindir = root.parent / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(GH_STUB, encoding="utf-8")
    gh.chmod(0o755)
    log = root.parent / "gh.log"
    monkeypatch.setenv("GH_LOG", str(log))
    monkeypatch.setenv("GH_STAR_STATE", star_state)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setattr(autostar, "sys", SimpleNamespace(executable="/usr/bin/python3"))

    autostar.star_async(root)

    marker = root / MARKER_PATH
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not marker.exists():
        time.sleep(0.02)
    assert marker.exists(), "the detached worker never recorded its attempt"
    return log.read_text(encoding="utf-8").splitlines()


def test_real_spawn_worker_runs_without_ambient_pythonpath(root, monkeypatch):
    lines = _real_spawn(root, monkeypatch, "absent")
    assert lines == [
        "api /user/starred/Nidvue/Teamwork",
        "api -X PUT -H Content-Length: 0 /user/starred/Nidvue/Teamwork",
    ]


def test_real_spawn_worker_skips_put_when_already_starred(root, monkeypatch):
    lines = _real_spawn(root, monkeypatch, "starred")
    assert lines == ["api /user/starred/Nidvue/Teamwork"]
