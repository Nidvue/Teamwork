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
    """The one worktree under the team's ``Runtime/Worktrees``.

    T-0029 keys the worktree by (instance, task), so it sits one level deeper than
    the instance directory: the search is for the directory that actually holds a
    ``.git`` file, not for the first child.
    """
    base = root / engine.DIR_RUNTIME / engine.DIR_WORKTREES
    worktrees = sorted(path.parent for path in base.rglob(".git"))
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
    assert f"# merged P-0001 {branch} -> main at " in out
    assert f"-> {base_sha[:7]} at" not in out.splitlines()[0]
    assert head_branch(cli, project) == "main"
    main_sha = engine.run_git(project, "rev-parse", "main").stdout.strip()
    assert main_sha != base_sha, "the base branch never advanced"
    assert engine.run_git(project, "merge-base", "--is-ancestor", base_sha, "main").returncode == 0
    assert engine.run_git(project, "cat-file", "-e", "main:feature.txt").returncode == 0
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

    engine.run_git(project, "checkout", "--", "docs/Team/Archive.md")
    assert branch not in engine.archive_path(root).read_text(encoding="utf-8")

    out = merge(cli, project, capsys)

    assert f"# archive: wrote the accepted-results entry for {branch} on the base" in out
    sha = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["merge_commit"]
    archive = committed_archive(project)
    assert f"- branch / merge: {branch} / {sha}" in archive
    assert " / pending" not in archive
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
    assert engine.archive_write_repo(root, {"base": "main"}) == project.resolve()
    side_wt = project / "side-checkout"
    assert engine.run_git(project, "worktree", "add", str(side_wt), "side").returncode == 0
    assert engine.archive_write_repo(root, {"base": "side"}) == side_wt
    assert engine.archive_write_repo(root, {"base": ""}) == project.resolve()


def test_the_merge_restores_the_branch_the_work_tree_was_on(cli, project, capsys) -> None:
    """A successful merge must not strand the calling work tree on the base.

    Only the failure path checked the previous branch out again, so a lane whose
    work tree was on another branch silently found itself on ``main`` after the
    merge - and its next edit/commit landed on the base (T-0020/A9).
    """
    root = init_workspace(cli, project)
    work = Path(add_task(cli, project, "restore the branch after a merge", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    pass_review(cli, project)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]

    assert engine.run_git(project, "checkout", "-b", "lane/scratch").returncode == 0
    out = merge(cli, project, capsys)

    assert "# restored lane/scratch" in out, out
    assert head_branch(cli, project) == "lane/scratch"
    assert engine.run_git(project, "cat-file", "-e", "main:feature.txt").returncode == 0
    assert engine.run_git(project, "branch", "--list", branch).stdout.strip() == ""
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


def branchless_task(cli, project: Path) -> None:
    """A deliverable with no branch and no PR: a records/doc task that never merges."""
    assert (
        cli(
            "--project", project, "task", "add", "developer", "record the thing", "--priority", "P1"
        )
        == 0
    )
    assert cli("--project", project, "task", "next", "developer-1") == 0
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
            "re-read the records",
            "--test",
            "pytest @HEAD -> 1 passed",
        )
        == 0
    )
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "review") == 0
    )


def test_a_branchless_pass_lands_its_entry_on_the_base(cli, project, capsys) -> None:
    """Nothing integrates a branchless deliverable, so its pass must commit the entry.

    L-0001: two accepted branchless deliverables had no archive entry, because the
    renderer wrote the entry and returned - `pr merge` is the only committer and a
    task with no branch never reaches it - so a reviewer restored them by hand.
    """
    root = init_workspace(cli, project)
    branchless_task(cli, project)

    capsys.readouterr()
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
            "pytest @HEAD -> 1 passed",
        )
        == 0
    )
    out = capsys.readouterr().out

    assert "# archive: committed the accepted-results entry for T-0001 on main" in out, out
    archive = committed_archive(project)
    assert "## T-0001 " in archive, archive[-400:]
    assert archive.count("## T-0001 ") == 1
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == "", (
        "the entry is still uncommitted in the work tree"
    )
    assert engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["status"] == "done"


def test_a_dirty_archive_render_does_not_block_the_merge(cli, project, capsys, monkeypatch) -> None:
    """The uncommitted render must not make `git checkout <base>` refuse the merge.

    Reviewer-1 L-0003 (P-0005): the pass wrote ``docs/Team/Archive.md`` into the work
    tree the merge had to use, ``git checkout main`` refused with "local changes ...
    would be overwritten", and the recovery was a stash plus a hand re-run - on
    P-0005 and again on P-0010/P-0013/P-0014. The render is generated, so the merge
    discards that one path, checks the base out, and re-renders the entry there.
    """
    root = init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the base-advance fix", "feature.txt", worktree=True))
    monkeypatch.chdir(work)
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    pass_review(cli, project)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]

    rendered = (project / "docs" / "Team" / "Archive.md").read_text(encoding="utf-8")
    engine.run_git(project, "checkout", "--", "docs/Team/Archive.md")
    (work / "docs" / "Team" / "Archive.md").write_text(rendered, encoding="utf-8")
    archive_path = project / "docs" / "Team" / "Archive.md"
    archive_path.write_text(
        archive_path.read_text(encoding="utf-8") + "\n## T-9999 - another lane (developer)\n",
        encoding="utf-8",
    )
    engine.run_git(project, "add", "docs/Team/Archive.md")
    engine.run_git(
        project,
        "-c",
        "user.name=Reviewer",
        "-c",
        "user.email=reviewer@agents.nidvue.com",
        "commit",
        "-q",
        "-m",
        "chore(records): another lane's entry",
    )
    assert engine.run_git(project, "checkout", "--detach").returncode == 0
    assert engine.branch_worktree(project, "main") is None

    out = merge(cli, project, capsys)
    monkeypatch.chdir(project.parent)

    assert "# discarded this pass's uncommitted render of docs/Team/Archive.md" in out, out
    assert f"# merged P-0001 {branch} -> main at " in out
    archive = committed_archive(project)
    assert archive.count("## T-9999 - another lane (developer)") == 1, (
        "another lane's entry was lost"
    )
    assert archive.count(f"- branch / merge: {branch} /") == 1, archive[-600:]
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""
