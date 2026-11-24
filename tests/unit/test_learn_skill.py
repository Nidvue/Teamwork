"""The companion skill ships with the npm package, beside the main skill.

`tw-learn` is its own installed skill directory so the host exposes its own
command. The package builder copies every directory under the checkout's
`skills/` except `tw` into the tarball's top-level `skills/`, which is the path
the manifest declares; the checkout source stays the only copy in git.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "skills" / "tw-learn" / "SKILL.md"
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


def test_the_source_skill_is_in_the_checkout() -> None:
    assert SOURCE.is_file(), "skills/tw-learn/SKILL.md is the source of the package copy"
    text = SOURCE.read_text(encoding="utf-8")
    assert text.startswith("---\nname: tw-learn\n"), "the frontmatter names the skill"
    assert "\ndescription: " in text.split("---\n")[1], "the description is what the host indexes"


def test_the_npm_package_ships_the_companion_skill_at_the_declared_path(tmp_path: Path) -> None:
    pkg = build(tmp_path)
    installed = pkg / "skills" / "tw-learn" / "SKILL.md"

    assert installed.is_file(), "the host loads top-level skills/, not skills/tw/skills/"
    assert installed.read_text(encoding="utf-8") == SOURCE.read_text(encoding="utf-8")
    manifest = json.loads((pkg / "package.json").read_text(encoding="utf-8"))
    assert manifest["pi"]["skills"] == ["./skills"]
    assert "skills" in manifest["files"]
    for pattern in manifest["pi"]["skills"]:
        assert (pkg / pattern.lstrip("./")).is_dir(), pattern


def test_the_main_skill_points_at_it() -> None:
    """A skill nobody is told to load is dead text: the procedure must name it."""
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "tw-learn" in text, "SKILL.md does not mention the companion skill"
    assert "skills/tw-learn/SKILL.md" in text, "the source path is not named"


def test_the_related_line_makes_no_path_claim() -> None:
    """The file ships at two depths, so any path it names is wrong in one of them."""
    body = SOURCE.read_text(encoding="utf-8").split("---\n", 2)[2]
    related = body.split("## 1.")[0]

    assert "](" not in related, "a link in the Related block resolves in one layout only"
    assert "skills/" not in related, "a path in the Related block is wrong in one layout"
    assert "../" not in related, "an escaping path in the Related block"


def test_the_documents_it_names_exist_in_both_layouts(tmp_path: Path) -> None:
    """An existence check on the documents, in the checkout *and* installed."""
    named = ("SKILL.md", "references/Roles.md", "references/Evidence.md", "references/Testing.md")
    for rel in named:
        assert (ROOT / rel).is_file(), f"{rel} is not in the checkout the skill points at"

    pkg = build(tmp_path)
    for rel in named:
        assert (pkg / "skills" / "tw" / rel).is_file(), (
            f"{rel} is not beside the installed companion skill, so the sentence the "
            "skill makes about where its related documents live is false when installed"
        )
