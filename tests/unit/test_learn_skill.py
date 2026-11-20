"""The companion skill ships with the bundle, and cannot drift from the checkout.

`tw-learn` is installed as its own skill directory so the host exposes its own
command, which puts it outside the one directory the bundle mirrors. A second copy
nobody verifies is exactly the drift `bundle.py` exists to prevent, so the manifest
lists it as a sibling and `sync-check` compares it like the main bundle.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import bundle

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "skills" / "tw-learn" / "SKILL.md"


def test_the_source_skill_is_in_the_checkout() -> None:
    assert SOURCE.is_file(), "skills/tw-learn/SKILL.md is the source of the bundle"
    text = SOURCE.read_text(encoding="utf-8")
    assert text.startswith("---\nname: tw-learn\n"), "the frontmatter names the skill"
    assert "\ndescription: " in text.split("---\n")[1], "the description is what the host indexes"


def test_the_manifest_names_it_as_a_sibling() -> None:
    assert bundle.SIBLING_SKILLS == {"skills/tw-learn": "tw-learn"}


def test_the_sibling_mirrors_next_to_the_installed_skill(tmp_path: Path) -> None:
    dest = tmp_path / "skills" / "tw"
    dest.mkdir(parents=True)
    pairs = bundle.sibling_targets(ROOT, dest)

    assert pairs == [(ROOT / "skills" / "tw-learn", tmp_path / "skills" / "tw-learn")]
    bundle.sync_siblings(ROOT, dest, dry_run=False, quiet=True)
    installed = tmp_path / "skills" / "tw-learn" / "SKILL.md"
    assert installed.is_file()
    assert installed.read_text(encoding="utf-8") == SOURCE.read_text(encoding="utf-8")


def test_a_stale_sibling_copy_is_reported_as_drift(tmp_path: Path) -> None:
    dest = tmp_path / "skills" / "tw"
    dest.mkdir(parents=True)
    bundle.sync_siblings(ROOT, dest, dry_run=False, quiet=True)
    (tmp_path / "skills" / "tw-learn" / "SKILL.md").write_text("old\n", encoding="utf-8")

    (target, (added, updated, removed)) = bundle.plan_siblings(ROOT, dest)[0]

    assert target.name == "tw-learn"
    assert updated == [Path("SKILL.md")], (added, updated, removed)


def test_the_main_skill_points_at_it() -> None:
    """A skill nobody is told to load is dead text: the procedure must name it."""
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "tw-learn" in text, "SKILL.md does not mention the companion skill"
    assert "skills/tw-learn/SKILL.md" in text, "the source path is not named"


def test_the_related_line_makes_no_path_claim() -> None:
    """The file ships at two depths, so any path it names is wrong in one of them.

    In the checkout it is `skills/tw-learn/SKILL.md`; installed it is a sibling
    of the teamwork skill, one level shallower. `../../SKILL.md` resolved to the repo
    root in the first and outside the skills directory in the second; `teamwork/...`
    then resolved only when installed. Both were real review findings, so the line
    now names the documents and claims no location at all.
    """
    body = SOURCE.read_text(encoding="utf-8").split("---\n", 2)[2]
    related = body.split("## 1.")[0]

    assert "](" not in related, "a link in the Related block resolves in one layout only"
    assert "skills/" not in related, "a path in the Related block is wrong in one layout"
    assert "../" not in related, "an escaping path in the Related block"


def test_the_documents_it_names_exist_in_both_layouts(tmp_path: Path) -> None:
    """An existence check on the documents, in the checkout *and* installed.

    The skill says the four live in the teamwork skill's directory: the repository
    root in the checkout, and beside this skill when installed. The first version of
    this test asserted only that `src/teamwork` was a directory for the installed
    side, so the docstring claimed both layouts and the body proved one - the exact
    kind of claim this skill exists to stop making. Both are resolved now.
    """
    named = ("SKILL.md", "references/Roles.md", "references/Evidence.md", "references/Testing.md")
    for rel in named:
        assert (ROOT / rel).is_file(), f"{rel} is not in the checkout the skill points at"

    dest = tmp_path / "skills" / "tw"
    dest.mkdir(parents=True)
    bundle.sync(ROOT, dest, dry_run=False, quiet=True)
    bundle.sync_siblings(ROOT, dest, dry_run=False, quiet=True)
    installed_teamwork = tmp_path / "skills" / "tw"
    for rel in named:
        assert (installed_teamwork / rel).is_file(), (
            f"{rel} is not beside the installed companion skill, so the sentence the "
            "skill makes about where its related documents live is false when installed"
        )
