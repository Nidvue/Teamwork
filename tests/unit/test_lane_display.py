"""The lane display must be loaded, not merely shipped (T-0065).

Why: the renderer that draws the live wave ships inside the bundle, and a
skill-only install therefore *carries* it while the host never loads it - a host
reads extensions from its own ``extensions/`` directory and its ``settings.json``,
never from a skills directory. The gap is silent: 60 lane runs on record, no
widget, and a skill-install check that only compared bundle bytes.

Pinned here: the install copies the shipped file and registers it once, the
settings file keeps every other key, a second run changes nothing, a broken
settings file is left untouched rather than rewritten, and a destination outside
the host's ``<agent>/skills/<name>`` shape is reported as having no display
instead of writing into a stranger's directory.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from teamwork import lanedisplay, messages

RENDERER = Path("extensions") / "tw-status.ts"

BUS = Path("extensions") / "teamwork-bus.ts"


def skill(tmp_path: Path) -> Path:
    """A bundle that carries the renderer and nothing else."""
    root = tmp_path / "bundle"
    target = root / RENDERER
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("export default function () {}\n", encoding="utf-8")
    return root


def host(tmp_path: Path) -> Path:
    """The host shape the agent directory is derived from."""
    return tmp_path / "agent" / "skills" / "tw"


def test_the_repository_ships_the_renderer() -> None:
    shipped = Path(__file__).resolve().parents[2] / RENDERER
    text = shipped.read_text(encoding="utf-8")
    assert "status" in text and "--json" in text, "the renderer polls the status feed"
    assert "setWidget" in text, "a renderer that draws nothing is not a renderer"


def test_install_copies_the_renderer_and_registers_it_once(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    settings.write_text(
        json.dumps({"theme": "dark", "extensions": ["extensions/other.ts"]}, indent=2) + "\n",
        encoding="utf-8",
    )

    state = lanedisplay.install(skill(tmp_path), skills=str(dest))

    assert state.ok and state.live, state.detail
    assert state.target is not None and state.target.is_file()
    assert state.target.read_text(encoding="utf-8") == "export default function () {}\n"
    written = json.loads(settings.read_text(encoding="utf-8"))
    assert written["theme"] == "dark", "an unrelated setting is never dropped"
    assert written["extensions"] == ["extensions/other.ts", "extensions/tw-status.ts"]

    again = lanedisplay.install(skill(tmp_path), skills=str(dest))
    assert again.live
    assert json.loads(settings.read_text(encoding="utf-8"))["extensions"] == [
        "extensions/other.ts",
        "extensions/tw-status.ts",
    ], "a second install must not append the entry twice"


def test_a_settings_entry_in_another_spelling_is_already_registered(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    settings.write_text(
        json.dumps({"extensions": ["/abs/path/extensions/tw-status.ts"]}),
        encoding="utf-8",
    )

    state = lanedisplay.install(skill(tmp_path), skills=str(dest))

    assert state.registered
    assert json.loads(settings.read_text(encoding="utf-8"))["extensions"] == [
        "/abs/path/extensions/tw-status.ts"
    ]


def test_status_reports_missing_before_the_install(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    state = lanedisplay.status(skill(tmp_path), skills=str(dest))

    assert state.ok, state.detail
    assert not state.installed and not state.registered and not state.live


def test_a_broken_settings_file_is_left_untouched(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    settings.write_text("{ not json", encoding="utf-8")

    state = lanedisplay.install(skill(tmp_path), skills=str(dest))

    assert not state.ok
    assert "not valid JSON" in state.detail
    assert settings.read_text(encoding="utf-8") == "{ not json"
    assert state.target is not None and not state.target.exists()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    state = lanedisplay.install(skill(tmp_path), skills=str(dest), dry_run=True)

    assert state.ok and not state.live
    assert state.target is not None and not state.target.exists()
    assert not (dest.parent.parent / "settings.json").exists()


def test_a_destination_outside_the_host_shape_has_no_display(tmp_path: Path) -> None:
    dest = tmp_path / "installed"
    dest.mkdir()

    state = lanedisplay.install(skill(tmp_path), skills=str(dest))

    assert not state.ok
    assert "no extensions directory" in state.detail
    assert not (tmp_path / "extensions").exists()


def test_the_cli_installs_and_then_reports_a_live_display(tmp_path: Path, cli, monkeypatch) -> None:
    monkeypatch.setenv("TEAMWORK_AGENT_HOST", "pi")
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    assert cli("ui", "status", "--dest", dest) == 1, "not installed yet"
    assert cli("ui", "install", "--dest", dest) == 0
    assert cli("ui", "status", "--dest", dest) == 0


@pytest.mark.parametrize("running_host", ["opencode", "claude", "unknown"])
def test_the_cli_refuses_install_outside_pi_without_writing(
    tmp_path: Path, cli, monkeypatch, capsys, running_host: str
) -> None:
    monkeypatch.setenv("TEAMWORK_AGENT_HOST", running_host)
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    settings.write_text('{"extensions": []}\n', encoding="utf-8")

    assert cli("ui", "install", "--dest", dest) == 1
    assert "pi" in capsys.readouterr().err
    assert not (dest.parent.parent / "extensions").exists()
    assert json.loads(settings.read_text(encoding="utf-8")) == {"extensions": []}


@pytest.mark.parametrize("running_host", ["opencode", "claude", "unknown"])
def test_ui_status_stays_read_only_outside_pi(
    tmp_path: Path, cli, monkeypatch, capsys, running_host: str
) -> None:
    monkeypatch.setenv("TEAMWORK_AGENT_HOST", running_host)
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    assert cli("ui", "status", "--dest", dest) == 1
    assert "lane display missing" in capsys.readouterr().out
    assert not (dest.parent.parent / "extensions").exists()
    assert not (dest.parent.parent / "settings.json").exists()


def test_the_cli_honours_the_explicit_host_override(tmp_path: Path, cli, monkeypatch) -> None:
    monkeypatch.setenv("TEAMWORK_AGENT_HOST", "pi")
    monkeypatch.setenv("OPENCODE_MODEL", "a-model")
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    assert cli("ui", "install", "--dest", dest) == 0
    assert (dest.parent.parent / "extensions" / "tw-status.ts").is_file()


def test_a_built_host_package_declares_its_own_extension(tmp_path: Path) -> None:
    """A package that ships ``extensions/`` beside ``skills/`` needs no install."""
    package = tmp_path / "package"
    skill_dir = package / "skills" / "tw"
    skill_dir.mkdir(parents=True)
    (package / "extensions").mkdir()
    (package / "extensions" / "tw-status.ts").write_text("x\n", encoding="utf-8")

    state = lanedisplay.status(skill_dir, skills=str(skill_dir))

    assert not state.ok
    assert "declares that file itself" in state.detail


def test_a_host_carrying_the_retired_renderer_is_cleaned_on_install(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    stale = dest.parent.parent / "extensions" / "teamwork-lanes.ts"
    stale.parent.mkdir(parents=True)
    stale.write_text("export default function () {}\n", encoding="utf-8")
    settings.write_text(
        json.dumps({"extensions": ["extensions/teamwork-lanes.ts"]}, indent=2) + "\n",
        encoding="utf-8",
    )

    state = lanedisplay.install(skill(tmp_path), skills=str(dest))

    assert state.live, state.detail
    assert not stale.exists(), "the host must load one renderer, not two"
    assert json.loads(settings.read_text(encoding="utf-8"))["extensions"] == [
        "extensions/tw-status.ts"
    ]


def test_the_tree_ships_exactly_one_teamwork_renderer() -> None:
    root = Path(__file__).resolve().parents[2]
    shipped = sorted(
        path.relative_to(root).as_posix()
        for path in root.glob("extensions/*.ts")
        if "setWidget" in path.read_text(encoding="utf-8")
    )
    assert shipped == ["extensions/tw-status.ts"], shipped
    assert not (root / "templates" / "pi-package" / "extensions").exists(), (
        "the second renderer tree is gone, not merely unloaded"
    )


def pair(tmp_path: Path) -> Path:
    """A bundle that carries both adapters, as the repository does."""
    root = tmp_path / "bundle"
    folder = root / "extensions"
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("tw-status.ts", "teamwork-bus.ts"):
        (folder / name).write_text("export default function () {}\n", encoding="utf-8")
    return root


def test_install_registers_every_shipped_adapter(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"

    state = lanedisplay.install(pair(tmp_path), skills=str(dest))

    assert state.ok and state.live, state.detail
    assert [path.name for path in state.files] == ["tw-status.ts", "teamwork-bus.ts"]
    written = json.loads(settings.read_text(encoding="utf-8"))
    assert written["extensions"] == [
        "extensions/tw-status.ts",
        "extensions/teamwork-bus.ts",
    ]

    again = lanedisplay.install(pair(tmp_path), skills=str(dest))
    assert again.live and again.missing == ()
    assert json.loads(settings.read_text(encoding="utf-8"))["extensions"] == written["extensions"]


def test_a_half_registered_pair_is_not_live(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    lanedisplay.install(pair(tmp_path), skills=str(dest))
    settings.write_text(json.dumps({"extensions": ["extensions/tw-status.ts"]}), encoding="utf-8")

    state = lanedisplay.status(pair(tmp_path), skills=str(dest))

    assert state.ok and not state.live
    assert not state.registered
    assert state.installed, "both files are on disk; only one is registered"
    assert state.missing == ("teamwork-bus.ts",), state.missing


def test_a_drifted_copy_is_reinstalled(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    lanedisplay.install(pair(tmp_path), skills=str(dest))
    target = dest.parent.parent / "extensions" / "teamwork-bus.ts"
    target.write_text("stale\n", encoding="utf-8")

    assert not lanedisplay.status(pair(tmp_path), skills=str(dest)).installed
    state = lanedisplay.install(pair(tmp_path), skills=str(dest))

    assert state.live
    assert target.read_text(encoding="utf-8") == "export default function () {}\n"


DRIVER = """
import assert from "node:assert";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.env.TW_ROOT;
const bus = process.env.TEAMWORK_BUS;
const session = "sess-1";
process.env.PI_SESSION_ID = session;
process.env.TEAMWORK_ROLE = "developer";
process.env.TEAMWORK_TEAM = "Teamwork";

const mod = await import(process.env.TW_EXTENSION);
const handlers = new Map();
const sent = [];
const pi = {
  on(name, handler) { handlers.set(name, handler); },
  sendMessage(message, options) { sent.push({ message, options }); },
  registerCommand() {},
  registerTool() {},
};
mod.default(pi);
const ctx = { cwd: root };
const checks = [];

const busKey = mod.busKey;
checks.push(["busKey is exported", typeof busKey === "function"]);
checks.push([
  "busKey matches the engine for every address",
  typeof busKey === "function" &&
    busKey("*") === "all" &&
    busKey("role:developer") === "role-developer" &&
    busKey(`session:${session}`) === "session-sess-1",
]);
const keys = typeof busKey === "function" ? ["*", "role:developer", `session:${session}`].map(busKey) : [];
checks.push(["no bus key carries an illegal path character", keys.length === 3 && keys.every((k) => !/[\\/:*?"<>|]/.test(k))]);
checks.push([
  "addresses names only the scopes the engine writes to the bus",
  JSON.stringify(mod.addresses({ TEAMWORK_TEAM: "Teamwork", TEAMWORK_ROLE: "developer", PI_SESSION_ID: session })) ===
    JSON.stringify(["team:Teamwork", `session:${session}`]),
]);

await handlers.get("session_start")({}, ctx);
checks.push(["session address", existsSync(join(bus, busKey(`session:${session}`)))]);

await handlers.get("before_agent_start")({}, ctx);
const mail = sent[0] || {};
const content = String((mail.message || {}).content || "");
checks.push(["one message", sent.length === 1]);
checks.push(["next turn", Boolean(mail.options && mail.options.deliverAs === "nextTurn")]);
checks.push(["mail id", content.includes("M-0001")]);
checks.push(["mail subject", content.includes("hello")]);
checks.push(["a colliding id in another folder is still read", content.includes("session-twin")]);
checks.push(["a fan-out address is not read from the bus", !content.includes("not-a-bus-scope")]);

await handlers.get("before_agent_start")({}, ctx);
await handlers.get("before_agent_start")({}, ctx);
checks.push(["no replay on turn 2 and 3", sent.length === 1]);
checks.push([
  "an address the engine fans out is never taken from the bus",
  JSON.parse(readFileSync(join(bus, busKey("*"), "M-0002.json"), "utf-8")).state === "pending",
]);

const blocked = await handlers.get("tool_call")(
  { toolName: "write", input: { path: join(root, "shared.ts") } }, ctx);
const reason = String((blocked || {}).reason || "");
checks.push(["claimed write blocked", Boolean(blocked && blocked.block === true)]);
checks.push(["names holder", reason.includes("Developer-9")]);
checks.push(["names claim", reason.includes("C-0007")]);

const free = await handlers.get("tool_call")(
  { toolName: "write", input: { path: join(root, "mine.ts") } }, ctx);
checks.push(["free path allowed", free === undefined]);

const expired = await handlers.get("tool_call")(
  { toolName: "edit", input: { path: join(root, "old.ts") } }, ctx);
checks.push(["expired claim allowed", expired === undefined]);

const own = await handlers.get("tool_call")(
  { toolName: "edit", input: { path: join(root, "own.ts") } }, ctx);
checks.push(["own claim allowed", own === undefined]);

const shell = await handlers.get("tool_call")(
  { toolName: "bash", input: { command: "rm shared.ts" } }, ctx);
checks.push(["non-write tool ignored", shell === undefined]);

const failed = checks.filter((pair) => !pair[1]);
console.log(JSON.stringify({ checks: checks.map((p) => `${p[0]}: ${p[1]}`), failed: failed.length }));
process.exit(failed.length ? 1 : 0);
"""


def test_the_shipped_bus_extension_drives_its_handlers(tmp_path: Path) -> None:
    """AC-BUS-4/5/6: drive session, mail and refusal through the shipped file, over
    the directory name the engine itself would write - so a key that drifts between
    the two halves, or a name a Windows filesystem refuses, fails here."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is a host tool, not a test dependency")
    extension = Path(__file__).resolve().parents[2] / BUS
    assert extension.is_file(), extension
    root = tmp_path / "repo"
    (root / ".pi").mkdir(parents=True)
    bus = tmp_path / "bus"
    team_bus = bus / messages.bus_key(*messages.parse_address("team:Teamwork"))
    team_bus.mkdir(parents=True)
    (team_bus / "M-0001.json").write_text(
        json.dumps(
            {
                "id": "M-0001",
                "from": "Developer-1",
                "subject": "hello",
                "priority": "high",
                "state": "pending",
                "created": "2026-11-17T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    session_bus = bus / messages.bus_key(*messages.parse_address("session:sess-1"))
    session_bus.mkdir(parents=True)
    (session_bus / "M-0001.json").write_text(
        json.dumps(
            {
                "id": "M-0001",
                "from": "Developer-1",
                "subject": "session-twin",
                "priority": "high",
                "state": "pending",
                "created": "2026-11-17T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (bus / "claims").mkdir()
    fan_out = bus / messages.bus_key(*messages.parse_address("*"))
    fan_out.mkdir(parents=True)
    (fan_out / "M-0002.json").write_text(
        json.dumps(
            {
                "id": "M-0002",
                "from": "CEO",
                "subject": "not-a-bus-scope",
                "priority": "high",
                "state": "pending",
                "created": "2026-11-17T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    future = "2099-01-01T00:00:00Z"
    for claim in (
        {
            "id": "C-0007",
            "path": "shared.ts",
            "by": "Developer-9",
            "session": "other",
            "expires": future,
        },
        {
            "id": "C-0008",
            "path": "old.ts",
            "by": "Developer-9",
            "session": "other",
            "expires": "2000-01-01T00:00:00Z",
        },
        {"id": "C-0009", "path": "own.ts", "by": "me", "session": "sess-1", "expires": future},
    ):
        record = {**claim, "root": str(root)}
        (bus / "claims" / f"{claim['id']}.json").write_text(json.dumps(record), encoding="utf-8")
    driver = tmp_path / "drive.mjs"
    driver.write_text(DRIVER, encoding="utf-8")

    run = subprocess.run(
        [node, "--experimental-strip-types", driver.name],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(tmp_path),
        env={
            **os.environ,
            "TW_EXTENSION": extension.as_uri(),
            "TW_ROOT": str(root),
            "TEAMWORK_BUS": str(bus),
            "TEAMWORK_ROOT": str(root),
        },
    )

    assert run.returncode == 0, run.stdout + run.stderr
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["failed"] == 0, report["checks"]


def test_ensure_installs_and_registers_on_pi(tmp_path: Path, monkeypatch) -> None:
    """On pi a host directory is drawn, and a second call is a no-op."""
    monkeypatch.delenv("TEAMWORK_UI", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("TEAMWORK_AGENT_HOST", "pi")
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    line = lanedisplay.ensure(skill(tmp_path), host="pi", skills=str(dest))

    assert "installed and registered" in line, line
    assert lanedisplay.status(skill(tmp_path), skills=str(dest)).live
    assert "already drawn" in lanedisplay.ensure(skill(tmp_path), host="pi", skills=str(dest))


@pytest.mark.parametrize("running_host", ["opencode", "claude", "unknown"])
def test_ensure_skips_without_writing_outside_pi(
    tmp_path: Path, monkeypatch, running_host: str
) -> None:
    """The live widget is pi-only: no extension file, no settings entry."""
    monkeypatch.delenv("TEAMWORK_UI", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("TEAMWORK_AGENT_HOST", running_host)
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    settings.write_text('{"extensions": [], "theme": "dark"}\n', encoding="utf-8")

    line = lanedisplay.ensure(skill(tmp_path), host=running_host, skills=str(dest))

    assert "skipped" in line and "not pi" in line, line
    assert not (dest.parent.parent / "extensions").exists()
    assert json.loads(settings.read_text(encoding="utf-8")) == {
        "extensions": [],
        "theme": "dark",
    }


def test_ensure_writes_nothing_when_the_caller_opts_out(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TEAMWORK_UI", "off")
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    line = lanedisplay.ensure(skill(tmp_path), skills=str(dest))

    assert "skipped" in line, line
    assert not (dest.parent.parent / "extensions").exists()


def test_ensure_writes_nothing_in_ci_or_without_a_host_directory(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("TEAMWORK_UI", raising=False)
    monkeypatch.setenv("CI", "true")
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    assert "CI run" in lanedisplay.ensure(skill(tmp_path), skills=str(dest))
    assert not (dest.parent.parent / "extensions").exists()

    monkeypatch.delenv("CI")
    absent = tmp_path / "nowhere" / "skills" / "tw"

    assert "no agent directory" in lanedisplay.ensure(skill(tmp_path), skills=str(absent))


def test_init_reports_the_lane_display_and_can_skip_it(tmp_path: Path, cli, capsys) -> None:
    project = tmp_path / "Project"
    project.mkdir()

    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    out = capsys.readouterr().out
    assert "lane display:" in out, out
    assert "TEAMWORK_UI=off" in out, out

    assert (
        cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git", "--no-ui") == 0
    )
    assert "lane display:" not in capsys.readouterr().out


def test_init_skips_the_display_outside_pi(tmp_path: Path, cli, capsys, monkeypatch) -> None:
    monkeypatch.delenv("TEAMWORK_UI", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("TEAMWORK_AGENT_HOST", "opencode")
    project = tmp_path / "Project"
    project.mkdir()

    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    out = capsys.readouterr().out
    assert "lane display:" in out and "not pi" in out, out


def test_ensure_never_raises_when_the_host_has_no_home(tmp_path: Path, monkeypatch) -> None:
    """A scrubbed environment is a skip, not a failed bootstrap (CI on Windows)."""
    monkeypatch.delenv("TEAMWORK_UI", raising=False)
    monkeypatch.delenv("CI", raising=False)

    def no_home(host: str = "pi", skills: str = "") -> Path:
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setattr(lanedisplay, "agent_dir", no_home)

    line = lanedisplay.ensure(skill(tmp_path), skills=str(host(tmp_path)))

    assert "cannot name its home directory" in line, line
