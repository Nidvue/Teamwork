"""The OpenCode TUI widget is executed, not grepped for.

The v2.3.0 authoring signature was validated against the installed binary and the
published docs: a TUI part default-exports ``Plugin.define({ id, setup })`` from
``@opencode/plugin/tui`` and claims ``ui.slot({ append: "home.footer.status", render })``.
The installed ``@opencode-ai/plugin`` type package is 1.18.x and cannot prove that,
so this test imports the pure core through node's type stripping with a stub context
and a fake CLI, and asserts the slot claim, the poll command, the 2 s interval and
the lines rendered from a captured schema-5 payload. It also proves the plugin ships
in the built npm package. Live TUI rendering inside a running OpenCode session is
not claimed here.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "tw-status"
INDEX = PLUGIN / "index.ts"
TUI = PLUGIN / "tui.tsx"
BUILD = ROOT / "scripts" / "build_pi_package.py"

HARNESS = """
(async () => {
  const mod = await import(process.env.TW_PLUGIN);
  const calls = { slots: [], exec: [], intervals: [] };
  const payload = JSON.parse(process.env.TW_PAYLOAD);
  const deps = {
    engine: {
      python: process.env.TW_PYTHON,
      engine: process.env.TW_ENGINE,
      project: process.env.TW_PROJECT,
    },
    env: { ...process.env, TEAMWORK_AGENT_HOST: process.env.TW_HOST || "" },
    width: () => 100,
    exec: (file, args, options, cb) => {
      calls.exec.push({ file, args, timeout: options.timeout, maxBuffer: options.maxBuffer });
      cb(null, JSON.stringify(payload), "");
      return {};
    },
    schedule: (fn, ms) => { calls.intervals.push(ms); calls.tick = fn; return "handle"; },
    cancel: (handle) => { calls.cancelled = handle; },
  };
  let viewLines = [];
  const view = { element: () => "TUI-ELEMENT", update: (lines) => { viewLines = lines; } };
  const def = mod.defineStatusPlugin(() => view, deps);
  const ctx = {
    ui: {
      slot: (input) => {
        calls.slots.push(input);
        return () => { calls.unclaimed = true; };
      },
    },
  };
  const cleanup = def.setup(ctx);
  await new Promise((resolve) => setImmediate(resolve));
  const slot = calls.slots[0];
  const out = {
    id: def.id,
    defaultId: mod.default.id,
    defaultSetup: typeof mod.default.setup,
    refreshMs: mod.REFRESH_MS,
    slotName: mod.SLOT,
    slots: calls.slots.map((s) => ({ append: s.append, hasRender: typeof s.render === "function" })),
    element: slot ? slot.render({ sessionID: "s1" }) : null,
    exec: calls.exec,
    intervals: calls.intervals,
    lines: viewLines,
  };
  if (typeof cleanup === "function") {
    cleanup();
    out.cleanup = { cancelled: calls.cancelled, unclaimed: calls.unclaimed, cleared: viewLines.length === 0 };
  }
  console.log(JSON.stringify(out));
})().catch((error) => {
  console.log(JSON.stringify({ error: String(error && error.message) }));
});
"""

SERVER_HARNESS = """
(async () => {
  const mod = await import(process.env.TW_PLUGIN);
  const calls = { slots: [] };
  const ctx = new Proxy({}, {
    get(_target, prop) {
      if (prop === "ui") return undefined;
      return undefined;
    },
  });
  let threw = null;
  try {
    mod.default.setup(ctx);
  } catch (error) {
    threw = String((error && error.message) || error);
  }
  console.log(JSON.stringify({ threw, slots: calls.slots, id: mod.default.id }));
})().catch((error) => {
  console.log(JSON.stringify({ harnessError: String(error && error.message) }));
});
"""

PAYLOAD = {
    "schema": 5,
    "generated": "2026-11-25T09:54:22",
    "count": 12,
    "counts": {
        "busy": 2,
        "stalled": 1,
        "idle": 9,
        "ready": 0,
        "review": 0,
        "activated": 12,
        "retired": 1,
        "lanes_live": 1,
        "lanes_ended": 110,
        "lanes": 6,
    },
    "instances": [
        {
            "instance": "Developer",
            "role": "developer",
            "state": "busy",
            "task": "T-0023",
            "stalled": False,
        },
        {
            "instance": "Architect",
            "role": "architect",
            "state": "stalled",
            "task": "T-0020",
            "stalled": True,
        },
    ],
    "lanes": [
        {
            "id": "L-0200",
            "instance": "Developer",
            "task": "T-0023",
            "state": "running",
            "elapsed_text": "12m",
        }
    ],
}


def node() -> str:
    binary = shutil.which("node")
    if not binary:
        pytest.skip("node is not installed, so the plugin cannot be executed here")
    probe = subprocess.run(
        [binary, "--experimental-strip-types", "--no-warnings", "-e", "0"],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        pytest.skip(f"node {binary} cannot strip TypeScript types: {probe.stderr.strip()[:120]}")
    return binary


def drive(payload: dict, host: str = "") -> dict:
    if not INDEX.is_file():
        pytest.skip("the plugin source is not present in this checkout")
    result = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", HARNESS],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={
            **os.environ,
            "TW_PLUGIN": INDEX.as_uri(),
            "TW_PAYLOAD": json.dumps(payload),
            "TW_PYTHON": "/abs/venv/bin/python",
            "TW_ENGINE": "scripts/teamwork.py",
            "TW_PROJECT": "/project/root",
            "TW_HOST": host,
        },
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert "error" not in body, body["error"]
    return body


def drive_server() -> dict:
    if not INDEX.is_file():
        pytest.skip("the plugin source is not present in this checkout")
    result = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", SERVER_HARNESS],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "TW_PLUGIN": INDEX.as_uri(), "TEAMWORK_AGENT_HOST": "opencode"},
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert "harnessError" not in body, body["harnessError"]
    return body


def test_setup_claims_footer_status_and_renders_the_schema5_summary() -> None:
    got = drive(PAYLOAD)
    assert got["id"] == "tw-status", got
    assert got["defaultId"] == "tw-status" and got["defaultSetup"] == "function", got
    assert got["slotName"] == "home.footer.status", got
    assert got["slots"] == [{"append": "home.footer.status", "hasRender": True}], got["slots"]
    assert got["element"] == "TUI-ELEMENT", got
    assert got["refreshMs"] == 2000 and got["intervals"] == [2000], got
    lines = got["lines"]
    assert lines and all(len(line) <= 100 for line in lines), lines
    joined = "\n".join(lines)
    for needed in ("2 busy", "1 stalled", "9 idle", "12 staffed", "1 live lane", "L-0200", "12m"):
        assert needed in joined, (needed, lines)


def test_poll_command_reads_the_real_cli_with_a_bounded_timeout() -> None:
    got = drive(PAYLOAD)
    assert len(got["exec"]) == 1, got["exec"]
    call = got["exec"][0]
    assert call["file"] == "/abs/venv/bin/python", call
    assert call["args"] == [
        "scripts/teamwork.py",
        "status",
        "--json",
        "--project",
        "/project/root",
    ], call
    assert call["timeout"] == 4000 and call["maxBuffer"] == 4 << 20, call


def test_cleanup_stops_the_timer_unclaims_the_slot_and_clears_the_lines() -> None:
    got = drive(PAYLOAD)
    assert got["cleanup"] == {"cancelled": "handle", "unclaimed": True, "cleared": True}, got


def test_another_host_gets_no_widget() -> None:
    got = drive(PAYLOAD, host="pi")
    assert got["slots"] == [] and got["lines"] == [] and got["exec"] == [], got


def test_a_non_schema5_payload_draws_nothing() -> None:
    legacy = {**PAYLOAD, "schema": 4}
    got = drive(legacy)
    assert got["slots"] == [{"append": "home.footer.status", "hasRender": True}], got
    assert got["lines"] == [], got


def test_server_default_export_is_safe_without_a_ui_context() -> None:
    got = drive_server()
    assert got["id"] == "tw-status", got
    assert got["threw"] is None, got
    assert got["slots"] == [], got


def build(tmp_path: Path) -> Path:
    out = tmp_path / "dist"
    done = subprocess.run(
        [sys.executable, str(BUILD), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    return out / "@nidvue" / "teamwork"


def test_the_tui_plugin_ships_at_an_opencode_discoverable_path(tmp_path: Path) -> None:
    pkg = build(tmp_path)
    shipped = pkg / "plugins" / "tw-status"
    for name in ("index.ts", "tui.tsx", "package.json"):
        assert (shipped / name).is_file(), name
    manifest = json.loads((pkg / "package.json").read_text(encoding="utf-8"))
    assert manifest["exports"]["./tui"] == "./plugins/tw-status/tui.tsx", manifest["exports"]
    assert "plugins" in manifest["files"], manifest["files"]
    declared = [p for v in manifest["pi"].values() if isinstance(v, list) for p in v]
    assert all((pkg / p.lstrip("./")).exists() for p in declared), declared

    nested = json.loads((shipped / "package.json").read_text(encoding="utf-8"))
    assert nested["exports"]["./tui"] == "./tui.tsx", nested["exports"]
    assert nested["dependencies"] == {"@opencode/plugin": "2.3.0"}, nested["dependencies"]
    exact = re.compile(r"^\d+\.\d+\.\d+$")
    assert nested["peerDependencies"], "the JSX peers are declared"
    assert all(exact.match(version) for version in nested["peerDependencies"].values()), nested


def test_the_host_entry_uses_the_validated_v230_authoring_signature() -> None:
    source = TUI.read_text(encoding="utf-8")
    assert 'from "@opencode/plugin/tui"' in source, source[:200]
    assert "Plugin.define(" in source, "the TUI part is wrapped by Plugin.define"
    source = INDEX.read_text(encoding="utf-8")
    assert 'SLOT = "home.footer.status"' in source, "the core claims the status line"
    assert "sidebar.content" not in source and "session.panel" not in source, source
