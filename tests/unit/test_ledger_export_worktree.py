"""``ledger export`` must act on the work tree the command runs in (T-0008).

The export resolved its project through ``project_of(root)`` and wrote
``docs/Team/AuditManifest.json`` into the checkout that owns the team tree.
A lane that exported from its own work tree therefore got a file it could not
commit: the work tree stayed clean while the main checkout turned dirty - the
very state the manifest's own ``dirty`` field then misreported - and the
manifest pinned the main checkout's head, a revision the committing branch does
not have.

The export now resolves the work tree the same way ``branch``, ``commit`` and
``pr`` do (``work_repo``), so the manifest lands where the command runs and
describes that work tree's revision.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine

AGENTS = ("ceo", "developer-1")


def team_root(project: Path) -> Path:
    """The hidden team tree ``<project>/.pi/Teamwork/Teams/<Team>/``."""
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def _seed_repo(cli, project: Path) -> Path:
    """A project with a team workspace and one committed revision."""
    assert cli("--project", project, "init", "--agents", ",".join(AGENTS)) == 0
    engine.ensure_repo(project, commit=False, quiet=True)
    (project / "a.txt").write_text("one\n", encoding="utf-8")
    engine.run_git(project, "add", "-A")
    engine.run_git(project, "commit", "-qm", "seed")
    return team_root(project)


def _worktree(project: Path, root: Path, name: str) -> Path:
    """A lane work tree under the team's ``Runtime/Worktrees``."""
    path = root / engine.DIR_RUNTIME / engine.DIR_WORKTREES / name
    path.parent.mkdir(parents=True, exist_ok=True)
    engine.run_git(project, "worktree", "add", "--detach", str(path), "HEAD")
    return path


def _manifest(work_tree: Path) -> dict:
    return json.loads((work_tree / "docs" / "Team" / engine.F_MANIFEST).read_text(encoding="utf-8"))


def test_the_export_lands_in_the_work_tree_it_runs_in(cli, project: Path, monkeypatch) -> None:
    root = _seed_repo(cli, project)
    wt = _worktree(project, root, "Developer-1")
    monkeypatch.chdir(wt)

    assert cli("ledger", "export") == 0

    assert (wt / "docs" / "Team" / engine.F_MANIFEST).exists()
    assert not (project / "docs" / "Team" / engine.F_MANIFEST).exists()


def test_the_export_leaves_the_main_checkout_untouched(cli, project: Path, monkeypatch) -> None:
    """The main checkout must not gain the lane's manifest or report it dirty."""
    root = _seed_repo(cli, project)
    wt = _worktree(project, root, "Developer-1")
    before = engine.run_git(project, "status", "--porcelain").stdout
    monkeypatch.chdir(wt)

    assert cli("ledger", "export") == 0

    assert engine.run_git(project, "status", "--porcelain").stdout == before
    assert not (project / "docs" / "Team" / engine.F_MANIFEST).exists()


def test_the_manifest_names_the_work_tree_revision(cli, project: Path, monkeypatch) -> None:
    """The manifest pins the revision of the tree it was exported from."""
    root = _seed_repo(cli, project)
    wt = _worktree(project, root, "Developer-1")
    (wt / "b.txt").write_text("two\n", encoding="utf-8")
    engine.run_git(wt, "add", "-A")
    engine.run_git(wt, "commit", "-qm", "lane work")
    lane_head = engine.run_git(wt, "rev-parse", "HEAD").stdout.strip()
    main_head = engine.run_git(project, "rev-parse", "HEAD").stdout.strip()
    assert lane_head != main_head
    monkeypatch.chdir(wt)

    assert cli("ledger", "export") == 0

    manifest = _manifest(wt)
    assert manifest["git"]["head"] == lane_head
    assert manifest["git"]["head"] != main_head


def test_the_manifest_reports_the_work_tree_as_clean(cli, project: Path, monkeypatch) -> None:
    """A dirty main checkout must not make the lane's manifest claim dirty."""
    root = _seed_repo(cli, project)
    wt = _worktree(project, root, "Developer-1")
    (project / "scratch.txt").write_text("dirty\n", encoding="utf-8")
    monkeypatch.chdir(wt)

    assert cli("ledger", "export") == 0

    assert _manifest(wt)["git"]["dirty"] is False


def test_a_plain_checkout_still_writes_into_itself(cli, project: Path, monkeypatch) -> None:
    """Outside a work tree the project that owns the team tree is the answer."""
    root = _seed_repo(cli, project)
    assert root.is_dir()
    monkeypatch.chdir(project)

    assert cli("ledger", "export") == 0

    manifest = project / "docs" / "Team" / engine.F_MANIFEST
    assert manifest.exists()
    assert (
        _manifest(project)["git"]["head"]
        == engine.run_git(project, "rev-parse", "HEAD").stdout.strip()
    )


def test_the_manifest_publishes_no_machine_path(cli, project: Path, monkeypatch) -> None:
    """A work tree path must never leak into the committed manifest."""
    root = _seed_repo(cli, project)
    wt = _worktree(project, root, "Developer-1")
    monkeypatch.chdir(wt)

    assert cli("ledger", "export") == 0

    text = (wt / "docs" / "Team" / engine.F_MANIFEST).read_text(encoding="utf-8")
    assert str(wt) not in text
    assert "/tmp/" not in text
