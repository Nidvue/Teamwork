"""Integration: the context-economy contract holds across a real merge.

The unit layer (``tests/unit/test_context_economy.py``) pins the clip helper and
the archive rewrite in isolation. This layer drives the whole thing the way a
team does: initialise a team, ship a task, get an independent pass, then
``pr merge`` against a real git repository - and asserts the contract on what
the repository and the on-disk records actually say afterwards.

The contract, as agreed for M8:

1. ``pr merge`` records the merge revision in the *committed* Archive.md entry
   of the merged branch, in the Reviewer's own ``chore(records)`` commit, and
   the ledger keeps ``pr.merge`` before ``pr.merge.archive``.
2. ``review --queue``, ``trace`` and ``archive`` clip free-text evidence to
   ``VIEW_CLIP_LIMIT`` and say how much they dropped; ``--full`` restores the
   whole string. Only the view clips - the stored records keep every character.
3. Rendering a clipped view is read-only: no record file changes and the ledger
   chain still verifies.

Scope note: the milestone asked for an ``archive sync`` subcommand as a second
way to reconcile the archive. That command was deliberately *not* shipped -
``pr merge`` now performs the reconciliation itself - so this layer asserts the
shipped surface instead of a command that does not exist.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

AGENTS = "ceo,developer-1,reviewer-1,reviewer-2"
LIMIT = engine.VIEW_CLIP_LIMIT

# Evidence long enough to be clipped, with a sentinel at the very end so its
# presence in a view proves nothing was omitted. No ``|`` and no leading ``#``:
# both values have to survive the markdown field round-trip.
AUTHOR_HEAD = "author-head "
AUTHOR_TAIL = "zulu-author-tail-sentinel-9f2c"
AUTHOR_LONG = AUTHOR_HEAD + ("alpha-evidence-word " * 40) + AUTHOR_TAIL

REVIEWER_HEAD = "reviewer-head "
REVIEWER_TAIL = "bravo-reviewer-tail-sentinel-4b1d"
REVIEWER_LONG = REVIEWER_HEAD + ("bravo-verification-word " * 40) + REVIEWER_TAIL

FINDINGS_HEAD = "finding-head "
FINDINGS_TAIL = "delta-finding-tail-sentinel-7a3e"
FINDINGS_LONG = FINDINGS_HEAD + ("charlie-finding-word " * 45) + FINDINGS_TAIL

assert len(AUTHOR_LONG) > LIMIT and len(REVIEWER_LONG) > LIMIT
assert len(FINDINGS_LONG) > LIMIT


# --------------------------------------------------------------------------- #
# workspace driving
# --------------------------------------------------------------------------- #


def team_root(project: Path) -> Path:
    """The hidden team tree ``<project>/.pi/Teamwork/Teams/<Team>/``."""
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path, *, git: bool = True) -> Path:
    argv = ["--project", project, "init", "--agents", AGENTS]
    if not git:
        argv.append("--no-git")
    assert cli(*argv) == 0
    return team_root(project)


def add_task(cli, project: Path, title: str = "ship the clip helper") -> None:
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            title,
            "--priority",
            "P0",
            "--evidence",
            AUTHOR_LONG,
        )
        == 0
    )


def ship(cli, project: Path, handle: str = "T-0001") -> None:
    """Owner path: branch, commit, self-check, ``pr open``."""
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli("--project", project, "branch", "start", "--agent", "developer-1", "--task", handle)
        == 0
    )
    (project / "feature.txt").write_text("done\n", encoding="utf-8")
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
            handle,
            "--area",
            "core",
            "--goal",
            "ship the clip helper",
            "--deliverable",
            "feature.txt",
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
        cli("--project", project, "task", "set", "developer", handle, "--status", "selfcheck") == 0
    )
    assert (
        cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            handle,
            "--by",
            "developer-1",
            "--note",
            "re-read the diff",
            "--test",
            "pytest @HEAD -> 1 passed",
        )
        == 0
    )
    assert cli("--project", project, "task", "set", "developer", handle, "--status", "review") == 0
    assert cli("--project", project, "pr", "open", "--agent", "developer-1", "--task", handle) == 0


def pass_review(cli, project: Path, handle: str = "T-0001", evidence: str = REVIEWER_LONG) -> None:
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            handle,
            "--by",
            "reviewer-1",
            "--result",
            "pass",
            "--evidence",
            evidence,
            "--replay",
            "pytest -q tests/integration",
            "--no-merge",
        )
        == 0
    )


def fail_review(cli, project: Path, handle: str = "T-0001") -> None:
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            handle,
            "--by",
            "reviewer-1",
            "--result",
            "fail",
            "--evidence",
            "pytest @HEAD -> 1 failed",
            "--findings",
            FINDINGS_LONG,
        )
        == 0
    )


def merge(cli, capsys, project: Path) -> str:
    """Merge the single approved PR and return the merge revision."""
    capsys.readouterr()
    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-2") == 0
    out = capsys.readouterr().out
    line = next(ln for ln in out.splitlines() if ln.startswith("# merged "))
    return line.split(" at ")[1].split(" by ")[0].strip()


def render(cli, capsys, *argv) -> str:
    """Run one view and return only what it printed."""
    capsys.readouterr()
    assert cli(*argv) == 0
    return capsys.readouterr().out


def stored_evidence(root: Path, handle: str = "T-0001") -> str:
    """The task record's own evidence string, as the queue and trace print it.

    The engine appends the commit revision to the field at self-check time, so
    the whole value - and therefore the clipped rendering - has to be derived
    from the record instead of from what the test wrote.
    """
    for role in engine.list_roles(root):
        for t in engine.parse_tasks(engine.task_file(root, role)):
            if t["id"] == handle:
                return t["evidence"]
    raise AssertionError(f"no task {handle} in {root}")


def committed_archive(project: Path, rev: str = "HEAD") -> str:
    """The archive blob exactly as the base branch stores it."""
    return engine.run_git(project, "show", f"{rev}:docs/Team/Archive.md").stdout


def merged_repo(cli, capsys, project: Path) -> tuple[Path, str]:
    """Initialise, ship T-0001, pass its review, merge it; return (root, sha)."""
    root = init(cli, project)
    add_task(cli, project)
    ship(cli, project)
    pass_review(cli, project)
    sha = merge(cli, capsys, project)
    return root, sha


# --------------------------------------------------------------------------- #
# 1. pr merge lands the merge revision in the committed archive
# --------------------------------------------------------------------------- #


def test_merge_commits_an_archive_entry_naming_the_merge_revision(
    cli, project: Path, capsys
) -> None:
    """The entry on the base branch stops saying ``pending`` and names the sha."""
    _root, sha = merged_repo(cli, capsys, project)

    committed = committed_archive(project)
    assert "ship the clip helper" in committed
    assert f"developer-1/t-0001-ship-the-clip-helper / {sha}" in committed
    assert "developer-1/t-0001-ship-the-clip-helper / pending" not in committed
    # the entry exists exactly once - the rewrite edits the line, never duplicates it
    assert committed.count("- branch / merge: developer-1/t-0001-ship-the-clip-helper") == 1


def test_the_archive_rewrite_is_its_own_reviewer_commit(cli, project: Path, capsys) -> None:
    """``pr merge`` leaves the archive fix in a commit the Reviewer authored."""
    merged_repo(cli, capsys, project)

    log = engine.run_git(project, "log", "-3", "--format=%H%x00%an%x00%ae%x00%s").stdout
    rows = [line for line in log.splitlines() if line.strip()]
    assert len(rows) >= 2, log

    head_sha, _name, head_email, head_subject = rows[0].split("\x00", 3)
    assert "Archive.md" in head_subject
    assert head_email.endswith("@agents.nidvue.com"), head_email
    assert head_email.startswith("reviewer"), f"archive commit author: {head_email}"
    # the commit really touches only the archive record
    changed = engine.run_git(project, "show", "--name-only", "--format=", head_sha).stdout.split()
    assert changed == ["docs/Team/Archive.md"], changed

    # the merge itself is the parent commit, so the recorded sha is reachable
    parent = engine.run_git(project, "rev-parse", f"{head_sha}^").stdout.strip()
    assert committed_archive(project, parent).count(" / pending") >= 1


def test_ledger_records_the_merge_before_the_archive_rewrite(cli, project: Path, capsys) -> None:
    """Order matters: the merge is evidence before the record fix that cites it."""
    root, sha = merged_repo(cli, capsys, project)

    actions = [rec.get("action") for rec in engine.ledger_read(root)]
    assert "pr.merge" in actions and "pr.merge.archive" in actions
    assert actions.index("pr.merge") < actions.index("pr.merge.archive")

    archive_rec = next(r for r in engine.ledger_read(root) if r.get("action") == "pr.merge.archive")
    assert sha in str(archive_rec), archive_rec
    assert cli("--project", project, "ledger", "verify") == 0


def test_the_worktree_is_clean_after_the_merge_rewrites_the_archive(
    cli, project: Path, capsys
) -> None:
    """The rewrite stages, commits and leaves nothing behind."""
    merged_repo(cli, capsys, project)
    porcelains = engine.run_git(project, "status", "--porcelain").stdout.strip()
    assert porcelains == "", porcelains


# --------------------------------------------------------------------------- #
# 2. the three machine views clip, and --full restores
# --------------------------------------------------------------------------- #


def test_archive_view_over_a_merged_repo_clips_and_full_restores(
    cli, project: Path, capsys
) -> None:
    """The post-merge archive is the big file: clipped by default, whole on --full."""
    root, sha = merged_repo(cli, capsys, project)

    clipped = render(cli, capsys, "--project", project, "archive")
    assert AUTHOR_TAIL not in clipped and REVIEWER_TAIL not in clipped
    assert "chars: --full)" in clipped
    # non-evidence lines are untouched, including the merge revision we just wrote
    assert f"developer-1/t-0001-ship-the-clip-helper / {sha}" in clipped
    # the clipped rendering is derived from the stored line, not a hardcoded count
    stored_lines = committed_archive(project).split("\n")
    for field in ("- author evidence: ", "- reviewer evidence: "):
        stored = next(ln for ln in stored_lines if ln.startswith(field))
        assert field + engine.clip(stored[len(field) :], LIMIT) in clipped

    whole = render(cli, capsys, "--project", project, "archive", "--full")
    assert AUTHOR_LONG in whole and REVIEWER_LONG in whole
    assert "chars: --full)" not in whole


def test_archive_agent_view_clips_on_a_merged_repo_too(cli, project: Path, capsys) -> None:
    """The per-agent listing shares the same field list and the same limit."""
    merged_repo(cli, capsys, project)

    clipped = render(cli, capsys, "--project", project, "archive", "--agent", "developer-1")
    assert AUTHOR_TAIL not in clipped and REVIEWER_TAIL not in clipped
    assert "chars: --full)" in clipped

    whole = render(cli, capsys, "--project", project, "archive", "--agent", "developer-1", "--full")
    assert AUTHOR_TAIL in whole and REVIEWER_TAIL in whole


def test_review_queue_clips_the_findings_of_a_failing_verdict(cli, project: Path, capsys) -> None:
    """A 10 KB findings line is the case the clip exists for."""
    init(cli, project)
    add_task(cli, project)
    ship(cli, project)
    fail_review(cli, project)

    root = team_root(project)
    clipped = render(cli, capsys, "--project", project, "review", "--queue")
    expected = (
        f"    findings so far: {FINDINGS_LONG[:LIMIT]}"
        f"... (+{len(FINDINGS_LONG) - LIMIT} chars: --full)"
    )
    assert expected in clipped
    assert FINDINGS_TAIL not in clipped
    # the author evidence of the same deliverable clips on the same rule, and the
    # stored value carries the engine's own ``; commit <sha>`` suffix
    author = stored_evidence(root)
    assert author.startswith(AUTHOR_LONG)
    assert f"    author evidence: {engine.clip(author, LIMIT)}" in clipped
    assert AUTHOR_TAIL not in clipped

    whole = render(cli, capsys, "--project", project, "review", "--queue", "--full")
    assert FINDINGS_LONG in whole and AUTHOR_LONG in whole
    assert "chars: --full)" not in whole


def test_trace_clips_both_evidence_fields_and_full_restores(cli, project: Path, capsys) -> None:
    """``trace`` is the audit view: same clipping, and --full brings it all back."""
    merged_repo(cli, capsys, project)

    author = stored_evidence(team_root(project))
    clipped = render(cli, capsys, "--project", project, "trace", "T-0001")
    assert f"- evidence: {engine.clip(author, LIMIT)}" in clipped
    assert AUTHOR_TAIL not in clipped and REVIEWER_TAIL not in clipped

    whole = render(cli, capsys, "--project", project, "trace", "T-0001", "--full")
    assert AUTHOR_LONG in whole and REVIEWER_TAIL in whole
    assert "chars: --full)" not in whole


def test_a_short_value_is_printed_whole_with_no_omission_marker(cli, project: Path, capsys) -> None:
    """Clipping must not touch records that already fit."""
    init(cli, project)
    short = "short evidence @abc123 -> 3 passed"
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "ship the clip helper",
            "--priority",
            "P0",
            "--evidence",
            short,
        )
        == 0
    )
    assert cli("--project", project, "task", "next", "developer-1") == 0

    queue = render(cli, capsys, "--project", project, "review", "--queue")
    assert f"    author evidence: {short}" in queue
    assert "chars: --full)" not in queue

    trace = render(cli, capsys, "--project", project, "trace", "T-0001")
    assert short in trace
    assert "chars: --full)" not in trace


# --------------------------------------------------------------------------- #
# 3. only the view clips - the stored records keep every character
# --------------------------------------------------------------------------- #


def test_rendering_clipped_views_over_a_merged_repo_rewrites_nothing(
    cli, project: Path, capsys
) -> None:
    """Read-only means read-only: byte-identical files and a valid chain."""
    root, _sha = merged_repo(cli, capsys, project)

    watched = [
        root / "Reviews.md",
        root / "Ledger.jsonl",
        root / "Roles" / "Developer" / engine.F_TASKS,
        engine.archive_path(root),
    ]
    before = {path: path.read_bytes() for path in watched}

    assert cli("--project", project, "review", "--queue", "--full") == 0
    assert cli("--project", project, "review", "--queue") == 0
    assert cli("--project", project, "trace", "T-0001") == 0
    assert cli("--project", project, "archive") == 0
    assert cli("--project", project, "archive", "--full") == 0

    for path in watched:
        assert path.read_bytes() == before[path], f"{path.name} changed while only a view ran"

    # the whole text is still in the records the clipped views summarised
    reviews = (root / "Reviews.md").read_text(encoding="utf-8")
    assert REVIEWER_LONG in reviews
    archive_text = engine.archive_path(root).read_text(encoding="utf-8")
    assert AUTHOR_LONG in archive_text and REVIEWER_LONG in archive_text
    assert cli("--project", project, "ledger", "verify") == 0


# --------------------------------------------------------------------------- #
# 4. the shipped surface: no ``archive sync``, reconciliation rides on pr merge
# --------------------------------------------------------------------------- #


def test_archive_sync_is_not_a_command_and_pr_merge_reconciles_instead(
    cli, project: Path, capsys
) -> None:
    """The milestone's ``archive sync`` was dropped; ``pr merge`` owns the fix."""
    _root, sha = merged_repo(cli, capsys, project)

    # no such subcommand: the parser refuses it rather than silently doing nothing
    # (the ``cli`` fixture turns the parser's SystemExit into its exit code)
    assert cli("--project", project, "archive", "sync") not in (0, None)

    # and the reconciliation it was meant to provide already happened, exactly once
    committed = committed_archive(project)
    assert committed.count(f" / {sha}") == 1
    assert " / pending" not in committed
