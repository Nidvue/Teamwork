"""The status widget against the real engine, in a checkout the test builds.

Why this layer exists: the unit layer (`tests/unit/test_pi_status_stale_ctx.py`)
hands the extension a fake `scripts/teamwork.py` that prints a payload, so it
proves the renderer and the stop-on-stale path but never the seam in between -
`findEngine`, the engine's own JSON contract, and a timer that outlives a
session. This layer drives the same extension the host loads, in a checkout the
test builds itself, against the real `scripts/teamwork.py` from this revision and
a team tree the test writes. Nothing is read from the ambient team, so the
result is the same in a worktree, on main and in CI.

Node is a host tool, not a test dependency: without it the layer skips with the
reason, exactly as the unit layer does.
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

DRIVE = """
const mod = await import(process.env.TW_EXTENSION);
const handlers = new Map();
const commands = new Map();
const pi = {
  on: (name, fn) => { handlers.set(name, fn); },
  registerCommand: (name, command) => { commands.set(name, command); },
};
const intervals = [];
globalThis.setInterval = (fn, ms) => {
  const handle = { fn, ms, cleared: false };
  intervals.push(handle);
  return handle;
};
globalThis.clearInterval = (handle) => {
  if (handle) handle.cleared = true;
};
let unhandled = 0;
process.on("unhandledRejection", () => { unhandled += 1; });
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const paint = { widgets: [], status: "" };
const live = {
  cwd: process.env.TW_CWD,
  ui: {
    setWidget: (_key, lines) => { paint.widgets.push(lines); },
    setStatus: (_key, value) => { paint.status = value; },
    notify: () => {},
  },
};
const stale = () => { throw new Error("This extension ctx is stale after session replacement or reload."); };
const dead = { cwd: process.env.TW_CWD, get ui() { return stale(); } };
const painted = () => paint.widgets.some((lines) => Array.isArray(lines) && lines.length > 0);
const running = () => intervals.filter((handle) => !handle.cleared).length;
mod.default(pi);
await handlers.get("session_start")({}, live);
const deadline = Date.now() + Number(process.env.TW_WAIT || 8000);
while (Date.now() < deadline && !painted()) await wait(50);
const paintedFromEngine = painted();
const liveAfterFirst = running();
await handlers.get("session_start")({}, live);
const liveAfterSecond = running();
const tick = intervals.filter((handle) => !handle.cleared).pop();
live.ui.setWidget = stale;
live.ui.setStatus = stale;
let commandThrew = 0;
if (tick) {
  try {
    await tick.fn();
  } catch {
    commandThrew += 1;
  }
}
await wait(200);
const liveAfterStaleTick = running();
try {
  await commands.get("tw-status").handler("", dead);
} catch {
  commandThrew += 1;
}
await wait(200);
const liveAfterStale = running();
const attempts = paint.widgets.length;
for (const handle of intervals) {
  if (handle.cleared) continue;
  try {
    await handle.fn();
  } catch {
    commandThrew += 1;
  }
}
await wait(200);
console.log(JSON.stringify({
  unhandled,
  commandThrew,
  paintedFromEngine,
  footer: paint.status,
  firstWidget: paint.widgets.find((lines) => Array.isArray(lines) && lines.length) || [],  liveAfterFirst,
  liveAfterSecond,
  liveAfterStale,
  liveAfterStaleTick,
  ticked: Boolean(tick),
  attempts,
}));
"""

QUEUE = """# Task queue - developer

## T-0001 · Prove the widget paints from a real status run
- priority: P0
- status: doing
- claimed_by: Developer
- review: required
- area: widget
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


def checkout(base: Path) -> Path:
    """A project the extension can find the real engine in, and nothing else.

    `project_root` names the team after the project directory, so the fixture's
    own name decides which team tree `status` reads: the ambient one is never in
    reach. `src` is a link to this revision, so the engine that answers is the
    code under test.
    """
    project = base / "WidgetFixture"
    (project / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "teamwork.py", project / "scripts" / "teamwork.py")
    (project / "src").symlink_to(ROOT / "src", target_is_directory=True)
    team = project / ".pi" / "Teamwork" / "Teams" / "WidgetFixture"
    (team / "Roles" / "Developer").mkdir(parents=True)
    (team / "Agents" / "Developer").mkdir(parents=True)
    (team / "Roles" / "Developer" / "TaskQueue.md").write_text(QUEUE)
    return project


def agent_home(base: Path) -> tuple[Path, Path]:
    """A host laid out like the pi install: the adapter under `<agent>/extensions`,
    the engine only under `<agent>/skills/tw`, the project somewhere else.

    The engine is never under the project here, which is the shape every repo but
    the skill checkout has: the hunt has to self-locate the bundle.
    """
    agent = base / "Agent"
    (agent / "extensions").mkdir(parents=True)
    adapter = agent / "extensions" / "tw-status.ts"
    shutil.copy(EXTENSION, adapter)
    skill = agent / "skills" / "tw"
    (skill / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "teamwork.py", skill / "scripts" / "teamwork.py")
    (skill / "src").symlink_to(ROOT / "src", target_is_directory=True)
    project = base / "SkillFixture"
    team = project / ".pi" / "Teamwork" / "Teams" / "SkillFixture"
    (team / "Roles" / "Developer").mkdir(parents=True)
    (team / "Agents" / "Developer").mkdir(parents=True)
    (team / "Roles" / "Developer" / "TaskQueue.md").write_text(QUEUE)
    return adapter, project


def drive(cwd: Path, wait_ms: int = 8000, extension: Path = EXTENSION) -> dict:
    env = {key: value for key, value in os.environ.items() if key != "TEAMWORK_ROOT"}
    result = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", DRIVE],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={
            **env,
            "TW_EXTENSION": extension.as_uri(),
            "TW_CWD": str(cwd),
            "TW_WAIT": str(wait_ms),
            "TEAMWORK_PYTHON": sys.executable,
        },
        timeout=180,
    )
    assert result.returncode == 0, f"the process died: {result.returncode}\n{result.stderr}"
    assert result.stdout.strip(), result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_the_widget_paints_the_real_status_payload_and_stops_on_a_stale_ctx(
    tmp_path: Path,
) -> None:
    body = drive(checkout(tmp_path))
    assert body["paintedFromEngine"], f"the widget never painted from a real status run: {body}"
    assert any("T-0001" in line for line in body["firstWidget"]), (
        f"the row of the fixture's only busy instance was not drawn: {body}"
    )
    assert all(isinstance(line, str) for line in body["firstWidget"]), body["firstWidget"]
    assert body["unhandled"] == 0, f"a rejected refresh escaped: {body}"
    assert body["commandThrew"] == 0, f"a throw escaped a handler: {body}"
    assert body["liveAfterFirst"] == 1, (
        f"a real session left {body['liveAfterFirst']} timer(s): {body}"
    )
    assert body["liveAfterSecond"] == 1, f"a second session_start stacked timers: {body}"
    assert body["ticked"], f"no live timer was left to tick: {body}"
    assert body["liveAfterStaleTick"] == 0, (
        f"the refresh tick kept running into a replaced session: {body}"
    )
    assert body["liveAfterStale"] == 0, f"a timer survived a stale ctx: {body}"
    assert body["attempts"] <= 2, f"the stale ctx was retried: {body}"


def test_a_skill_only_install_paints_the_team_of_the_session_cwd(tmp_path: Path) -> None:
    adapter, project = agent_home(tmp_path)
    body = drive(project, extension=adapter)
    assert body["paintedFromEngine"], f"a skill-only install drew nothing: {body}"
    assert any("T-0001" in line for line in body["firstWidget"]), (
        f"the widget read another project's team: {body['firstWidget']}"
    )
    assert body["unhandled"] == 0, f"a rejected refresh escaped: {body}"


def test_a_checkout_without_the_engine_paints_nothing_and_does_not_crash(
    tmp_path: Path,
) -> None:
    body = drive(tmp_path, wait_ms=1200)
    assert not body["paintedFromEngine"], f"a widget appeared with no engine to read: {body}"
    assert body["unhandled"] == 0, f"a rejected refresh escaped: {body}"
    assert body["commandThrew"] == 0, f"a throw escaped a handler: {body}"
    assert body["liveAfterStale"] == 0, f"a timer survived a stale ctx: {body}"
