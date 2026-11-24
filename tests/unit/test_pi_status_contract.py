"""AC-D1/D2/D3/D5 of the panel contract, proven against a real status payload.

Why this file exists: test_pi_status_render.py proves the renderer's arithmetic on
fixtures it builds itself. It cannot prove AC-D1 (every drawn element has a source
field in the real payload), AC-D2 on a real payload, AC-D3 measured in terminal
cells by pi-tui's visibleWidth (Python len counts characters, so a wide glyph hides
a one-cell overflow), or AC-D5 (silent with no team tree, no hard-coded colour).
Those four are what this file asserts, each against `teamwork.py status --json`.

Node is a host tool, not a test dependency: without it the tests skip with the
reason. pi-tui is resolved from the pi install that loads the extension, so the
width measurement is the one the terminal will apply.
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
EXTENSION = ROOT / "extensions" / "tw-status.ts"
ENGINE = ROOT / "scripts" / "teamwork.py"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
KEY = "tw-status"

RENDER_SCRIPT = """
const mod = await import(process.env.TW_EXTENSION);
const payload = JSON.parse(process.env.TW_PAYLOAD);
const width = Number(process.env.TW_WIDTH || 0);
const paint = process.env.TW_PAINT
  ? { fg: (token, text) => `\\u001b[3${token === "success" ? 2 : token === "warning" ? 3 : 1}m${text}\\u001b[0m` }
  : undefined;
let lines;
try {
  lines = width ? mod.render(payload, width, paint) : mod.render(payload, undefined, paint);
} catch (error) {
  console.log(JSON.stringify({ error: String(error && error.message) }));
  process.exit(0);
}
console.log(JSON.stringify({ lines }));
"""

WIDTH_SCRIPT = """
const mod = await import(process.env.TW_EXTENSION);
const tui = await import(process.env.TW_TUI);
const payload = JSON.parse(process.env.TW_PAYLOAD);
const width = Number(process.env.TW_WIDTH);
const paint = process.env.TW_PAINT
  ? { fg: (token, text) => `\\u001b[3${token === "success" ? 2 : token === "warning" ? 3 : 1}m${text}\\u001b[0m` }
  : undefined;
const lines = mod.render(payload, width, paint);
const taskAt = lines.map((line) => {
  const at = line.indexOf("T-0001");
  return at < 0 ? -1 : tui.visibleWidth(line.slice(0, at));
});
console.log(JSON.stringify({ widths: lines.map((line) => tui.visibleWidth(line)), taskAt, lines }));
"""

SILENT_SCRIPT = """
const mod = await import(process.env.TW_EXTENSION);
const handlers = new Map();
const calls = [];
const pi = { on: (name, fn) => handlers.set(name, fn), registerCommand: () => {} };
mod.default(pi);
const ctx = {
  cwd: process.env.TW_CWD,
  ui: {
    setWidget: (key, lines) => calls.push(["widget", key, lines]),
    setStatus: (key, value) => calls.push(["status", key, value]),
    notify: () => {},
  },
};
let threw = null;
try {
  await handlers.get("session_start")({}, ctx);
  await handlers.get("session_shutdown")({}, ctx);
} catch (error) {
  threw = String(error && error.message);
}
console.log(JSON.stringify({ calls, threw }));
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


def pi_tui() -> Path:
    candidates = [
        os.environ.get("TEAMWORK_PI_TUI"),
        str(
            Path.home()
            / ".local/lib/node_modules/@earendil-works/pi-coding-agent/node_modules"
            / "@earendil-works/pi-tui/dist/index.js"
        ),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    pytest.skip("pi-tui is not installed, so the cell width cannot be measured with it")


def execute(script: str, env: dict) -> dict:
    result = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={
            **os.environ,
            "TEAMWORK_AGENT_HOST": "pi",
            "TW_EXTENSION": EXTENSION.as_uri(),
            **env,
        },
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert "error" not in body, body["error"]
    return body


def render(payload: dict, width: int | None = None, paint: bool = False) -> list[str]:
    return execute(
        RENDER_SCRIPT,
        {
            "TW_PAYLOAD": json.dumps(payload),
            "TW_WIDTH": str(width or ""),
            "TW_PAINT": "1" if paint else "",
        },
    )["lines"]


def real_payload(tmp_path: Path) -> dict:
    """A payload the shipped engine produced, in a throwaway team tree."""
    project = tmp_path / "Project"
    python = sys.executable
    for command in (
        [python, str(ENGINE), "--project", str(project), "init"],
        [python, str(ENGINE), "--project", str(project), "instance", "add", "developer"],
        [
            python,
            str(ENGINE),
            "--project",
            str(project),
            "task",
            "add",
            "developer",
            "--goal",
            "panel contract probe",
            "--deliverable",
            "a claimed row",
        ],
    ):
        subprocess.run(command, capture_output=True, text=True, timeout=120)
    listed = subprocess.run(
        [python, str(ENGINE), "--project", str(project), "status", "--json"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert listed.returncode == 0, listed.stderr
    payload = json.loads(listed.stdout)
    assert payload["instances"], "the engine printed no instance row to render"
    return payload


def busy(payload: dict, **extra) -> dict:
    """One real row, drawn as busy so the row body is exercised."""
    row = dict(payload["instances"][0])
    row.update(
        {
            "state": "busy",
            "stalled": False,
            "task": "T-0001",
            "title": "a real title",
            "elapsed_seconds": 300,
            "elapsed_text": "5m00s",
            "remaining_seconds": 900,
            "remaining_text": "15m00s",
            "activity": "lane started L-0141",
            "last": "lane.start L-0141",
            "last_seconds": 12,
            "model": "deepinfra/deepseek-v4",
        }
    )
    row.update(extra)
    return row


DRAWN = {
    "instance": "instance",
    "task": "task",
    "state": "state",
    "used clock": "elapsed_seconds",
    "left clock": "remaining_seconds",
    "activity": "activity",
    "age": "last_seconds",
    "model": "model",
}


def test_every_drawn_element_has_a_source_field_in_the_real_payload(tmp_path: Path) -> None:
    payload = real_payload(tmp_path)
    for row in payload["instances"]:
        for element, field in DRAWN.items():
            assert field in row, (
                f"the renderer draws {element} from {field}, which the payload lacks"
            )
    lines = render({**payload, "instances": [busy(payload)]}, 100)
    body = [line for line in lines if line.startswith("●")]
    assert body, lines
    assert "T-0001" in body[0] and "lane started" in body[0], body[0]
    titled = render({**payload, "instances": [busy(payload, activity=None, last=None)]}, 100)[1]
    assert "a real title" in titled, titled


def test_a_drawn_element_disappears_when_its_source_field_does(tmp_path: Path) -> None:
    payload = real_payload(tmp_path)
    render({**payload, "instances": [busy(payload)]}, 100)
    cases = [
        ({"task": None}, "T-0001"),
        ({"activity": None, "last": None, "title": None}, "lane started"),
        ({"elapsed_seconds": None, "elapsed_text": None}, "5m00s"),
        ({"remaining_seconds": None, "remaining_text": None}, "15m"),
        ({"model": None}, "deepseek-v4"),
        ({"instance": None}, busy(payload)["instance"]),
    ]
    for dropped, drawn in cases:
        line = render({**payload, "instances": [busy(payload, **dropped)]}, 100)[1]
        assert drawn not in line, f"{drawn!r} is drawn with {dropped} absent: {line}"


def test_the_real_payload_stays_bounded_and_the_hidden_count_is_exact(tmp_path: Path) -> None:
    payload = real_payload(tmp_path)
    rows = [busy(payload, instance=f"Developer-{index + 1}") for index in range(21)]
    lines = render({**payload, "instances": rows}, 100)
    assert len(lines) <= 12, lines
    shown = len([line for line in lines if line.startswith("●")])
    hidden = [line for line in lines if line.endswith("more busy")]
    assert len(hidden) == 1, lines
    assert int(re.match(r"^\+(\d+) more busy$", hidden[0]).group(1)) == 21 - shown, lines
    assert len(lines) == 12 and shown + 21 - shown == 21


def test_every_line_fits_the_width_in_cells_including_ansi_and_wide_glyphs(
    tmp_path: Path,
) -> None:
    payload = real_payload(tmp_path)
    rows = [
        busy(payload, instance="ReleaseEngineer", activity="lane started L-0141"),
        busy(payload, instance="开发团队", activity="运行中 lane started L-0142"),
        busy(payload, instance="Developer", activity="a wide 活動報告 activity line"),
    ]
    tui = pi_tui()
    for width in (40, 80, 120):
        for paint in (False, True):
            body = execute(
                WIDTH_SCRIPT,
                {
                    "TW_PAYLOAD": json.dumps({**payload, "instances": rows}),
                    "TW_WIDTH": str(width),
                    "TW_TUI": tui.as_uri(),
                    "TW_PAINT": "1" if paint else "",
                },
            )
            for line, cells in zip(body["lines"], body["widths"], strict=True):
                assert cells <= width, (width, paint, cells, line)
                if not paint:
                    assert ANSI.search(line) is None, (width, line)
            drawn = [at for at in body["taskAt"] if at >= 0]
            assert len(drawn) == len(rows), body["lines"]
            assert len(set(drawn)) == 1, (width, paint, drawn, body["lines"])


def test_no_colour_is_hard_coded_in_the_renderer() -> None:
    source = EXTENSION.read_text(encoding="utf-8")
    assert "\\u001b" not in source and "\\x1b" not in source, (
        "the renderer emits no escape of its own"
    )
    assert not ANSI.search(source), "no literal ANSI sequence in the source"
    for token in re.findall(r"COLOUR: Record<string, string> = \{([^}]*)\}", source):
        names = set(re.findall(r'"([a-z]+)"', token))
        assert names == {"success", "warning", "error"}, names


def test_the_panel_is_silent_with_no_team_tree(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    body = execute(SILENT_SCRIPT, {"TW_CWD": str(empty)})
    assert body["threw"] is None, body["threw"]
    assert ["widget", KEY, []] in body["calls"], body["calls"]
    assert ["status", KEY, ""] in body["calls"], body["calls"]


def test_a_partial_payload_never_throws(tmp_path: Path) -> None:
    payload = real_payload(tmp_path)
    row = busy(payload)
    for missing in (
        "activity",
        "last",
        "title",
        "elapsed_text",
        "elapsed_seconds",
        "remaining_seconds",
        "model",
        "last_seconds",
    ):
        row.pop(missing, None)
    partials = [
        {"instances": [row]},
        {"instances": [{"instance": "Developer"}]},
        {"instances": [{}], "counts": {}},
        {"instances": [row], "counts": None},
    ]
    for partial in partials:
        lines = render(partial, 100)
        assert lines and "undefined" not in "\n".join(lines), (partial, lines)
        assert "NaN" not in "\n".join(lines), (partial, lines)
    assert render({}) == []
    assert render({"instances": [], "lanes": []}) == []
