"""Acceptance: the status panel survives a session replacement.

The operator-visible promise of the stale-ctx fix (extensions/teamwork-status.ts)
stated as three scenarios, each driven the way a person meets the widget - the
shipped extension file, loaded through the host's own registration contract, with
a session that is replaced and a command the operator types:

* a replaced session does not take the host process down: the stale ctx is
  refused, nothing is drawn afterwards and node exits clean,
* a reload gives the panel back: the new session paints again and leaves exactly
  one live refresh timer,
* the toggle still works: ``teamwork-status`` off clears the panel and stops the
  timer, and on paints it again.

The payload comes from a stub engine this test writes, so the layer proves the
artifact's contract rather than the engine's arithmetic - the integration layer
(tests/integration/test_widget_survives.py) owns the real engine seam. Node is a
host tool, not a test dependency: without it the layer skips with the reason.

Owner: reviewer. Layer: acceptance. Area: widget. Task: T-0008.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXTENSION = ROOT / "extensions" / "teamwork-status.ts"

STUB_ENGINE = """
import json

print(
    json.dumps(
        {
            "schema": 5,
            "count": 1,
            "counts": {"busy": 1, "idle": 0, "lanes_live": 0, "review": 0},
            "instances": [
                {
                    "instance": "Developer",
                    "role": "developer",
                    "state": "busy",
                    "task": "T-0001",
                    "title": "prove the panel comes back after a reload",
                    "elapsed_seconds": 60,
                    "elapsed_text": "1m00s",
                    "remaining_seconds": 600,
                    "activity": "lane started",
                    "model": "a-model",
                }
            ],
            "lanes": [],
        }
    )
)
"""

PROBE = """
const mod = await import(process.env.TW_EXTENSION);
const handlers = new Map();
const commands = new Map();
mod.default({
  on: (name, fn) => { handlers.set(name, fn); },
  registerCommand: (name, command) => { commands.set(name, command); },
});
const intervals = [];
globalThis.setInterval = (fn) => {
  const handle = { fn, cleared: false };
  intervals.push(handle);
  return handle;
};
globalThis.clearInterval = (handle) => { if (handle) handle.cleared = true; };
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const paints = [];
const statuses = [];
const live = {
  cwd: process.env.TW_CWD,
  ui: {
    setWidget: (_key, lines) => { paints.push(lines); },
    setStatus: (_key, value) => { statuses.push(value); },
    notify: () => {},
  },
};
const stale = () => { throw new Error(process.env.TW_STALE); };
const dead = { cwd: process.env.TW_CWD, get ui() { return stale(); } };
const running = () => intervals.filter((handle) => !handle.cleared).length;
const since = (mark) => paints.slice(mark);
const threw = async (fn) => {
  try {
    await fn();
    return 0;
  } catch {
    return 1;
  }
};
const drew = (mark) => since(mark).some((lines) => Array.isArray(lines) && lines.length > 0);
const waitForPaint = async (mark) => {
  const end = Date.now() + 8000;
  while (Date.now() < end && !drew(mark)) await wait(50);
  return drew(mark);
};
let unhandled = 0;
process.on("unhandledRejection", () => { unhandled += 1; });
const out = {};

await handlers.get("session_start")({}, live);
out.first_paint = await waitForPaint(0);
out.first_lines = paints.find((lines) => Array.isArray(lines) && lines.length > 0) || [];
out.timers_after_first = running();

let mark = paints.length;
out.shutdown_threw = await threw(() => handlers.get("session_shutdown")({}, live));
out.shutdown_cleared = since(mark).some((lines) => Array.isArray(lines) && lines.length === 0);
out.timers_after_shutdown = running();

mark = paints.length;
await handlers.get("session_start")({}, live);
out.reload_paint = await waitForPaint(mark);
out.timers_after_reload = running();

mark = paints.length;
out.stale_start_threw = await threw(() => handlers.get("session_start")({}, dead));
await wait(300);
out.stale_start_paint = since(mark).length;
out.timers_after_stale_start = running();

await handlers.get("session_start")({}, live);
mark = paints.length;
const toggle = commands.get("teamwork-status").handler;
out.off_threw = await threw(() => toggle("", live));
out.off_cleared = since(mark).some((lines) => Array.isArray(lines) && lines.length === 0);
out.timers_after_off = running();
mark = paints.length;
out.on_threw = await threw(() => toggle("", live));
out.on_paint = await waitForPaint(mark);
out.timers_after_on = running();
out.stale_command_threw = await threw(() => toggle("", dead));
await wait(300);
out.unhandled = unhandled;
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
    project = tmp_path_factory.mktemp("widget")
    engine = project / "scripts" / "teamwork.py"
    engine.parent.mkdir(parents=True)
    engine.write_text(STUB_ENGINE, encoding="utf-8")
    result = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", PROBE],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={
            **os.environ,
            "TW_EXTENSION": EXTENSION.as_uri(),
            "TW_CWD": str(project),
            "TW_STALE": "This extension ctx is stale after session replacement or reload.",
        },
        timeout=180,
    )
    assert result.returncode == 0, (
        f"the host process died: {result.returncode}\n{result.stderr.strip()[-1500:]}"
    )
    assert result.stdout.strip(), result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_a_live_session_shows_the_panel(observed: dict) -> None:
    """The operator sees the busy row of the team the session is looking at."""
    assert observed["first_paint"], observed
    assert any("Developer" in line for line in observed["first_lines"]), observed["first_lines"]
    assert any("T-0001" in line for line in observed["first_lines"]), observed["first_lines"]
    assert observed["timers_after_first"] == 1, observed


def test_a_replaced_session_neither_kills_the_host_nor_loses_the_panel(observed: dict) -> None:
    """Shutdown clears the panel; the reload paints again; a stale start is refused."""
    assert observed["shutdown_threw"] == 0, observed
    assert observed["shutdown_cleared"], observed
    assert observed["timers_after_shutdown"] == 0, observed
    assert observed["reload_paint"], f"the panel never came back after the reload: {observed}"
    assert observed["timers_after_reload"] == 1, observed
    assert observed["stale_start_threw"] == 0, f"a stale start threw out: {observed}"
    assert observed["stale_start_paint"] == 0, f"a stale session drew: {observed}"
    assert observed["timers_after_stale_start"] == 0, observed
    assert observed["unhandled"] == 0, f"a rejected refresh escaped: {observed}"


def test_the_operator_can_switch_the_panel_off_and_on(observed: dict) -> None:
    """The documented toggle clears and stops, then paints and restarts."""
    assert observed["off_threw"] == 0, observed
    assert observed["off_cleared"], observed
    assert observed["timers_after_off"] == 0, observed
    assert observed["on_threw"] == 0, observed
    assert observed["on_paint"], f"the toggle did not paint again: {observed}"
    assert observed["timers_after_on"] == 1, observed
    assert observed["stale_command_threw"] == 0, f"a stale command threw out: {observed}"
    assert observed["unhandled"] == 0, f"a rejected refresh escaped: {observed}"
