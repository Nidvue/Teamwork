"""A Reviewer's pass lands with the real default-branch hook installed.

The R1 pre-commit hook refuses a commit on the default branch. The merge path
commits four times on that branch (records, squash, archive revision, board
render), so if it does not carry the override itself a Reviewer lane needs a human
to export `TEAMWORK_ALLOW_MAIN` before its pass can land - which is the opposite
of an unattended lane.

This drives the real hook (installed by `hooks install`, executing the shipped
rules) and then the real branch -> self-check -> PR -> review-pass path.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from support import in_lane, lane_cli
from teamwork import engine

AGENTS = ("ceo", "developer-1", "reviewer-1")


def team_root(project: Path) -> Path:
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def git(project: Path, *argv: str) -> subprocess.CompletedProcess:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("TEAMWORK_ALLOW_MAIN", "TEAMWORK_SKIP_HOOKS")
    }
    return subprocess.run(
        ["git", "-C", str(project), *argv], capture_output=True, text=True, env=env
    )


def write_shim(root: Path, repo_root: Path) -> None:
    """The hook runs ``<tree>/scripts/teamwork.py``; give a tree one that imports us."""
    shim = root / "scripts" / "teamwork.py"
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(repo_root / 'src')!r})\n"
        "from teamwork.cli import main\n"
        "raise SystemExit(main())\n",
        encoding="utf-8",
    )


def ignore_scripts(root: Path) -> None:
    """The shim is scaffolding, not a deliverable: keep it out of every tree's status."""
    ignore = root / ".gitignore"
    ignore.write_text(ignore.read_text(encoding="utf-8") + "\nscripts/\n", encoding="utf-8")


def install_real_hooks(cli, project: Path, repo_root: Path) -> None:
    """Install the shipped hooks, with a shim so they can import this tree."""
    write_shim(project, repo_root)
    ignore_scripts(project)
    assert git(project, "add", "-A").returncode == 0
    assert (
        git(
            project,
            "-c",
            "user.name=CEO",
            "-c",
            "user.email=ceo@agents.nidvue.com",
            "commit",
            "-qm",
            "chore(init): commit what init wrote",
        ).returncode
        == 0
    )
    assert cli("--project", project, "hooks", "install") == 0


def test_a_review_pass_lands_with_the_default_branch_hook_installed(
    cli, project: Path, repo_root: Path
) -> None:
    assert cli("--project", project, "init", "--agents", ",".join(AGENTS)) == 0
    root = team_root(project)
    install_real_hooks(cli, project, repo_root)

    assert cli("--project", project, "task", "add", "developer", "ship it", "--priority", "P0") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli("--project", project, "branch", "start", "--agent", "developer-1", "--task", "T-0001")
        == 0
    )
    author = lane_cli(cli, project, "T-0001")
    with in_lane(project, "T-0001") as tree:
        write_shim(tree, repo_root)
        ignore_scripts(tree)
        (tree / "feature.txt").write_text("done\n", encoding="utf-8")
    assert (
        author(
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
            "feature.txt",
            "--why",
            "the task asked for it",
            "--status",
            "implemented",
            "--result",
            "true @rev -> ok",
            "--paths",
            "feature.txt,.gitignore",
        )
        == 0
    )
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "selfcheck")
        == 0
    )
    assert (
        author(
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
            "true @rev -> ok",
        )
        == 0
    )
    assert (
        cli("--project", project, "pr", "open", "--agent", "developer-1", "--task", "T-0001") == 0
    )

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
            "true @rev -> ok",
        )
        == 0
    )
    task = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]
    assert task["status"] == "done"
    assert task.get("merge_commit")
    assert engine.branch_exists(project, task["branch"]) is False
    log = git(project, "log", "--oneline", engine.DEFAULT_BASE)
    assert "merge" in log.stdout.lower(), log.stderr


def test_the_same_hook_still_refuses_a_lane_committing_on_the_default_branch(
    cli, project: Path, repo_root: Path
) -> None:
    assert cli("--project", project, "init", "--agents", ",".join(AGENTS)) == 0
    install_real_hooks(cli, project, repo_root)

    (project / "direct.txt").write_text("not on a branch\n", encoding="utf-8")
    git(project, "add", "direct.txt")
    refused = git(
        project,
        "-c",
        "user.name=Developer",
        "-c",
        "user.email=developer@agents.nidvue.com",
        "commit",
        "-m",
        "chore: a lane committing straight to main",
    )
    assert refused.returncode != 0
    assert "refusing to commit on 'main'" in refused.stderr
