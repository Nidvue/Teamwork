"""Why these tests exist: the published pi package is built, not hand-edited, and
three review rounds found the same class of defect - metadata that did not match
the shipped tree (an Apache licence over AGPL code, a `files` list naming
directories the tarball never contained, notices silently dropped by npm, and the
pi layer shipped twice).

Pinned here: the built manifest carries the repository's licence, every declared
path exists, npm's `files` list covers what the tarball needs, the host-provided
packages stay peers, and the pi adapter tree is not duplicated inside the portable
skill.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "scripts" / "build_pi_package.py"


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


def test_manifest_matches_the_shipped_tree(tmp_path: Path) -> None:
    pkg = build(tmp_path)
    manifest = json.loads((pkg / "package.json").read_text(encoding="utf-8"))

    assert manifest["name"] == "@nidvue/teamwork", "the master brand owns the npm scope"
    assert "pi-package" in manifest["keywords"], "the gallery discovers pi-package only"
    assert manifest["license"] == "AGPL-3.0-or-later", "LICENSE is AGPL v3"
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (pkg / "LICENSE").read_text(encoding="utf-8")

    # every resource the pi manifest declares must exist in the tarball
    for paths in manifest["pi"].values():
        if not isinstance(paths, list):
            continue  # pi.image is a URL, not a path
        for pattern in paths:
            assert (pkg / pattern.lstrip("./")).exists(), pattern

    # npm drops anything not named in `files`, including the notices
    for needed in ("README.md", "LICENSE", "NOTICE", "CHANGELOG.md", "SECURITY.md"):
        assert needed in manifest["files"], needed
        assert (pkg / needed).exists(), needed

    # the gallery card is the description, and every link must reach the repo
    assert "Nidvue Teamwork" in manifest["description"]
    assert len(manifest["description"]) <= 256, "npm truncates the gallery card"
    assert manifest["homepage"] == "https://github.com/Nidvue/Teamwork"
    assert manifest["repository"]["url"].endswith("github.com/Nidvue/Teamwork.git")
    assert manifest["bugs"]["url"].endswith("/issues")
    assert manifest["pi"]["image"].startswith("https://")

    # host packages are peer-only: a physical copy duplicates pi's module registry
    for host in (
        "@earendil-works/pi-ai",
        "@earendil-works/pi-agent-core",
        "@earendil-works/pi-coding-agent",
        "@earendil-works/pi-tui",
    ):
        assert host in manifest["peerDependencies"], host
        assert host not in manifest.get("dependencies", {}), host


def test_the_pi_layer_is_not_shipped_twice(tmp_path: Path) -> None:
    pkg = build(tmp_path)
    adapter = pkg / "skills" / "teamwork-pi" / "SKILL.md"
    assert adapter.is_file()
    duplicates = [p for p in (pkg / "skills" / "teamwork").rglob("teamwork-pi") if p.is_dir()]
    assert not duplicates, duplicates
    # the portable skill must stay host-neutral; the pi names live in the adapter
    portable = (pkg / "skills" / "teamwork" / "SKILL.md").read_text(encoding="utf-8")
    for tool in ("subagent(", "schedule.create"):
        assert tool not in portable, tool


def test_engine_and_skill_are_runnable_from_the_tarball(tmp_path: Path) -> None:
    """A pi package with no node dependency must still run the engine it ships."""
    pkg = build(tmp_path)
    engine = pkg / "skills" / "teamwork" / "scripts" / "teamwork.py"
    assert engine.is_file()
    done = subprocess.run(
        [sys.executable, str(engine), "--version"], capture_output=True, text=True
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().startswith("teamwork "), done.stdout
