"""Why these tests exist: M22 shipped a memory index on every `load` and a built
pi package, and the layer matrix had no black-box acceptance check for either -
the unit layer pins the renderer internals and the manifest, which cannot show
that the shipped command output and the built tarball obey the contract. These
are the acceptance checks: they run the real CLI and the real build, and they
assert only what a user of the merged tree observes.
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


def main_checkout() -> Path:
    """The team store lives only in the main checkout (`.pi/` is gitignored), so a
    worktree run must measure the merged tree, not its own empty `.pi/`."""
    here = Path(__file__).resolve().parents[2]
    common = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"], cwd=here, capture_output=True, text=True
    ).stdout.strip()
    return (here / common).resolve().parent if common else here


ROOT = main_checkout()
BUILD = ROOT / "scripts" / "build_pi_package.py"
INDEX_CAP = 800
INDEX_LINES = 8
PACK_CAP = 4000


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "teamwork.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def index_block(out: str) -> list[str]:
    block: list[str] = []
    for line in out.splitlines():
        block.append(line)
        if line.startswith("# index:"):
            return block
    raise AssertionError(f"load did not open with a memory index header:\n{out}")


def index_bytes(block: list[str]) -> int:
    return len("\n".join(block)) + 1


def has_team_tree() -> bool:
    return (
        any((ROOT / ".pi" / "Teamwork" / "Teams").glob("*/Roles"))
        if (ROOT / ".pi" / "Teamwork" / "Teams").is_dir()
        else False
    )


@pytest.mark.skipif(
    not has_team_tree(),
    reason="no team tree in this checkout: `load` reads the live stores, and CI has none",
)
def test_load_opens_with_the_index_inside_its_cap() -> None:
    out = cli("load", "CEO").stdout
    block = index_block(out)
    assert block[0].startswith("# memory index:")
    assert len([line for line in block if line.startswith("- ")]) <= INDEX_LINES
    assert index_bytes(block) <= INDEX_CAP


@pytest.mark.skipif(
    not has_team_tree(),
    reason="no team tree in this checkout: `load` reads the live stores, and CI has none",
)
def test_index_and_pack_share_one_injected_budget() -> None:
    out = cli("load", "CEO", "--task", "T-0006").stdout
    index = index_bytes(index_block(out))
    packed = re.search(r"^# pack: .*?, (\d+) bytes", out, re.MULTILINE)
    assert packed, out
    assert index + int(packed.group(1)) <= PACK_CAP
    assert index <= INDEX_CAP


@pytest.mark.skipif(
    not has_team_tree(),
    reason="no team tree in this checkout: `load` reads the live stores, and CI has none",
)
def test_load_is_deterministic() -> None:
    assert cli("load", "CEO").stdout == cli("load", "CEO").stdout


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


def test_the_package_ships_every_declared_path(tmp_path: Path) -> None:
    pkg = build(tmp_path)
    manifest = json.loads((pkg / "package.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "@nidvue/teamwork"
    assert manifest["license"] == "AGPL-3.0-or-later"
    assert "pi-package" in manifest["keywords"]
    for pattern in manifest["files"]:
        assert (pkg / pattern).exists(), pattern
    for paths in manifest["pi"].values():
        for pattern in paths if isinstance(paths, list) else []:
            assert (pkg / pattern.lstrip("./")).exists(), pattern
    assert not (pkg / "src" / "teamwork").exists(), "the engine ships once, not twice"


def run_npm(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run npm, resolving ``npm.cmd`` the way Windows needs it started.

    ``subprocess`` cannot start a ``.cmd`` shim without a shell, so
    ``["npm", ...]`` on Windows raised WinError 2 (T-0094). The resolved path is
    run as one shell line there, quotes intact; POSIX keeps the plain argv.
    """
    npm = shutil.which("npm")
    assert npm is not None, "npm absent on this host"
    if os.name == "nt":
        line = " ".join([f'"{npm}"', *argv])
        return subprocess.run(line, cwd=cwd, capture_output=True, text=True, shell=True)
    return subprocess.run([npm, *argv], cwd=cwd, capture_output=True, text=True)


def test_the_tarball_has_no_engine_duplicate(tmp_path: Path) -> None:
    if shutil.which("npm") is None:
        pytest.skip("npm absent on this host")
    pkg = build(tmp_path)
    done = run_npm(["pack", "--dry-run", "--json"], pkg)
    assert done.returncode == 0, done.stderr
    files = [entry["path"] for entry in json.loads(done.stdout)[0]["files"]]
    assert "package.json" in files
    assert not [path for path in files if path.startswith("src/")], "engine shipped twice"
