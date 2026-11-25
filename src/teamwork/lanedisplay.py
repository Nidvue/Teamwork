"""The lane adapters: install the host extensions the bundle ships.

``swarm run`` starts every lane as a detached child process, so the session that
dispatched them sees nothing on its own screen: the team works, the display stays
empty, and no command says why. The picture is a separate one-way adapter - an
extension that polls ``status --json`` and draws the rows - and it ships inside
the bundle at ``extensions/tw-status.ts``. A second adapter,
``extensions/teamwork-bus.ts``, carries the push side: it registers the session's
bus address, injects pending mail and refuses a write another live session claims.

Shipping a file is not the same as loading it. A host reads extensions from its
own ``extensions/`` directory and from the ``extensions`` list in ``settings.json``,
never from a skills directory, so a skill-only install carries the adapters and
still draws nothing. That gap was measured on this project's own machine: 60 lane
runs on record, no widget, and a ``--check`` that reported the bundle as in sync.

So the install is a step, not a footnote, and it is the same step for every
adapter: :func:`install` copies every extension the bundle ships next to the
host's skills directory and registers each one in ``settings.json`` once,
idempotently; :func:`status` answers the same question without writing. Both are
safe on a host with neither directory: the protocol completes without an adapter
(``references/Adapters.md``), so a missing adapter is a lost picture or an
undelivered message, never a blocked lane.
"""

from __future__ import annotations

import filecmp
import json
import os
import shutil
from dataclasses import dataclass, replace
from pathlib import Path

HOST_DEFAULTS = {
    "pi": Path("~/.pi/agent/skills/tw"),
    "agents": Path("~/.agents/skills/tw"),
}

EXT_FILES = ("tw-status.ts", "teamwork-bus.ts")

EXT_NAME = EXT_FILES[0]

EXT_DIR = Path("extensions")

EXT_REL = EXT_DIR / EXT_NAME

BUNDLED = EXT_REL

RETIRED = ("teamwork-lanes.ts", "teamwork-status.ts")

SETTINGS_NAME = "settings.json"

SUPPORTED_HOSTS = frozenset(("pi", "opencode"))

OPENCODE_PLUGIN = Path("~/.config/opencode/plugins/tw-status")

OPENCODE_SOURCE = Path("plugins") / "tw-status"

OPENCODE_CONFIG_HINT = (
    "opencode: the sidebar plugin is auto-discovered at ~/.config/opencode/plugins/tw-status; "
    'if it does not load, add "file://<config>/plugins/tw-status" to the "plugins" array '
    "in ~/.config/opencode/opencode.jsonc (or cli.json for TUI-only plugins). "
    "This command never edits either file."
)


@dataclass(frozen=True)
class State:
    """What the host would load: ``ok`` says the question could be answered."""

    ok: bool
    installed: bool
    registered: bool
    target: Path | None
    settings: Path | None
    detail: str
    files: tuple[Path, ...] = ()
    missing: tuple[str, ...] = ()

    @property
    def live(self) -> bool:
        """Does the host load every adapter? Both halves are required."""
        return self.ok and self.installed and self.registered


def shipped(skill_dir: Path) -> tuple[Path, ...]:
    """The adapters a bundle carries, the known pair first, then any other file.

    A bundle is whatever is installed in the host: a checkout, a wheel, the skill
    directory itself. Reading the tuple from the bundle rather than from a
    constant keeps a bundle that carries one adapter installable on its own.
    """
    folder = skill_dir / EXT_DIR
    if not folder.is_dir():
        return ()
    found = {
        path.name: path
        for path in folder.glob("*.ts")
        if path.is_file() and path.name not in RETIRED
    }
    order = [name for name in EXT_FILES if name in found]
    order += sorted(name for name in found if name not in EXT_FILES)
    return tuple(found[name] for name in order)


def bundled(skill_dir: Path) -> Path:
    """The renderer inside a skill bundle or checkout."""
    files = shipped(skill_dir)
    return files[0] if files else skill_dir / BUNDLED


def _resolve_dest(host: str = "pi", skills: str = "") -> Path:
    target = Path(skills).expanduser() if skills else HOST_DEFAULTS.get(host, HOST_DEFAULTS["pi"])
    target = target.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    return target


def agent_dir(host: str = "pi", skills: str = "") -> Path | None:
    """The host's own directory, derived from where its skills live.

    ``<agent>/skills/<name>`` is the shape every host uses, so the extension
    directory is one level up from ``skills``. A ``--dest`` outside that shape
    (a scratch directory, a wheel) has no host to register with.
    """
    installed = _resolve_dest(host, skills)
    if installed.parent.name != "skills":
        return None
    return installed.parent.parent


def opencode_plugin_dir(skills: str = "") -> Path:
    """The OpenCode plugin package directory, from ``--dest`` when one is given.

    OpenCode auto-discovers immediate package directories under
    ``~/.config/opencode/plugins/`` (https://opencode.ai/docs/plugins/,
    accessed 2026-11-25). The directory itself is the install target; unlike pi
    there is no ``extensions/`` list to register in.
    """
    return Path(skills).expanduser() if skills else OPENCODE_PLUGIN.expanduser()


def opencode_base(skills: str = "") -> Path:
    """The config directory whose existence makes an opencode install possible."""
    plugin = opencode_plugin_dir(skills)
    return plugin.parent.parent if plugin.parent.name == "plugins" else plugin.parent


def opencode_sources(skill_dir: Path) -> tuple[Path, ...]:
    """Every file the bundle ships for the opencode sidebar plugin."""
    folder = skill_dir / OPENCODE_SOURCE
    if not folder.is_dir():
        return ()
    return tuple(sorted(path for path in folder.iterdir() if path.is_file()))


def _missing(skill_dir: Path) -> str:
    """Why the bundle cannot hand an adapter over, in the caller's terms.

    A built host package is the one layout that ships the extension beside the
    skill instead of inside it (``<package>/extensions``, declared in the package
    manifest), so its host loads the file without anything being installed here.
    """
    detail = f"the bundle carries no {BUNDLED.as_posix()}"
    if (skill_dir.parent.parent / EXT_REL).is_file():
        detail += "; a built host package declares that file itself, so the host loads it"
    return detail


def _load(path: Path) -> dict[str, object] | None:
    """The settings object, ``{}`` when the file does not exist, ``None`` when broken."""
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def listed(settings: dict[str, object]) -> set[str]:
    """The adapter file names the settings file already lists, in any spelling."""
    entries = settings.get("extensions")
    if not isinstance(entries, list):
        return set()
    return {Path(str(entry)).name for entry in entries}


def registered(settings: dict[str, object], names: tuple[str, ...] = ()) -> bool:
    """Is every adapter of ``names`` (default: the known pair) already listed?"""
    wanted = names or EXT_FILES
    have = listed(settings)
    return bool(wanted) and all(name in have for name in wanted)


def _current(target_dir: Path, source: Path) -> bool:
    """Is the host's copy of one adapter byte-identical to the bundle's?"""
    target = target_dir / source.name
    return target.is_file() and filecmp.cmp(source, target, shallow=False)


def status(skill_dir: Path, *, host: str = "pi", skills: str = "") -> State:
    """Report the installed files and the settings entries without writing anything.

    ``skill_dir`` is the bundle that carries the adapters (a checkout, a wheel, the
    installed skill itself); ``skills`` is where the host keeps that bundle, and
    only it can say which agent directory the extensions belong in.
    """
    if host == "opencode":
        return opencode_status(skill_dir, skills)
    target_dir = agent_dir(host, skills)
    if target_dir is None:
        return State(False, False, False, None, None, f"host {host!r} has no extensions directory")
    sources = shipped(skill_dir)
    if not sources:
        return State(False, False, False, None, None, _missing(skill_dir))
    target = target_dir / EXT_DIR / sources[0].name
    settings_path = target_dir / SETTINGS_NAME
    settings = _load(settings_path)
    if settings is None:
        return State(
            False, False, False, target, settings_path, f"{settings_path} is not valid JSON"
        )
    have = listed(settings)
    stale = tuple(source.name for source in sources if not _current(target_dir / EXT_DIR, source))
    unlisted = tuple(source.name for source in sources if source.name not in have)
    missing = tuple(dict.fromkeys(stale + unlisted))
    return State(
        True,
        not stale,
        not unlisted,
        target,
        settings_path,
        "",
        tuple(target_dir / EXT_DIR / source.name for source in sources),
        missing,
    )


def retire(directory: Path, settings: dict[str, object]) -> bool:
    """Drop the adapters this file replaced, so the host loads exactly one.

    A host that already installed the lanes-only renderer would otherwise draw two
    widgets for the same team, which is the defect this file exists to close.
    """
    entries = settings.get("extensions")
    kept = entries if isinstance(entries, list) else None
    removed = False
    for name in RETIRED:
        stale = directory / name
        if stale.is_file():
            stale.unlink()
            removed = True
    if kept is not None:
        surviving = [entry for entry in kept if Path(str(entry)).name not in RETIRED]
        if surviving != kept:
            settings["extensions"] = surviving
            removed = True
    return removed


def install(skill_dir: Path, *, host: str = "pi", skills: str = "", dry_run: bool = False) -> State:
    """Copy every shipped adapter into the host's directory and register each once."""
    if host == "opencode":
        return opencode_install(skill_dir, skills=skills, dry_run=dry_run)
    state = status(skill_dir, host=host, skills=skills)
    if not state.ok or state.target is None or state.settings is None:
        return state
    settings = _load(state.settings) or {}
    retired = retire(state.target.parent, settings)
    sources = shipped(skill_dir)
    folder = state.target.parent
    pending = [
        source
        for source in sources
        if source.name not in listed(settings) or not _current(folder, source)
    ]
    if not (retired or pending):
        return state
    if dry_run:
        return replace(state, detail="would install")
    folder.mkdir(parents=True, exist_ok=True)
    for source in sources:
        if not _current(folder, source):
            shutil.copy2(source, folder / source.name)
    entries = settings.get("extensions")
    listed_entries = list(entries) if isinstance(entries, list) else []
    names = {Path(str(entry)).name for entry in listed_entries}
    for source in sources:
        if source.name not in names:
            listed_entries.append((EXT_DIR / source.name).as_posix())
    settings["extensions"] = listed_entries
    state.settings.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return replace(state, installed=True, registered=True, detail="")


def opencode_status(skill_dir: Path, skills: str = "") -> State:
    """Report the sidebar plugin files OpenCode would discover, without writing."""
    target = opencode_plugin_dir(skills)
    sources = opencode_sources(skill_dir)
    if not sources:
        return State(
            False, False, False, target, None, f"the bundle carries no {OPENCODE_SOURCE.as_posix()}"
        )
    stale = tuple(source.name for source in sources if not _current(target, source))
    return State(
        True,
        not stale,
        True,
        target / sources[0].name,
        None,
        "",
        tuple(target / source.name for source in sources),
        stale,
    )


def opencode_install(skill_dir: Path, *, skills: str = "", dry_run: bool = False) -> State:
    """Copy the bundled sidebar plugin into OpenCode's discovery directory."""
    state = opencode_status(skill_dir, skills)
    if not state.ok:
        return state
    target = opencode_plugin_dir(skills)
    sources = opencode_sources(skill_dir)
    if not any(not _current(target, source) for source in sources):
        return state
    if dry_run:
        return replace(state, detail="would install")
    target.mkdir(parents=True, exist_ok=True)
    for source in sources:
        if not _current(target, source):
            shutil.copy2(source, target / source.name)
    return replace(state, installed=True, registered=True)


OFF = {"off", "0", "no", "false"}


def ensure(skill_dir: Path, *, host: str = "", skills: str = "") -> str:
    """Draw the wave on the running host unless the caller opted out - one line back.

    The skill is bootstrapped by ``init``, so that is where a default belongs: an
    operator who installs the skill on a supported host gets the picture without
    reading a section about adapters. ``host`` is the running host, supplied by
    the caller from ``detect_agent_host()``; only pi and opencode draw, and every
    other host is skipped with no writes. Never raises - a bootstrap step that
    can fail the workspace is worse than one that says why it was skipped - and
    it writes nothing when the host has no agent directory, when ``CI`` is set,
    or when ``TEAMWORK_UI=off``.
    """
    if (os.environ.get("TEAMWORK_UI") or "").strip().lower() in OFF:
        return "lane display: skipped (TEAMWORK_UI=off)"
    if os.environ.get("CI"):
        return "lane display: skipped (a CI run is not the operator's host)"
    if host and host not in SUPPORTED_HOSTS:
        return f"lane display: skipped (running host {host!r} has no display)"
    try:
        directory = opencode_base(skills) if host == "opencode" else agent_dir(host, skills)
        if directory is None or not directory.is_dir():
            return "lane display: skipped (no agent directory to draw in)"
        state = status(skill_dir, host=host, skills=skills)
        if state.live:
            return f"lane display: already drawn from {state.target}"
        if not state.ok:
            return f"lane display: not drawn - {state.detail}"
        drawn = install(skill_dir, host=host, skills=skills)
    except (RuntimeError, OSError) as exc:
        return f"lane display: skipped (this host cannot name its home directory: {exc})"
    if not drawn.live:
        return f"lane display: not drawn - {drawn.detail or drawn.settings}"
    ui = "the OpenCode status line" if host == "opencode" else "the pi UI"
    return f"lane display: installed and registered at {drawn.target} - {ui} draws the wave"
