"""Why this file exists: AC-M25-4 - an installed package exposes exactly one skill.

pi discovers skills as ``<root>/<name>/SKILL.md``, so a second copy of the skill in
the published tarball (a stale ``dist/``, a duplicated reference tree, a skill file
copied at the wrong depth) makes pi register the same skill twice: the operator sees
two ``teamwork`` entries and only one of them is the revision that was released.

The unit layer proves the build *directory*; this file proves the artifact npm would
install - the packed tarball, unpacked where npm puts it. It also pins the skill's
frontmatter ``name`` to the directory that holds it, because pi keys the skill by the
declared name and a mismatch is a silent duplicate.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "scripts" / "build_pi_package.py"
SKILL = "tw"


def pack(tmp_path: Path) -> tuple[Path, Path]:
    if shutil.which("npm") is None:
        pytest.skip("npm is not on PATH, so no tarball can be packed here")
    out = tmp_path / "dist"
    built = subprocess.run(
        [sys.executable, str(BUILD), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert built.returncode == 0, built.stderr
    pkg = out / "@nidvue" / "teamwork"
    packed = subprocess.run(
        ["npm", "pack", "--pack-destination", str(tmp_path)],
        cwd=pkg,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert packed.returncode == 0, packed.stderr
    tarballs = sorted(tmp_path.glob("*.tgz"))
    assert len(tarballs) == 1, f"one pack run produced one tarball: {tarballs}"
    installed = tmp_path / "node_modules" / "@nidvue" / "teamwork"
    installed.mkdir(parents=True)
    with tarfile.open(tarballs[0]) as archive:
        archive.extractall(installed, filter="data")
    return tarballs[0], installed / "package"


def test_installed_package_exposes_exactly_one_skill_named_teamwork(tmp_path: Path) -> None:
    _tarball, installed = pack(tmp_path)

    skills = sorted(p.name for p in (installed / "skills").iterdir() if p.is_dir())
    assert skills == [SKILL], f"the installed package ships exactly one skill: {skills}"

    manifests = sorted(p.relative_to(installed).as_posix() for p in installed.rglob("SKILL.md"))
    assert manifests == [f"skills/{SKILL}/SKILL.md"], (
        f"exactly one SKILL.md in the installed tree, at one depth: {manifests}"
    )

    manifest = json.loads((installed / "package.json").read_text(encoding="utf-8"))
    assert manifest["pi"]["skills"] == ["./skills"], manifest["pi"]["skills"]
    assert manifest["name"] == "@nidvue/teamwork", manifest["name"]


def test_installed_skill_declares_the_directory_that_holds_it(tmp_path: Path) -> None:
    _tarball, installed = pack(tmp_path)
    text = (installed / "skills" / SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), "pi reads the name from the frontmatter, not the path"
    header = text.split("---", 2)[1]
    names = [
        line.split(":", 1)[1].strip().strip('"')
        for line in header.splitlines()
        if line.startswith("name:")
    ]
    assert names == [SKILL], f"the declared skill name is the directory name: {names}"
