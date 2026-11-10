"""Why these tests exist: the published pi package is built, not hand-edited, and
three review rounds found the same class of defect - metadata that did not match
the shipped tree (an Apache licence over AGPL code, a `files` list naming
directories the tarball never contained, notices silently dropped by npm, and the
pi layer shipped twice).

Pinned here: the built manifest carries the repository's licence, every declared
path exists, npm's `files` list covers what the tarball needs, the host-provided
packages stay peers, the pi adapter tree is not duplicated inside the portable
skill, and the command line answers `--help` without assembling a package.
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


# --------------------------------------------------------------------------- #
# The command line: asking what this script does must never build anything
# --------------------------------------------------------------------------- #


def dist_entries() -> set[str]:
    """Everything the default output directory holds, recursively."""
    dist = ROOT / "dist"
    return {str(p.relative_to(dist)) for p in dist.rglob("*")} if dist.is_dir() else set()


def run_script(*argv: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BUILD), *argv], cwd=str(cwd), capture_output=True, text=True
    )


def test_help_exits_zero_before_touching_the_filesystem(tmp_path: Path) -> None:
    """The CI probe runs every workflow script with ``--help`` and must create nothing.

    The hand-rolled argv scan looked for a literal ``--out`` and otherwise fell
    through to a full build, so the probe assembled a real package into
    ``dist/@nidvue/teamwork`` - residue ``release.yml`` had to delete before it
    could publish.
    """
    before = dist_entries()
    done = run_script("--help", cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    assert "--out" in done.stdout, "the help text does not document the only flag"
    assert dist_entries() == before, "`--help` assembled a package into dist/"
    assert list(tmp_path.iterdir()) == [], "`--help` wrote into the working directory"


def test_a_flag_without_its_value_is_a_usage_error_not_a_traceback(tmp_path: Path) -> None:
    """``--out`` with no value raised ``IndexError`` from ``argv.index(...) + 1``."""
    done = run_script("--out", cwd=tmp_path)
    assert done.returncode == 2, (done.returncode, done.stderr)
    assert done.stderr.startswith("usage:"), done.stderr
    assert "Traceback" not in done.stderr
    assert list(tmp_path.iterdir()) == []


def test_an_unknown_flag_is_refused_before_anything_is_built(tmp_path: Path) -> None:
    before = dist_entries()
    done = run_script("--nonesuch", cwd=tmp_path)
    assert done.returncode == 2, (done.returncode, done.stderr)
    assert "unrecognized arguments: --nonesuch" in done.stderr, done.stderr
    assert dist_entries() == before, "an unknown flag still built a package"
