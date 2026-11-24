"""A stale extension ctx stops the widget, it does not exit node.

Why this file exists: the lane log of L-0264 and L-0279 both end with the host
message "This extension ctx is stale after session replacement or reload" raised
at `get ui` from `refresh()` in extensions/tw-status.ts, followed by
`Node.js v26.13.0` - the interval touched a ctx captured at session_start after
the session was replaced, the rejection reached process level and node exited,
losing the lane's run. This probe loads the extension with a fake ctx whose `ui`
and `cwd` getters throw that exact error once the session is replaced, fires the
interval callback, and requires the process to survive: the timer is stopped, no
widget write follows, and a live session still draws.

Node is a host tool, not a test dependency: without it the test skips with the
reason.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXTENSION = ROOT / "extensions" / "tw-status.ts"
STALE = (
    "This extension ctx is stale after session replacement or reload. "
    "Do not use a captured pi or command ctx after ctx.newSession()"
)

FAKE_ENGINE = """
import json

print(
    json.dumps(
        {
            "instances": [
                {
                    "instance": "dev-1",
                    "role": "developer",
                    "state": "busy",
                    "task": "T-0001",
                    "title": "a title",
                    "elapsed_seconds": 60,
                    "elapsed_text": "1m00s",
                    "remaining_seconds": 600,
                    "remaining_text": "10m00s",
                    "activity": "lane started",
                    "last": "lane.start",
                    "last_seconds": 5,
                    "model": "a-model",
                }
            ],
            "lanes": [],
            "counts": {"lanes_live": 0, "review": 0},
        }
    )
)
"""

PROBE = """
const mod = await import(process.env.TW_EXTENSION);
const realSetTimeout = globalThis.setTimeout;
const intervals = [];
const cleared = [];
globalThis.setInterval = (fn) => {
  const token = { unref() {} };
  intervals.push([fn, token]);
  return token;
};
globalThis.clearInterval = (token) => cleared.push(token);

const calls = [];
const handlers = new Map();
mod.default({ on: (name, fn) => handlers.set(name, fn), registerCommand: () => {} });

const session = () => {
  const state = { stale: false };
  const ui = {
    setWidget: (key, lines) => calls.push(["widget", key, lines]),
    setStatus: (key, value) => calls.push(["status", key, value]),
    notify: () => {},
  };
  const boom = () => {
    if (state.stale) throw new Error(process.env.TW_STALE);
  };
  return {
    state,
    ctx: {
      get ui() {
        boom();
        return ui;
      },
      get cwd() {
        boom();
        return process.env.TW_CWD;
      },
    },
  };
};

const pause = (ms) => new Promise((resolve) => realSetTimeout(resolve, ms));
const waitFor = async (done, ms = 20000) => {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (done()) return true;
    await pause(50);
  }
  return false;
};
const drew = () => calls.some((call) => call[0] === "widget" && Array.isArray(call[2]) && call[2].length > 0);

const out = {};

const a = session();
await handlers.get("session_start")({}, a.ctx);
out.live_drew = await waitFor(drew);
out.live_first = calls.length ? String(calls[0][2][0] || "") : "";
const beforeStale = calls.length;
a.state.stale = true;
intervals[intervals.length - 1][0]();
await pause(400);
out.stale_draws = calls.length - beforeStale;
out.stale_stopped = cleared.length > 0;

const b = session();
b.state.stale = true;
const clearedB = cleared.length;
await handlers.get("session_start")({}, b.ctx);
await pause(400);
out.stale_start_stopped = cleared.length > clearedB;
out.stale_start_draws = calls.length - beforeStale;

const c = session();
await handlers.get("session_start")({}, c.ctx);
out.shutdown_drew = await waitFor(drew);
calls.length = 0;
const clearedC = cleared.length;
await handlers.get("session_shutdown")({}, c.ctx);
out.shutdown_cleared = calls.some(
  (call) => call[0] === "widget" && Array.isArray(call[2]) && call[2].length === 0,
);
out.shutdown_stopped = cleared.length > clearedC;

console.log(JSON.stringify(out));
"""


def node() -> str:
    binary = shutil.which("node")
    if not binary:
        pytest.skip("node is not installed, so the extension cannot be executed here")
    probe = subprocess.run(
        [binary, "--experimental-strip-types", "--no-warnings", "-e", "0"],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        pytest.skip(f"node {binary} cannot strip TypeScript types: {probe.stderr.strip()[:120]}")
    return binary


@pytest.fixture(scope="module")
def observed(tmp_path_factory: pytest.TempPathFactory) -> dict:
    project = tmp_path_factory.mktemp("panel")
    engine = project / "scripts" / "teamwork.py"
    engine.parent.mkdir(parents=True)
    engine.write_text(FAKE_ENGINE)
    result = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", PROBE],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={
            **os.environ,
            "TW_EXTENSION": EXTENSION.as_uri(),
            "TW_CWD": str(project),
            "TW_STALE": STALE,
            "TEAMWORK_PYTHON": sys.executable,
            "TEAMWORK_AGENT_HOST": "pi",
        },
        timeout=180,
    )
    assert result.returncode == 0, (
        f"the probe process exited {result.returncode}: {result.stderr.strip()[-1500:]}"
    )
    return json.loads(result.stdout)


def test_a_live_session_still_draws(observed: dict) -> None:
    assert observed["live_drew"], observed
    assert observed["live_first"].startswith("teamwork"), observed


def test_a_stale_ctx_stops_the_interval_without_drawing(observed: dict) -> None:
    assert observed["stale_stopped"], observed
    assert observed["stale_draws"] == 0, observed


def test_a_ctx_already_stale_at_session_start_is_shutdown(observed: dict) -> None:
    assert observed["stale_start_stopped"], observed
    assert observed["stale_start_draws"] == 0, observed


def test_shutdown_clears_and_stops(observed: dict) -> None:
    assert observed["shutdown_drew"], observed
    assert observed["shutdown_cleared"], observed
    assert observed["shutdown_stopped"], observed
