"""``pr merge`` must advance the base *branch* - and land the archive on it (T-0030).

The P-0022 merge exposed two defects that have one cause: the merge happened
somewhere other than on the base branch.

1. The PR record carried the base as a raw revision (``- base: 8f210bc...``)
   instead of a branch name. ``git checkout <sha>`` detaches HEAD, so
   ``git merge --no-ff`` built the merge commit off-branch: the merge was
   printed as done, the task and the ledger recorded it, and ``main`` still
   pointed at the pre-merge tip. Nothing was published; the merge commit was
   only reachable by fast-forwarding ``main`` by hand.
2. The archive entry is written by the review pass, in whichever work tree the
   pass ran in. In the per-instance layout that is a lane work tree, so the base
   branch never received an entry: after the merge, the base held no record that
   the work shipped.

So ``pr merge`` maps a revision base back to the branch pointing at it (and
refuses when there is none), runs the merge in the work tree that holds the
base, and guarantees the base carries the branch's archive entry inside the same
``chore(records)`` commit.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

AGENTS = ("ceo", "developer-1", "reviewer-1", "reviewer-2")


def team_root(project: Path) -> Path:
    """The hidden team tree ``<project>/.pi/Teamwork/Teams/<Team>/``."""
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init_workspace(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ",".join(AGENTS)) == 0
    root = team_root(project)
    assert root.is_dir()
    return root


def add_task(
    cli, project: Path, title: str, filename: str, *, worktree: bool = False, base: str = ""
) -> str:
    """Add + claim a task, start its branch (optionally in its own worktree)."""
    assert cli("--project", project, "task", "add", "developer", title, "--priority", "P0") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    argv = ["--project", project, "branch", "start", "--agent", "developer-1", "--task", "T-0001"]
    if worktree:
        argv.append("--worktree")
    if base:
        argv += ["--base", base]
    assert cli(*argv) == 0
    work = project_of_worktree(team_root(project)) if worktree else project
    (work / filename).write_text("done\n", encoding="utf-8")
    return str(work)


def project_of_worktree(root: Path) -> Path:
    """The one worktree under the team's ``Runtime/Worktrees``."""
    worktrees = sorted((root / engine.DIR_RUNTIME / engine.DIR_WORKTREES).iterdir())
    assert len(worktrees) == 1, worktrees
    return worktrees[0]


def commit_self_check_and_open(cli, project: Path, *, work: Path, filename: str) -> None:
    assert (
        cli(
            "--project",
            project,
            "commit",
            "--role",
            "developer",
            "--type",
            "feat",
            "--task",
            "T-0001",
            "--area",
            "core",
            "--goal",
            "ship it",
            "--deliverable",
            filename,
            "--why",
            "the task asked for it",
            "--status",
            "implemented",
            "--result",
            "pytest @HEAD -> 1 passed",
            "--all",
        )
        == 0
    )
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "selfcheck")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            "T-0001",
            "--by",
            "developer-1",
            "--note",
            "re-read the diff",
            "--test",
            "pytest @HEAD -> 1 passed",
        )
        == 0
    )
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "review") == 0
    )
    assert (
        cli("--project", project, "pr", "open", "--agent", "developer-1", "--task", "T-0001") == 0
    )
    assert work.is_dir()


def pass_review(cli, project: Path) -> None:
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0001",
            "--by",
            "reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest @HEAD -> 1 passed @be762bf",
            # these tests drive the merge themselves and rewrite the recorded
            # base first, so the pass records the verdict only
            "--no-merge",
        )
        == 0
    )


def rework_records(cli, project: Path, *, base: str) -> None:
    """Rewrite the recorded base of T-0001's PR and task - as P-0022 stored it."""
    root = team_root(project)
    path = root / "Reviews.md"
    prs = engine.parse_reviews(path)
    assert len(prs) == 1
    prs[0]["base"] = base
    engine.write_reviews(path, prs)
    tpath = root / "Roles" / "Developer" / "TaskQueue.md"
    tasks = engine.parse_tasks(tpath)
    tasks[0]["base"] = base
    engine.write_tasks(tpath, tasks, "developer")


def merge(cli, project: Path, capsys) -> str:
    """Merge the single approved PR and return its output."""
    capsys.readouterr()
    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-2") == 0
    return capsys.readouterr().out


def head_branch(cli, project: Path) -> str:
    return engine.run_git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def committed_archive(project: Path, rev: str = "main") -> str:
    """The archive blob as the base branch stores it (not as a work tree shows it)."""
    return engine.run_git(project, "show", f"{rev}:docs/Team/Archive.md").stdout


def test_merge_into_a_revision_base_still_advances_the_base_branch(cli, project, capsys) -> None:
    """A base recorded as a sha must not detach HEAD and orphan the merge commit.

    This is the P-0022 defect verbatim: ``- base: 8f210bc...`` in the record
    produced ``# merged ... -> 8f210bc at 8444134`` while ``main`` stayed at
    8f210bc, and the merge commit was reachable only by a hand fast-forward.
    """
    root = init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the base-advance fix", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    pass_review(cli, project)

    base_sha = engine.run_git(project, "rev-parse", "main").stdout.strip()
    rework_records(cli, project, base=base_sha)

    out = merge(cli, project, capsys)

    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]
    # the reported base is the branch, not the revision it was recorded as
    assert f"# merged P-0001 {branch} -> main at " in out
    assert f"-> {base_sha[:7]} at" not in out.splitlines()[0]
    # HEAD is on the branch, not detached, so the merge commit is on main
    assert head_branch(cli, project) == "main"
    main_sha = engine.run_git(project, "rev-parse", "main").stdout.strip()
    assert main_sha != base_sha, "the base branch never advanced"
    assert engine.run_git(project, "merge-base", "--is-ancestor", base_sha, "main").returncode == 0
    # the merged work is reachable from main
    assert engine.run_git(project, "cat-file", "-e", "main:feature.txt").returncode == 0
    # the record now names the branch, so the next merge has a branch to advance
    assert engine.parse_reviews(root / "Reviews.md")[0]["base"] == "main"
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


def test_merge_refuses_a_base_revision_that_no_branch_points_at(cli, project, capsys) -> None:
    """Only a branch can be advanced: an unbound revision is refused, not half-merged."""
    init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the base-advance fix", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    pass_review(cli, project)
    rework_records(cli, project, base="0" * 40)
    before = engine.run_git(project, "rev-parse", "main").stdout.strip()

    capsys.readouterr()
    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-2") == 2
    err = capsys.readouterr().err
    assert "not a local branch" in err
    assert "detached HEAD" in err
    # nothing moved and nothing was merged
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == before
    assert engine.parse_reviews(team_root(project) / "Reviews.md")[0]["status"] == "approved"


def test_merge_refuses_to_merge_a_branch_into_itself(cli, project, capsys) -> None:
    """A base equal to the PR branch integrates nothing and must not be attempted."""
    init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the base-advance fix", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    pass_review(cli, project)
    branch = engine.parse_tasks(team_root(project) / "Roles" / "Developer" / "TaskQueue.md")[0][
        "branch"
    ]
    rework_records(cli, project, base=branch)

    capsys.readouterr()
    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-2") == 2
    assert "into itself" in capsys.readouterr().err


def test_merge_writes_the_missing_archive_entry_on_the_base(cli, project, capsys) -> None:
    """The entry the review pass wrote elsewhere must reach the base's history.

    In the per-instance layout the pass wrote ``docs/Team/Archive.md`` into a
    lane work tree, so the base branch had no entry for the branch and the merge
    had nothing to repoint: ``main`` archived nothing about the shipped work.
    """
    root = init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the base-advance fix", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    pass_review(cli, project)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]

    # drop the entry the pass left in this work tree: the base branch has none,
    # which is the state the per-instance layout produced on its own
    engine.run_git(project, "checkout", "--", "docs/Team/Archive.md")
    assert branch not in engine.archive_path(root).read_text(encoding="utf-8")

    out = merge(cli, project, capsys)

    assert f"# archive: wrote the accepted-results entry for {branch} on the base" in out
    sha = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["merge_commit"]
    archive = committed_archive(project)
    assert f"- branch / merge: {branch} / {sha}" in archive
    assert " / pending" not in archive
    # the entry arrived in the same records commit the merge makes before merging
    assert cli("--project", project, "archive") == 0
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


def test_merge_does_not_duplicate_an_entry_the_base_already_has(cli, project, capsys) -> None:
    """When the pass already wrote it on the base, the merge reuses that entry."""
    root = init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the base-advance fix", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    pass_review(cli, project)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]

    out = merge(cli, project, capsys)

    assert f"# archive: {branch} already has an entry on the base" in out
    archived_branches = [
        line[len("- branch / merge: ") :].rstrip().rpartition(" / ")[0]
        for line in committed_archive(project).split("\n")
        if line.startswith("- branch / merge: ")
    ]
    assert archived_branches.count(branch) == 1, archived_branches


def test_merge_runs_in_the_work_tree_that_holds_the_base(cli, project, capsys, monkeypatch) -> None:
    """A lane work tree cannot check out the base: the merge moves to the one that has it.

    ``git checkout`` switches only its own work tree and git refuses to check
    one branch out twice, so merging from inside the Developer's worktree either
    failed outright or advanced a work tree nobody expected to be on the base.
    """
    root = init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the base-advance fix", "feature.txt", worktree=True))
    monkeypatch.chdir(work)
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    pass_review(cli, project)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]

    out = merge(cli, project, capsys)
    monkeypatch.chdir(project.parent)

    assert f"# merged P-0001 {branch} -> main at " in out
    assert engine.run_git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"
    assert engine.run_git(project, "cat-file", "-e", "main:feature.txt").returncode == 0
    sha = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["merge_commit"]
    assert f"- branch / merge: {branch} / {sha}" in committed_archive(project)
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


def test_merge_base_branch_maps_a_revision_to_the_branch_at_it(cli, project) -> None:
    """The resolver prefers the default base and accepts a unique branch."""
    init_workspace(cli, project)
    main_tip = engine.run_git(project, "rev-parse", "main").stdout.strip()
    assert engine._merge_base_branch(project, "main", {}) == "main"
    assert engine._merge_base_branch(project, "", {}) == "main"
    assert engine._merge_base_branch(project, main_tip, {}) == "main"
    # a second branch at the same commit loses to the default base
    engine.run_git(project, "branch", "side", "main")
    assert engine._merge_base_branch(project, main_tip, {}) == "main"
    assert engine._merge_base_branch(project, "side", {}) == "side"


def test_archive_write_repo_targets_the_work_tree_holding_the_base(cli, project) -> None:
    """The review pass must write the entry where the base branch is checked out."""
    init_workspace(cli, project)
    engine.run_git(project, "branch", "side", "main")
    work = Path(
        add_task(
            cli, project, "ship the base-advance fix", "feature.txt", worktree=True, base="side"
        )
    )
    assert work.is_dir()
    root = team_root(project)
    # main is checked out at the project root, so that is where its records belong
    assert engine.archive_write_repo(root, {"base": "main"}) == project.resolve()
    # a base branch parked in a work tree is written there, not in the command's cwd
    side_wt = project / "side-checkout"
    assert engine.run_git(project, "worktree", "add", str(side_wt), "side").returncode == 0
    assert engine.archive_write_repo(root, {"base": "side"}) == side_wt
    # a base that no work tree holds falls back to the project root
    assert engine.archive_write_repo(root, {"base": ""}) == project.resolve()
