"""The lane display: install the host extension that draws the live wave.

``swarm run`` starts every lane as a detached child process, so the session that
dispatched them sees nothing on its own screen: the team works, the display stays
empty, and no command says why. The picture is a separate one-way adapter - an
extension that polls ``status --json`` and draws the rows - and it ships inside
the bundle at ``extensions/teamwork-status.ts``.

Shipping the file is not the same as loading it. A host reads extensions from its
own ``extensions/`` directory and from the ``extensions`` list in ``settings.json``,
never from a skills directory, so a skill-only install carries the renderer and
still draws nothing. That gap was measured on this project's own machine: 60 lane
runs on record, no widget, and a ``--check`` that reported the bundle as in sync.

So the install is a step, not a footnote. :func:`install` copies the shipped file
next to the host's skills directory and registers it in ``settings.json`` once,
idempotently; :func:`status` answers the same question without writing. Both are
safe on a host with neither directory: the protocol completes without a display
(``references/Adapters.md``), so a missing renderer is a lost picture, never a
blocked lane.
"""

from __future__ import annotations

import filecmp
import json
import os
import shutil
from dataclasses import dataclass, replace
from pathlib import Path

from . import bundle

EXT_NAME = "teamwork-status.ts"

EXT_REL = Path("extensions") / EXT_NAME

BUNDLED = EXT_REL

RETIRED = ("teamwork-lanes.ts",)

SETTINGS_NAME = "settings.json"


@dataclass(frozen=True)
class State:
    """What the host would load: ``ok`` says the question could be answered."""

    ok: bool
    installed: bool
    registered: bool
    target: Path | None
    settings: Path | None
    detail: str

    @property
    def live(self) -> bool:
        """Does the host draw the wave? Both halves are required."""
        return self.ok and self.installed and self.registered


def bundled(skill_dir: Path) -> Path:
    """The renderer inside a skill bundle or checkout."""
    return skill_dir / BUNDLED


def agent_dir(host: str = "pi", skills: str = "") -> Path | None:
    """The host's own directory, derived from where its skills live.

    ``<agent>/skills/<name>`` is the shape every host uses, so the extension
    directory is one level up from ``skills``. A ``--dest`` outside that shape
    (a scratch directory, a wheel) has no host to register with.
    """
    installed = bundle.resolve_dest(host, skills)
    if installed.parent.name != "skills":
        return None
    return installed.parent.parent


def _missing(skill_dir: Path) -> str:
    """Why the bundle cannot hand the renderer over, in the caller's terms.

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


def registered(settings: dict[str, object]) -> bool:
    """Is the renderer already listed? Any spelling of the same file counts."""
    entries = settings.get("extensions")
    if not isinstance(entries, list):
        return False
    return any(Path(str(entry)).name == EXT_NAME for entry in entries)


def status(skill_dir: Path, *, host: str = "pi", skills: str = "") -> State:
    """Report the installed file and the settings entry without writing anything.

    ``skill_dir`` is the bundle that carries the renderer (a checkout, a wheel, the
    installed skill itself); ``skills`` is where the host keeps that bundle, and
    only it can say which agent directory the extension belongs in.
    """
    source = bundled(skill_dir)
    target_dir = agent_dir(host, skills)
    if target_dir is None:
        return State(False, False, False, None, None, f"host {host!r} has no extensions directory")
    if not source.is_file():
        return State(False, False, False, None, None, _missing(skill_dir))
    target = target_dir / EXT_REL
    settings_path = target_dir / SETTINGS_NAME
    settings = _load(settings_path)
    if settings is None:
        return State(
            False, False, False, target, settings_path, f"{settings_path} is not valid JSON"
        )
    same = target.is_file() and filecmp.cmp(source, target, shallow=False)
    return State(True, same, registered(settings), target, settings_path, "")


def retire(directory: Path, settings: dict[str, object]) -> bool:
    """Drop the renderers this file replaced, so the host loads exactly one.

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
    """Copy the shipped renderer into the host's directory and register it once."""
    state = status(skill_dir, host=host, skills=skills)
    if not state.ok or state.target is None or state.settings is None:
        return state
    settings = _load(state.settings) or {}
    retired = retire(state.target.parent, settings)
    needed = retired or not (state.installed and state.registered)
    if not needed:
        return state
    if dry_run:
        return replace(state, detail="would install")
    if not state.installed:
        state.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundled(skill_dir), state.target)
    if not state.registered:
        entries = settings.get("extensions")
        listed = list(entries) if isinstance(entries, list) else []
        listed.append(EXT_REL.as_posix())
        settings["extensions"] = listed
    state.settings.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return replace(state, installed=True, registered=True)


OFF = {"off", "0", "no", "false"}


def ensure(skill_dir: Path, *, host: str = "pi", skills: str = "") -> str:
    """Draw the wave on this host unless the caller opted out - one line back.

    The skill is bootstrapped by ``init``, so that is where a default belongs: an
    operator who installs the skill in pi gets the picture without reading a
    section about extensions. Never raises - a bootstrap step that can fail the
    workspace is worse than one that says why it was skipped - and it writes
    nothing when the host has no agent directory, when ``CI`` is set, or when
    ``TEAMWORK_UI=off``.
    """
    if (os.environ.get("TEAMWORK_UI") or "").strip().lower() in OFF:
        return "lane display: skipped (TEAMWORK_UI=off)"
    if os.environ.get("CI"):
        return "lane display: skipped (a CI run is not the operator's host)"
    try:
        directory = agent_dir(host, skills)
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
    return f"lane display: installed and registered at {drawn.target} - the pi UI draws the wave"
