"""Every instance works in its own worktree; the shared checkout is the exception.

The contract, in the order a lane meets it:

* `branch start` creates the task's worktree and leaves the shared checkout on the
  default branch, so two lanes of one repository never share a writable tree;
* the recorded path is relative to the team root - an absolute host path in a queue
  is disclosure to every lane that reads it, and the record mask can rewrite a
  directory path that looks high-entropy, which silently points the record at a
  tree that does not exist;
* the worktree carries the project's toolchain link, so the project gate command
  runs there unchanged;
* `commit --task` refuses from the shared checkout when the task owns a worktree;
* `preflight` fails its `tree` check when the command ran in a different tree than
  the task records, and its gate runs in the task's tree;
* `--shared` is the documented exception and records no worktree.
"""

from __future__ import annotations

from pathlib import Path

from support import in_lane, lane_cli, lane_tree, team_root
from teamwork import engine

AGENTS = ("ceo", "developer-1", "reviewer-1")


def init_team(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ",".join(AGENTS)) == 0
    return team_root(project)


def start_task(cli, project: Path, *, shared: bool = False) -> None:
    assert cli("--project", project, "task", "add", "developer", "ship it", "--priority", "P0") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    argv = ["--project", project, "branch", "start", "--agent", "developer-1", "--task", "T-0001"]
    if shared:
        argv += ["--shared", "--reason", "the test needs the shared checkout"]
    assert cli(*argv) == 0


def record(project: Path) -> dict:
    root = team_root(project)
    for item in engine.parse_tasks(engine.task_file(root, "developer")):
        if item["id"] == "T-0001":
            return item
    raise AssertionError("T-0001 not on the developer queue")


def test_branch_start_gives_the_task_its_own_worktree(cli, project: Path) -> None:
    """The default: a worktree exists, the shared checkout did not move."""
    root = init_team(cli, project)
    start_task(cli, project)

    task = record(project)
    recorded = task["worktree"]
    assert recorded, "the task must record the worktree it works in"
    assert not Path(recorded).is_absolute(), "a recorded host path is disclosure to every lane"
    tree = engine.task_worktree(root, task)
    assert tree.is_dir()
    assert (tree / ".git").exists()
    assert engine.current_branch(project) == "main"
    assert engine.current_branch(tree) == task["branch"]


def test_the_toolchain_link_lets_the_gate_command_run_in_the_worktree(cli, project: Path) -> None:
    """A worktree carries tracked files only; the venv is linked, not copied."""
    (project / ".venv" / "bin").mkdir(parents=True)
    (project / ".venv" / "bin" / "ruff").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    init_team(cli, project)
    start_task(cli, project)

    tree = lane_tree(project, "T-0001")
    link = tree / ".venv"
    assert link.is_symlink() or link.is_dir()
    assert (link / "bin" / "ruff").is_file()


def test_commit_from_the_shared_checkout_is_refused(cli, project: Path, capsys) -> None:
    """Two guards, two messages: the branch guard first, then the worktree guard."""
    init_team(cli, project)
    start_task(cli, project)
    tree = lane_tree(project, "T-0001")
    (project / "feature.txt").write_text("done\n", encoding="utf-8")
    capsys.readouterr()

    argv = (
        "--project",
        project,
        "commit",
        "--role",
        "developer",
        "--task",
        "T-0001",
        "--type",
        "feat",
        "--goal",
        "ship it",
        "--deliverable",
        "feature.txt",
        "--why",
        "the task asks for it",
        "--status",
        "implemented",
        "--result",
        "true @rev -> ok",
        "--all",
    )
    assert cli(*argv) == 2
    first = capsys.readouterr().err
    assert "belongs to" in first, "on the default branch the branch guard refuses first"

    assert cli(*argv, "--allow-main") == 2
    second = capsys.readouterr().err
    assert "owns the worktree" in second, (
        "with the branch guard bypassed the worktree guard refuses"
    )
    assert str(tree) in second, "the refusal must name the worktree to cd into"
    assert engine.current_branch(project) == "main"

    with in_lane(project, "T-0001") as work:
        (work / "feature.txt").write_text("done\n", encoding="utf-8")
        assert (
            cli(
                "--project",
                project,
                "commit",
                "--role",
                "developer",
                "--task",
                "T-0001",
                "--type",
                "feat",
                "--goal",
                "ship it",
                "--deliverable",
                "feature.txt",
                "--why",
                "the task asks for it",
                "--status",
                "implemented",
                "--result",
                "true @rev -> ok",
                "--all",
            )
            == 0
        )


def commit_feature(cli, project: Path) -> None:
    """One committed change in the task's tree, so the branch check is not the reason."""
    with in_lane(project, "T-0001") as work:
        (work / "feature.txt").write_text("done\n", encoding="utf-8")
        assert (
            cli(
                "--project",
                project,
                "commit",
                "--role",
                "developer",
                "--task",
                "T-0001",
                "--type",
                "feat",
                "--goal",
                "ship it",
                "--deliverable",
                "feature.txt",
                "--why",
                "the task asks for it",
                "--status",
                "implemented",
                "--result",
                "true @rev -> ok",
                "--all",
            )
            == 0
        )


def test_preflight_refuses_a_command_that_ran_in_another_tree(cli, project: Path, capsys) -> None:
    """A green gate that measured the shared checkout says nothing about the branch."""
    init_team(cli, project)
    start_task(cli, project)
    commit_feature(cli, project)

    capsys.readouterr()
    assert cli("--project", project, "preflight", "developer", "T-0001") == 1
    assert "- fail       tree" in capsys.readouterr().out

    with in_lane(project, "T-0001"):
        capsys.readouterr()
        assert cli("--project", project, "preflight", "developer", "T-0001") == 0
        assert "- ok         tree" in capsys.readouterr().out


def test_the_gate_runs_in_the_task_tree(cli, project: Path) -> None:
    """`PreflightCommand` runs in the task's tree: the branch's file is visible."""
    import json

    root = init_team(cli, project)
    start_task(cli, project)
    commit_feature(cli, project)
    settings = root / "Settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["PreflightCommand"] = "test -f feature.txt"
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    with in_lane(project, "T-0001"):
        assert cli("--project", project, "preflight", "developer", "T-0001", "--run") == 0


def test_shared_is_the_exception_and_records_no_worktree(cli, project: Path) -> None:
    """`--shared` switches the shared checkout, records why, and records no worktree."""
    init_team(cli, project)
    start_task(cli, project, shared=True)

    task = record(project)
    assert not task.get("worktree")
    assert task["shared_reason"] == "the test needs the shared checkout"
    assert engine.current_branch(project) == task["branch"]
    assert not (team_root(project) / "Runtime" / "Worktrees").exists() or not any(
        (team_root(project) / "Runtime" / "Worktrees").rglob("T-0001")
    )


def test_shared_without_a_recorded_reason_is_refused(cli, project: Path, capsys) -> None:
    """AC-GIT-4: the isolation default cannot be bypassed silently."""
    init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "ship it", "--priority", "P0") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    capsys.readouterr()

    argv = ("--project", project, "branch", "start", "--agent", "developer-1", "--task", "T-0001")
    assert cli(*argv, "--shared") == 2
    err = capsys.readouterr().err
    assert "refusing --shared" in err
    assert "--reason" in err
    assert not record(project).get("shared_reason")

    assert cli(*argv, "--shared", "--reason", "pinned toolchain in the shared tree") == 0
    assert record(project)["shared_reason"] == "pinned toolchain in the shared tree"


def author_and_submit(cli, project: Path, task: str, filename: str) -> None:
    """One committed, self-checked, reviewed change in the task's own worktree."""
    run = lane_cli(cli, project, task)
    (lane_tree(project, task) / filename).write_text("done\n", encoding="utf-8")
    assert (
        run(
            "--project",
            project,
            "commit",
            "--role",
            "developer",
            "--type",
            "feat",
            "--task",
            task,
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
    assert cli("--project", project, "task", "set", "developer", task, "--status", "selfcheck") == 0
    assert (
        run(
            "--project",
            project,
            "selfcheck",
            "developer",
            task,
            "--by",
            "developer-1",
            "--note",
            "re-read the diff",
            "--test",
            "pytest @HEAD -> 1 passed",
        )
        == 0
    )
    assert cli("--project", project, "task", "set", "developer", task, "--status", "review") == 0
    assert run("--project", project, "pr", "open", "--agent", "developer-1", "--task", task) == 0


def two_tasks_in_two_worktrees(cli, project: Path) -> None:
    """Two tasks, each in its own worktree, both branched from the same base."""
    for title in ("ship the first", "ship the second"):
        assert cli("--project", project, "task", "add", "developer", title, "--priority", "P0") == 0
    for task in ("T-0001", "T-0002"):
        assert cli("--project", project, "task", "next", "developer-1") == 0
        assert (
            cli(
                "--project",
                project,
                "branch",
                "start",
                "--agent",
                "developer-1",
                "--task",
                task,
            )
            == 0
        )


def task_record(project: Path, task: str) -> dict:
    root = team_root(project)
    for role in engine.list_roles(root):
        for item in engine.parse_tasks(engine.task_file(root, role)):
            if item["id"] == task:
                return item
    raise AssertionError(f"{task} is not on any queue")


def approve(cli, project: Path, task: str) -> None:
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            task,
            "--by",
            "reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest @HEAD -> 1 passed",
            "--no-merge",
        )
        == 0
    )


def test_pr_merge_rebases_onto_a_moved_base_and_retires_the_worktree(
    cli, project: Path, capsys
) -> None:
    """AC-GIT-1 + AC-GIT-2: linear landing, and nothing of the task survives it.

    The second task lands first, so the first one's base has moved when its turn
    comes: the merge rebases it onto the new base and fast-forwards, so the base
    gains the task's one commit and no merge commit, and the task's worktree and
    branch are both gone afterwards.
    """
    init_team(cli, project)
    two_tasks_in_two_worktrees(cli, project)
    author_and_submit(cli, project, "T-0001", "one.txt")
    author_and_submit(cli, project, "T-0002", "two.txt")
    approve(cli, project, "T-0001")
    approve(cli, project, "T-0002")

    first_tree = lane_tree(project, "T-0001")
    first_branch = task_record(project, "T-0001")["branch"]
    assert first_tree.is_dir()
    assert cli("--project", project, "pr", "merge", "--pr", "P-0002", "--by", "reviewer-1") == 0
    before = engine.run_git(project, "rev-parse", "main").stdout.strip()
    capsys.readouterr()

    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-1") == 0
    out = capsys.readouterr().out
    after = engine.run_git(project, "rev-parse", "main").stdout.strip()

    assert "# rebased " in out, out
    assert after != before
    assert (
        engine.run_git(
            project, "rev-list", "--merges", "--count", f"{before}..{after}"
        ).stdout.strip()
        == "0"
    ), "rebase-then-land must not add a merge commit"
    subjects = engine.run_git(
        project, "log", "--format=%s", f"{before}..{after}"
    ).stdout.splitlines()
    assert len([s for s in subjects if s.startswith("feat(core)")]) == 1, subjects
    assert engine.run_git(project, "cat-file", "-e", "main:one.txt").returncode == 0
    assert engine.run_git(project, "merge-base", "--is-ancestor", before, after).returncode == 0

    assert not first_tree.exists(), "the merged task's worktree must be gone (AC-GIT-2)"
    assert engine.run_git(project, "branch", "--list", first_branch).stdout.strip() == ""
    assert "# retired worktree" in out, out


def test_merge_refuses_a_moved_base_it_cannot_rebase(cli, project: Path, capsys) -> None:
    """AC-GIT-1: a moved base that cannot be rebased is refused, and the rebase named.

    No worktree holds the branch, so the rebase is the owner's step: the merge
    refuses, names the command, and leaves the base untouched.
    """
    init_team(cli, project)
    two_tasks_in_two_worktrees(cli, project)
    author_and_submit(cli, project, "T-0001", "one.txt")
    author_and_submit(cli, project, "T-0002", "two.txt")
    approve(cli, project, "T-0001")
    approve(cli, project, "T-0002")

    first_tree = lane_tree(project, "T-0001")
    assert engine.run_git(project, "worktree", "remove", "--force", str(first_tree)).returncode == 0
    assert cli("--project", project, "pr", "merge", "--pr", "P-0002", "--by", "reviewer-1") == 0
    before = engine.run_git(project, "rev-parse", "main").stdout.strip()
    capsys.readouterr()

    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-1") == 2
    err = capsys.readouterr().err
    assert "has moved" in err
    assert "rebase main" in err
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == before
    assert task_record(project, "T-0001").get("merge_commit") in ("", None)


def test_audit_reports_merged_branches_orphaned_worktrees_and_stale_refs(
    cli, project: Path, capsys
) -> None:
    """AC-GIT-3: one command reports all three kinds of leftover."""
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "ship it", "--priority", "P0") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli("--project", project, "branch", "start", "--agent", "developer-1", "--task", "T-0001")
        == 0
    )

    assert engine.run_git(project, "branch", "leftover", "main").returncode == 0
    orphan = root / engine.DIR_RUNTIME / engine.DIR_WORKTREES / "Dev-1" / "T-9999"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    assert engine.run_git(project, "worktree", "add", str(orphan), "leftover").returncode == 0

    origin = project.parent / "origin.git"
    assert engine.run_git(project, "init", "--bare", str(origin)).returncode == 0
    assert engine.run_git(project, "remote", "add", "origin", str(origin)).returncode == 0
    assert engine.run_git(project, "push", "-q", "origin", "main").returncode == 0
    assert engine.run_git(project, "push", "-q", "origin", "main:gone").returncode == 0
    assert engine.run_git(project, "fetch", "-q", "origin").returncode == 0
    assert engine.run_git(origin, "update-ref", "-d", "refs/heads/gone").returncode == 0

    capsys.readouterr()
    assert cli("--project", project, "audit") == 1
    out = capsys.readouterr().out
    assert "- branch leftover is merged into main and still exists; delete it" in out, out
    assert f"- worktree {orphan.name} is on merged branch leftover; remove it" in out, out
    assert "- stale remote-tracking ref origin/gone" in out, out


def test_audit_is_clean_after_a_merge(cli, project: Path, capsys) -> None:
    """The audit's three questions are answered 'none' once the merge cleaned up."""
    init_team(cli, project)
    start_task(cli, project)
    author_and_submit(cli, project, "T-0001", "one.txt")
    approve(cli, project, "T-0001")
    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-1") == 0

    capsys.readouterr()
    cli("--project", project, "audit")
    out = capsys.readouterr().out
    section = out.split("## git leftovers", 1)[1].split("\n## ", 1)[0]
    assert section.strip().endswith("- none"), section
