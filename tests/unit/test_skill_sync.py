"""The installed skill must stay a mirror of the checkout (T-0044).

The repository root *is* the skill, but an agent host loads a copy from its
skills directory (``~/.pi/agent/skills/teamwork`` on pi). That copy is what every
agent actually reads, so a stale copy is a live defect, not a cosmetic one:
measured before this existed, the installed tree carried an old ``SKILL.md`` and
was **missing 8 engine modules** - ``config.py``, ``gitutil.py``, ``io.py``,
``layout.py``, ``names.py``, ``records.py``, and others - so an engine that
imports ``config`` worked from the checkout and failed from the installed copy.

``scripts/sync_skill.py`` owns the mirror. These tests pin its contract:
idempotent, complete, deleting only what it manages, and ``--check`` a truthful
drift detector that writes nothing.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

# ``scripts/`` is not on the import path: these are build tools, not a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import sync_skill  # noqa: E402  (import after the path fix)
from build_pi_package import SKILL_FILES, SKILL_TREES  # noqa: E402


def make_source(root: Path) -> Path:
    """A miniature skill checkout with one file in every bundle tree."""
    source = root / "checkout"
    (source).mkdir(parents=True)
    for name in SKILL_FILES:
        (source / name).write_text(f"# {name}\n", encoding="utf-8")
    for tree in SKILL_TREES:
        (source / tree).mkdir(parents=True)
        (source / tree / "one.txt").write_text(f"{tree}\n", encoding="utf-8")
    (source / "tests").mkdir()
    (source / "tests" / "not-shipped.py").write_text("x = 1\n", encoding="utf-8")
    return source


def test_the_bundle_contains_every_shipped_file_and_no_test_file(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    rels = {str(rel) for rel in sync_skill.bundle_files(source)}
    assert {str(n) for n in SKILL_FILES} | {f"{t}/one.txt" for t in SKILL_TREES} == rels
    assert not any(rel.startswith("tests/") for rel in rels)


def test_sync_is_idempotent(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    dest = tmp_path / "installed"
    assert sync_skill.sync(source, dest, dry_run=False, quiet=True) == 0
    before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
    assert sync_skill.sync(source, dest, dry_run=False, quiet=True) == 0
    after = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
    assert before == after
    added, updated, removed = sync_skill.plan(source, dest)
    assert (added, updated, removed) == ([], [], [])


def test_a_new_and_a_changed_file_are_both_carried(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    dest = tmp_path / "installed"
    sync_skill.sync(source, dest, dry_run=False, quiet=True)

    (source / "src" / "new_module.py").write_text("NEW = 1\n", encoding="utf-8")
    (source / "SKILL.md").write_text("# changed\n", encoding="utf-8")

    added, updated, _removed = sync_skill.plan(source, dest)
    assert added == [Path("src/new_module.py")]
    assert updated == [Path("SKILL.md")]

    sync_skill.sync(source, dest, dry_run=False, quiet=True)
    assert (dest / "src" / "new_module.py").read_text(encoding="utf-8") == "NEW = 1\n"
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# changed\n"


def test_a_renamed_module_is_removed_rather_than_shadowing_the_new_one(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    dest = tmp_path / "installed"
    sync_skill.sync(source, dest, dry_run=False, quiet=True)
    stale = dest / "src" / "old_module.py"
    stale.write_text("OLD = 1\n", encoding="utf-8")

    _added, _updated, removed = sync_skill.plan(source, dest)
    assert removed == [Path("src/old_module.py")]
    sync_skill.sync(source, dest, dry_run=False, quiet=True)
    assert not stale.exists()


def test_an_unmanaged_file_in_the_skills_directory_is_never_deleted(tmp_path: Path) -> None:
    """A README or a local override the operator put there is not ours to remove."""
    source = make_source(tmp_path)
    dest = tmp_path / "installed"
    sync_skill.sync(source, dest, dry_run=False, quiet=True)
    note = dest / "README.md"
    note.write_text("operator notes\n", encoding="utf-8")
    (source / "references" / "one.txt").unlink()  # a managed file disappears

    _added, _updated, removed = sync_skill.plan(source, dest)
    assert Path("README.md") not in removed
    assert Path("references/one.txt") in removed
    sync_skill.sync(source, dest, dry_run=False, quiet=True)
    assert note.read_text(encoding="utf-8") == "operator notes\n"


def test_check_reports_drift_and_writes_nothing(tmp_path: Path, capsys) -> None:
    source = make_source(tmp_path)
    dest = tmp_path / "installed"
    sync_skill.sync(source, dest, dry_run=False, quiet=True)
    (source / "SKILL.md").write_text("# moved on\n", encoding="utf-8")
    marker = dest / "SKILL.md"
    before = marker.read_bytes()

    rc = sync_skill.main(["--source", str(source), "--dest", str(dest), "--check"])
    assert rc == 1, "a stale installed copy must fail the check"
    assert marker.read_bytes() == before, "--check must not write"
    assert "out of sync" in capsys.readouterr().err


def test_check_passes_on_an_in_sync_copy(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    dest = tmp_path / "installed"
    sync_skill.sync(source, dest, dry_run=False, quiet=True)
    assert sync_skill.main(["--source", str(source), "--dest", str(dest), "--check"]) == 0


def test_check_fails_when_nothing_is_installed(tmp_path: Path, capsys) -> None:
    assert sync_skill.main(["--dest", str(tmp_path / "absent"), "--check"]) == 1
    assert "does not exist" in capsys.readouterr().err


def test_the_shipped_source_trees_are_the_package_trees(repo_root: Path) -> None:
    """One list, two consumers: the tarball builder and the mirror cannot drift."""
    assert sync_skill.BUNDLE_FILES == SKILL_FILES
    assert sync_skill.BUNDLE_TREES == SKILL_TREES
    assert (repo_root / "SKILL.md").is_file()
    assert all((repo_root / tree).is_dir() for tree in SKILL_TREES)


@pytest.mark.parametrize("rel", ["src/teamwork/config.py", "SKILL.md", "scripts/teamwork.py"])
def test_the_real_checkout_bundle_carries_the_runtime_engine(repo_root: Path, rel: str) -> None:
    """The installed copy must be runnable: every engine module ships with it."""
    assert Path(rel) in set(sync_skill.bundle_files(repo_root)), rel


def test_syncing_the_real_checkout_into_a_fresh_dir_produces_a_runnable_engine(
    repo_root: Path, tmp_path: Path
) -> None:
    """A full copy of the bundle runs the CLI - that is what 'in sync' has to mean."""
    dest = tmp_path / "skills" / "teamwork"
    assert sync_skill.main(["--dest", str(dest)]) == 0
    assert sync_skill.main(["--dest", str(dest), "--check"]) == 0
    engine = dest / "src" / "teamwork" / "engine.py"
    assert engine.is_file(), "the copied bundle has no engine"
    import subprocess
    import sys

    probe = subprocess.run(
        [sys.executable, str(dest / "scripts" / "teamwork.py"), "--help"],
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr
    assert "usage: teamwork" in probe.stdout
    shutil.rmtree(dest.parent)
