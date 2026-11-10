"""A merge's records commit carries only the records the merge itself wrote (R-20).

``_pr_merge`` staged every dirty path under ``docs/`` before merging, so a file
another lane had left uncommitted in the base checkout rode into the Reviewer's
``chore(records)`` commit: 13ea3d1 (subject "docs/Team/Archive.md") also carried
D-20261030-Developer-3, and 30855f3 carried D-20261031-Designer. Both were a
peer lane's entry in ``docs/Team/Decisions.md``, written in the checkout the
merge ran in.

The pass owns the archive entry it writes (and the board, once the merge renders
it - T-0012); it commits exactly those paths and leaves every other uncommitted
file where it found it.

A peer's *staged* entry has to be lifted out of the index for ``git merge`` and
put back byte for byte afterwards, so the index shapes are part of that contract:
``M `` (modified), ``A `` (new - the path has no index entry to overwrite),
``D `` (deleted - no entry to capture), ``R `` (a rename, which is two paths, not
one ``old -> new`` token), ``MM`` (index != work tree) and a failed merge.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from test_pr_merge_base_advance import (
    add_task,
    commit_self_check_and_open,
    init_workspace,
    merge,
    pass_review,
    team_root,
)

from teamwork import engine

DEVELOPER = ["-c", "user.name=Developer", "-c", "user.email=developer@agents.nidvue.com"]
ARCHIVE = "docs/Team/Archive.md"


def ship(cli, project: Path) -> Path:
    """One task through branch, commit, self-check and a review-passed PR."""
    init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the records-scope fix", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    pass_review(cli, project)
    return work


def task_record(cli, project: Path) -> dict:
    return engine.parse_tasks(team_root(project) / "Roles" / "Developer" / "TaskQueue.md")[0]


def changed_paths(project: Path, rev: str) -> list[str]:
    return engine.run_git(project, "show", "--name-only", "--format=", rev).stdout.split()


def porcelain_status(project: Path) -> str:
    return engine.run_git(project, "status", "--porcelain").stdout


def index_rows(project: Path, *paths: str) -> dict[str, tuple[str, str]]:
    """The (mode, blob) the index holds for each of ``paths``."""
    rows: dict[str, tuple[str, str]] = {}
    for line in engine.run_git(project, "ls-files", "-s", "--", *paths).stdout.splitlines():
        meta, _, rel = line.partition("\t")
        mode, sha, _stage = meta.split()
        rows[rel] = (mode, sha)
    return rows


def index_blob(project: Path, rel: str) -> str:
    """The exact blob the index holds for ``rel`` (empty when absent)."""
    rows = index_rows(project, rel)
    return rows[rel][1] if rel in rows else ""


def main_blob(project: Path, rel: str) -> str:
    got = engine.run_git(project, "rev-parse", f"main:{rel}")
    return got.stdout.strip() if got.returncode == 0 else ""


def commit_on_main(project: Path, rel: str, text: str) -> None:
    """Commit a file on the base branch - the other side of a conflict."""
    assert engine.run_git(project, "checkout", "main").returncode == 0
    (project / rel).write_text(text, encoding="utf-8")
    assert engine.run_git(project, "add", "--", rel).returncode == 0
    made = subprocess.run(
        ["git", "-C", str(project)] + DEVELOPER + ["commit", "-q", "-m", f"main side {rel}"],
        capture_output=True,
        text=True,
    )
    assert made.returncode == 0, made.stderr


def one_commit_repo(path: Path) -> Path:
    """A repo with a committed archive and costs record, away from the CLI."""
    (path / "docs" / "Team").mkdir(parents=True)
    assert engine.run_git(path, "init", "-q").returncode == 0
    for key, value in (("user.name", "Developer"), ("user.email", "developer@agents.nidvue.com")):
        assert engine.run_git(path, "config", key, value).returncode == 0
    (path / ARCHIVE).write_text("archive\n", encoding="utf-8")
    (path / "docs" / "Team" / "Costs.md").write_text("costs\n", encoding="utf-8")
    assert engine.run_git(path, "add", "-A").returncode == 0
    assert engine.run_git(path, "commit", "-q", "-m", "base").returncode == 0
    return path


def test_a_foreign_uncommitted_record_stays_out_of_the_records_commit(cli, project, capsys) -> None:
    """The peer's dirty files survive the merge; the records commit holds the archive.

    This is the reported defect verbatim: a modified ``Decisions.md`` (the
    measured case, D-20261030-Developer-3) plus an untracked note under
    ``docs/Team/`` must neither enter the records commit nor be committed by it.
    """
    root = ship(cli, project)
    branch = task_record(cli, project)["branch"]
    decisions = project / "docs" / "Team" / "Decisions.md"
    foreign_entry = "\n## D-20261030-Developer-3 a foreign decision\n- decision: a peer lane's\n"
    decisions.write_text(decisions.read_text(encoding="utf-8") + foreign_entry, encoding="utf-8")
    peer_note = project / "docs" / "Team" / "PeerNotes.md"
    peer_note.write_text("a peer lane's untracked note\n", encoding="utf-8")

    merge(cli, project, capsys)

    task = task_record(cli, project)
    records = engine.run_git(project, "rev-parse", f"{task['merge_commit']}^1").stdout.strip()
    assert changed_paths(project, records) == ["docs/Team/Archive.md"]
    archive = engine.run_git(project, "show", f"{records}:docs/Team/Archive.md").stdout
    assert f"- branch / merge: {branch} / pending" in archive, archive
    assert (
        engine.run_git(project, "cat-file", "-e", f"{records}:docs/Team/PeerNotes.md").returncode
        != 0
    )
    assert changed_paths(project, "HEAD") == ["docs/Team/Archive.md"]
    committed = engine.run_git(project, "show", "HEAD:docs/Team/Decisions.md").stdout
    assert "D-20261030-Developer-3" not in committed
    status = engine.run_git(project, "status", "--porcelain").stdout
    assert "docs/Team/Decisions.md" in status, status
    assert "docs/Team/PeerNotes.md" in status, status
    assert "D-20261030-Developer-3" in decisions.read_text(encoding="utf-8")
    assert peer_note.read_text(encoding="utf-8") == "a peer lane's untracked note\n"
    assert root.is_dir()


def test_a_staged_foreign_record_is_left_staged_and_out_of_the_records_commit(
    cli, project, capsys
) -> None:
    """A peer's ``git add``ed record must not ride in on the commit's whole index.

    The regression case: ``git add -- <owned>`` narrowed only what this pass
    *staged*, and ``git commit`` without a pathspec then committed the entire
    index, so a foreign file a peer had already staged entered the Reviewer's
    ``chore(records)`` commit while the run claimed it was left uncommitted.
    """
    root = ship(cli, project)
    branch = task_record(cli, project)["branch"]
    decisions = project / "docs" / "Team" / "Decisions.md"
    foreign_entry = (
        "\n## D-20261031-Designer a staged foreign decision\n- decision: a peer lane's\n"
    )
    decisions.write_text(decisions.read_text(encoding="utf-8") + foreign_entry, encoding="utf-8")
    assert engine.run_git(project, "add", "--", "docs/Team/Decisions.md").returncode == 0
    assert "M  docs/Team/Decisions.md" in engine.run_git(project, "status", "--porcelain").stdout

    out = merge(cli, project, capsys)

    task = task_record(cli, project)
    records = engine.run_git(project, "rev-parse", f"{task['merge_commit']}^1").stdout.strip()
    assert changed_paths(project, records) == ["docs/Team/Archive.md"]
    assert (
        f"- branch / merge: {branch} / pending"
        in engine.run_git(project, "show", f"{records}:docs/Team/Archive.md").stdout
    )
    assert (
        "D-20261031-Designer"
        not in engine.run_git(project, "show", f"{records}:docs/Team/Decisions.md").stdout
    )
    assert changed_paths(project, "HEAD") == ["docs/Team/Archive.md"]
    assert (
        "D-20261031-Designer"
        not in engine.run_git(project, "show", "HEAD:docs/Team/Decisions.md").stdout
    )
    status = engine.run_git(project, "status", "--porcelain").stdout
    assert "M  docs/Team/Decisions.md" in status, status
    assert "D-20261031-Designer" in decisions.read_text(encoding="utf-8")
    left_claim = "left docs/Team/Decisions.md uncommitted" in out
    assert left_claim == ("M  docs/Team/Decisions.md" in status), (out, status)
    assert root.is_dir()


def test_a_foreign_record_staged_as_new_comes_back_staged(cli, project, capsys) -> None:
    """A peer's ``A `` entry has no index entry to overwrite after the lift.

    The delta defect: ``_return_staged_entries`` restored with
    ``update-index --cacheinfo``, which only updates an existing entry, so the
    restore of a staged *new* path exited 128, printed a WARNING, and left the
    peer's work untracked (``??``) instead of staged (``A ``).
    """
    ship(cli, project)
    fresh = project / "docs" / "Team" / "PeerNew.md"
    fresh.write_text("# peer new record\n", encoding="utf-8")
    assert engine.run_git(project, "add", "--", "docs/Team/PeerNew.md").returncode == 0
    assert "A  docs/Team/PeerNew.md" in porcelain_status(project)
    before = index_rows(project, "docs/Team/PeerNew.md")
    assert (
        before["docs/Team/PeerNew.md"][1]
        == engine.run_git(project, "rev-parse", ":docs/Team/PeerNew.md").stdout.strip()
    )

    out = merge(cli, project, capsys)

    task = task_record(cli, project)
    records = engine.run_git(project, "rev-parse", f"{task['merge_commit']}^1").stdout.strip()
    assert changed_paths(project, records) == [ARCHIVE]
    assert "WARNING" not in out, out
    assert index_rows(project, "docs/Team/PeerNew.md") == before
    assert "A  docs/Team/PeerNew.md" in porcelain_status(project), porcelain_status(project)
    assert fresh.read_text(encoding="utf-8") == "# peer new record\n"
    assert not main_blob(project, "docs/Team/PeerNew.md")


def test_a_foreign_record_staged_as_a_rename_comes_back_staged(cli, project, capsys) -> None:
    """A staged rename is two paths: lift both ends, or ``git merge`` refuses.

    The delta defect: plain porcelain renders ``R  old -> new`` as one token and
    that token was used as a pathspec, which matches nothing - nothing was
    lifted, the merge died on the dirty index, and the run blamed the branch
    owner for a rebase that was never needed.
    """
    ship(cli, project)
    assert (
        engine.run_git(
            project, "mv", "--", "docs/Team/Costs.md", "docs/Team/CostsRenamed.md"
        ).returncode
        == 0
    )
    renamed = "R  docs/Team/Costs.md -> docs/Team/CostsRenamed.md"
    assert renamed in porcelain_status(project), porcelain_status(project)
    before = index_rows(project, "docs/Team/Costs.md", "docs/Team/CostsRenamed.md")
    assert set(before) == {"docs/Team/CostsRenamed.md"}, before

    out = merge(cli, project, capsys)

    task = task_record(cli, project)
    records = engine.run_git(project, "rev-parse", f"{task['merge_commit']}^1").stdout.strip()
    assert changed_paths(project, records) == [ARCHIVE]
    assert "owner must rebase" not in out, out
    assert "WARNING" not in out, out
    assert index_rows(project, "docs/Team/Costs.md", "docs/Team/CostsRenamed.md") == before
    assert renamed in porcelain_status(project), porcelain_status(project)
    assert (project / "docs" / "Team" / "CostsRenamed.md").is_file()
    assert not (project / "docs" / "Team" / "Costs.md").exists()
    assert main_blob(project, "docs/Team/Costs.md")
    assert not main_blob(project, "docs/Team/CostsRenamed.md")


def test_a_foreign_record_staged_as_a_deletion_comes_back_staged(cli, project, capsys) -> None:
    """A ``D `` entry has no blob to capture, only a path to re-remove."""
    ship(cli, project)
    victim = project / "docs" / "Team" / "Costs.md"
    assert victim.is_file()
    assert engine.run_git(project, "rm", "-q", "--", "docs/Team/Costs.md").returncode == 0
    assert "D  docs/Team/Costs.md" in porcelain_status(project)
    before = index_rows(project, "docs/Team/Costs.md")
    assert before == {}

    out = merge(cli, project, capsys)

    task = task_record(cli, project)
    records = engine.run_git(project, "rev-parse", f"{task['merge_commit']}^1").stdout.strip()
    assert changed_paths(project, records) == [ARCHIVE]
    assert "WARNING" not in out, out
    assert index_rows(project, "docs/Team/Costs.md") == before
    assert "D  docs/Team/Costs.md" in porcelain_status(project), porcelain_status(project)
    assert not victim.exists()
    assert main_blob(project, "docs/Team/Costs.md")


def test_a_partially_staged_foreign_record_keeps_its_exact_index_blob(cli, project, capsys) -> None:
    """index != work tree: restore the index blob, never re-stage the work tree."""
    ship(cli, project)
    decisions = project / "docs" / "Team" / "Decisions.md"
    staged_text = (
        decisions.read_text(encoding="utf-8") + "\n## D-20261031-Tester a staged foreign half\n"
    )
    decisions.write_text(staged_text, encoding="utf-8")
    assert engine.run_git(project, "add", "--", "docs/Team/Decisions.md").returncode == 0
    worktree_text = staged_text + "- decision: work-tree only half\n"
    decisions.write_text(worktree_text, encoding="utf-8")
    assert "MM docs/Team/Decisions.md" in porcelain_status(project)
    staged_blob = index_blob(project, "docs/Team/Decisions.md")

    out = merge(cli, project, capsys)

    task = task_record(cli, project)
    records = engine.run_git(project, "rev-parse", f"{task['merge_commit']}^1").stdout.strip()
    assert changed_paths(project, records) == [ARCHIVE]
    assert "WARNING" not in out, out
    assert index_blob(project, "docs/Team/Decisions.md") == staged_blob
    assert decisions.read_text(encoding="utf-8") == worktree_text
    assert "MM docs/Team/Decisions.md" in porcelain_status(project)
    assert (
        "D-20261031-Tester a staged foreign half"
        not in engine.run_git(project, "show", "main:docs/Team/Decisions.md").stdout
    )


def test_a_failed_merge_gives_the_peer_its_index_back(cli, project, capsys) -> None:
    """A branch that cannot merge is refused before the work tree, peer index intact."""
    ship(cli, project)
    commit_on_main(project, "feature.txt", "main side\n")
    decisions = project / "docs" / "Team" / "Decisions.md"
    decisions.write_text(
        decisions.read_text(encoding="utf-8") + "\n## D-20261031-Reviewer a staged foreign half\n",
        encoding="utf-8",
    )
    assert engine.run_git(project, "add", "--", "docs/Team/Decisions.md").returncode == 0
    staged_blob = index_blob(project, "docs/Team/Decisions.md")

    capsys.readouterr()
    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-2") == 2
    captured = capsys.readouterr()

    assert "does not merge into" in captured.err, captured
    assert "owner must rebase" in captured.err, captured
    assert engine.run_git(project, "ls-files", "-u").stdout.strip() == ""
    assert index_blob(project, "docs/Team/Decisions.md") == staged_blob
    assert "M  docs/Team/Decisions.md" in porcelain_status(project)
    assert not engine.run_git(project, "log", "-1", "--format=%s", "main").stdout.startswith(
        "chore(merge)"
    )
    assert engine.run_git(project, "show", "main:feature.txt").stdout == "main side\n"
    assert not task_record(cli, project).get("merge_commit")


def test_a_clean_merge_takes_the_fast_path(cli, project, capsys) -> None:
    """No foreign entry: no lift, no noise, and nothing left in the index."""
    ship(cli, project)
    branch = task_record(cli, project)["branch"]

    out = merge(cli, project, capsys)

    task = task_record(cli, project)
    assert "# left" not in out, out
    assert "WARNING" not in out, out
    archive = engine.run_git(project, "show", f"main:{ARCHIVE}").stdout
    assert f"- branch / merge: {branch} / {task['merge_commit']}" in archive
    assert " / pending" not in archive
    assert porcelain_status(project) == "", porcelain_status(project)
    assert engine.run_git(project, "diff", "--cached", "--name-only").stdout.strip() == ""
    assert main_blob(project, "feature.txt")


def test_the_lift_and_restore_keep_a_record_staged_as_new(tmp_path) -> None:
    """The restore primitive itself: an ``A `` entry needs ``update-index --add``."""
    repo = one_commit_repo(tmp_path / "r")
    (repo / "docs" / "Team" / "PeerNew.md").write_text("peer new\n", encoding="utf-8")
    assert engine.run_git(repo, "add", "--", "docs/Team/PeerNew.md").returncode == 0
    before = index_rows(repo, "docs/Team/PeerNew.md")
    assert len(before) == 1

    rows, deleted = engine._lift_staged_entries(repo, ["docs/Team/PeerNew.md"])
    assert rows == [("100644", before["docs/Team/PeerNew.md"][1], "docs/Team/PeerNew.md")], rows
    assert deleted == []
    assert porcelain_status(repo) == "?? docs/Team/PeerNew.md\n", porcelain_status(repo)

    engine._return_staged_entries(repo, rows, deleted)

    assert index_rows(repo, "docs/Team/PeerNew.md") == before
    assert porcelain_status(repo) == "A  docs/Team/PeerNew.md\n", porcelain_status(repo)


def test_the_lift_and_restore_keep_a_staged_rename_as_two_paths(tmp_path) -> None:
    """The parse primitive itself: ``-z`` makes a rename ``new`` then ``old``."""
    repo = one_commit_repo(tmp_path / "r")
    assert (
        engine.run_git(repo, "mv", "--", "docs/Team/Costs.md", "docs/Team/CostsRenamed.md")
    ).returncode == 0

    ends = engine._uncommitted_paths(repo)
    assert ends == ["docs/Team/CostsRenamed.md", "docs/Team/Costs.md"], ends
    before = index_rows(repo, *ends)
    assert set(before) == {"docs/Team/CostsRenamed.md"}, before

    rows, deleted = engine._lift_staged_entries(repo, ends)
    assert [rel for _, _, rel in rows] == ["docs/Team/CostsRenamed.md"], rows
    assert deleted == ["docs/Team/Costs.md"], deleted
    assert porcelain_status(repo) == (" D docs/Team/Costs.md\n?? docs/Team/CostsRenamed.md\n"), (
        porcelain_status(repo)
    )

    engine._return_staged_entries(repo, rows, deleted)

    assert index_rows(repo, *ends) == before
    assert porcelain_status(repo) == ("R  docs/Team/Costs.md -> docs/Team/CostsRenamed.md\n"), (
        porcelain_status(repo)
    )


def commit_the_entry_on_main(project: Path) -> str:
    """Commit the pass's archive entry on the base branch and return the base tip.

    The pass wrote the entry into this work tree while it held the lane branch
    (the tests run without a separate lane worktree); putting the work tree on
    ``main`` and committing there is the state a pass running in the base
    checkout's work tree leaves behind.
    """
    assert engine.run_git(project, "checkout", "main").returncode == 0
    assert engine.run_git(project, "add", "--", "docs/Team/Archive.md").returncode == 0
    assert (
        engine.run_git(project, "commit", "-q", "-m", "docs(records): archive entry").returncode
        == 0
    )
    return engine.run_git(project, "rev-parse", "main").stdout.strip()


def test_a_merge_with_nothing_to_record_makes_no_records_commit(cli, project, capsys) -> None:
    """An entry already on the base means no records commit and no empty commit."""
    ship(cli, project)
    before = commit_the_entry_on_main(project)

    merge(cli, project, capsys)

    task = task_record(cli, project)
    merge_sha = engine.run_git(project, "rev-parse", task["merge_commit"]).stdout.strip()
    first_parent = engine.run_git(project, "rev-parse", f"{merge_sha}^1").stdout.strip()
    assert first_parent == before, (
        "a records commit was made with nothing to record: "
        + engine.run_git(project, "log", "--oneline", "-4").stdout
    )
    assert changed_paths(project, "HEAD") == ["docs/Team/Archive.md"]
    assert (
        f"- branch / merge: {task['branch']} / {task['merge_commit']}"
        in engine.run_git(project, "show", "HEAD:docs/Team/Archive.md").stdout
    )


def test_uncommitted_work_outside_the_records_is_still_refused(cli, project, capsys) -> None:
    """Narrowing the records commit must not let unrelated work sit under a merge."""
    ship(cli, project)
    (project / "peer-work.txt").write_text("a peer lane's uncommitted work\n", encoding="utf-8")
    before = engine.run_git(project, "rev-parse", "main").stdout.strip()

    capsys.readouterr()
    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-2") == 1
    err = capsys.readouterr().err
    assert "outside the reviewed records" in err, err
    assert "peer-work.txt" in err, err
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == before
