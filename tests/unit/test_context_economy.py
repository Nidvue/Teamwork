"""Context economy: machine views clip, the stored records never do (T-0003, M4.3).

Two behaviors are pinned here.

1. ``review --queue``, ``trace`` and ``archive`` render free-text evidence at
   600 characters and say how much they omitted (``... (+N chars: --full)``);
   ``--full`` on those same subcommands prints the whole value. The clipped text
   only ever leaves the *view*: Reviews.md, Ledger.jsonl, Archive.md and the task
   queues keep the whole string, and running a view rewrites none of them.
2. ``pr merge`` repoints the merged branch's Archive entry at the real merge
   revision. ``archive_append`` runs when the review passes - before anyone has
   merged - so it can only write ``pending``; the merge fixes that one field,
   idempotently, and says so when no entry names the branch.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine
from teamwork.names import clip

AGENTS = ("ceo", "developer-1", "reviewer-1", "reviewer-2")
LIMIT = engine.VIEW_CLIP_LIMIT

# Long single-line evidence: the sentinel sits at the very end, so it is visible
# only when nothing was omitted. No ``|`` or leading ``#`` - the values also have
# to survive the markdown field round-trip in TaskQueue.md and Reviews.md.
AUTHOR_HEAD = "author-head "
AUTHOR_TAIL = "zulu-author-tail-sentinel-9f2c"
AUTHOR_LONG = AUTHOR_HEAD + ("alpha-evidence-word " * 40) + AUTHOR_TAIL

REVIEWER_HEAD = "reviewer-head "
REVIEWER_TAIL = "bravo-reviewer-tail-sentinel-4b1d"
REVIEWER_LONG = REVIEWER_HEAD + ("bravo-verification-word " * 40) + REVIEWER_TAIL

# Long findings written by a failing review (the trace/queue view under test).
FINDINGS_HEAD = "finding-head "
FINDINGS_TAIL = "delta-finding-tail-sentinel-7a3e"
FINDINGS_LONG = FINDINGS_HEAD + ("charlie-finding-word " * 45) + FINDINGS_TAIL

assert len(AUTHOR_LONG) > LIMIT and len(REVIEWER_LONG) > LIMIT and len(FINDINGS_LONG) > LIMIT


def team_root(project: Path) -> Path:
    """The hidden team tree ``<project>/.pi/Teamwork/Teams/<Team>/``."""
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init_workspace(cli, project: Path, *, git: bool) -> Path:
    """Bootstrap a four-agent team; ``git`` also creates the work repo."""
    argv = ["--project", project, "init", "--agents", ",".join(AGENTS)]
    if not git:
        argv.append("--no-git")
    assert cli(*argv) == 0
    root = team_root(project)
    assert root.is_dir()
    return root


def queue_author_line(total: int = len(AUTHOR_LONG)) -> str:
    return f"    author evidence: {AUTHOR_LONG[:LIMIT]}... (+{total - LIMIT} chars: --full)"


def render(cli, capsys, *argv) -> str:
    """Return only what one view prints; the setup commands' output is dropped."""
    capsys.readouterr()
    assert cli(*argv) == 0
    return capsys.readouterr().out


def render_any(cli, capsys, *argv) -> str:
    """Like ``render`` but tolerant of the exit code (``loop`` returns 1 on CONTINUE)."""
    capsys.readouterr()
    cli(*argv)
    return capsys.readouterr().out


def task_to_review(cli, project: Path, root: Path) -> None:
    """Claim T-0001 with long author evidence and park it awaiting review."""
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
            AUTHOR_LONG,
        )
        == 0
    )
    assert cli("--project", project, "task", "next", "developer-1") == 0


def submitted_task(cli, project: Path, root: Path) -> None:
    """Claim T-0001 and submit it: only a submitted deliverable is in the queue."""
    task_to_review(cli, project, root)
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


def ship_and_open_pr(cli, project: Path, root: Path) -> None:
    """Full owner path up to an open PR: branch, commit, self-check, ``pr open``."""
    task_to_review(cli, project, root)
    ship_task(cli, project, "T-0001", "ship the clip helper", "feature.txt")


def ship_task(cli, project: Path, handle: str, title: str, filename: str) -> None:
    """Branch, commit, self-check and ``pr open`` for one already-claimed task."""
    assert (
        cli(
            "--project",
            project,
            "branch",
            "start",
            "--agent",
            "developer-1",
            "--task",
            handle,
        )
        == 0
    )
    (project / filename).write_text("done\n", encoding="utf-8")
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
            title,
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


# --------------------------------------------------------------------------- #
# the clip helper itself
# --------------------------------------------------------------------------- #


def test_clip_returns_short_text_unchanged() -> None:
    """Below the limit nothing is omitted, so nothing is added."""
    text = "x" * (LIMIT - 1)
    assert clip(text) == text
    assert clip(text, limit=LIMIT) == text
    assert clip("") == ""
    assert clip(None) == ""


def test_clip_at_the_limit_is_still_unchanged() -> None:
    """Exactly ``limit`` characters is not "longer than the limit"."""
    text = "y" * LIMIT
    assert clip(text) == text
    assert not clip(text).endswith("chars: --full)")


def test_clip_at_limit_plus_one_reports_one_omitted_character() -> None:
    text = "z" * (LIMIT + 1)
    assert clip(text) == "z" * LIMIT + "... (+1 chars: --full)"


def test_clip_keeps_the_head_and_counts_the_omitted_tail() -> None:
    """The head is verbatim and ``N`` is exactly the omitted character count."""
    text = "q" * (LIMIT + 400)
    out = clip(text)
    assert out.startswith("q" * LIMIT)
    assert out.endswith("... (+400 chars: --full)")
    assert len(out) == LIMIT + len("... (+400 chars: --full)")
    # a custom limit counts from the custom limit, not from 600
    assert clip("r" * 100, limit=60) == "r" * 60 + "... (+40 chars: --full)"


# --------------------------------------------------------------------------- #
# review --queue
# --------------------------------------------------------------------------- #


def test_review_queue_clips_author_evidence_by_default(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=False)
    submitted_task(cli, project, root)
    out = render(cli, capsys, "--project", project, "review", "--queue")
    assert queue_author_line() in out
    assert AUTHOR_TAIL not in out


def test_review_queue_full_prints_the_omitted_text(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=False)
    submitted_task(cli, project, root)
    out = render(cli, capsys, "--project", project, "review", "--queue", "--full")
    assert AUTHOR_TAIL in out
    assert AUTHOR_LONG in out
    assert "chars: --full)" not in out


def test_review_queue_clips_findings_too_and_counts_them(cli, project: Path, capsys) -> None:
    """A 10 KB findings line is the case the clip exists for."""
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
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
            "fail",
            "--evidence",
            "pytest @HEAD -> 1 failed",
            "--findings",
            FINDINGS_LONG,
        )
        == 0
    )
    # A fail returns the deliverable to the author; it re-enters the queue only on
    # re-submission, still carrying the findings.
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
            "fix the finding",
            "--test",
            "pytest @HEAD -> 1 passed",
        )
        == 0
    )
    out = render(cli, capsys, "--project", project, "review", "--queue")
    assert (
        f"    findings so far: {FINDINGS_LONG[:LIMIT]}... (+{len(FINDINGS_LONG) - LIMIT} chars: --full)"
        in out
    )
    assert FINDINGS_TAIL not in out
    out = render(cli, capsys, "--project", project, "review", "--queue", "--full")
    assert FINDINGS_LONG in out


# --------------------------------------------------------------------------- #
# trace
# --------------------------------------------------------------------------- #


def test_trace_clips_evidence_by_default(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=False)
    task_to_review(cli, project, root)
    out = render(cli, capsys, "--project", project, "trace", "T-0001")
    assert (
        f"- evidence: {AUTHOR_LONG[:LIMIT]}... (+{len(AUTHOR_LONG) - LIMIT} chars: --full)" in out
    )
    assert AUTHOR_TAIL not in out


def test_trace_full_prints_the_whole_evidence(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=False)
    task_to_review(cli, project, root)
    out = render(cli, capsys, "--project", project, "trace", "T-0001", "--full")
    assert AUTHOR_LONG in out
    assert "chars: --full)" not in out


# --------------------------------------------------------------------------- #
# archive
# --------------------------------------------------------------------------- #


def pass_review(cli, project: Path, capsys) -> None:
    """Ship T-0001 through an independent pass so the archive entry exists."""
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
            REVIEWER_LONG,
            # this module tests the merge path separately (merge_pr below), so the
            # pass records the verdict without landing it
            "--no-merge",
        )
        == 0
    )


def archive_clipped_line(root: Path, field: str) -> str:
    """What a clipped view must show for one stored archive line.

    The stored line carries whatever the review pass wrote in it (an evidence
    string plus the engine's own suffix), so the expected clipped rendering is
    derived from the file instead of hardcoding a character count.
    """
    stored = engine.archive_path(root).read_text(encoding="utf-8").split("\n")
    line = next(ln for ln in stored if ln.startswith(field))
    return field + engine.clip(line[len(field) :], LIMIT)


def test_archive_clips_evidence_lines_by_default(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    out = render(cli, capsys, "--project", project, "archive")
    assert archive_clipped_line(root, "- author evidence: ") in out
    assert archive_clipped_line(root, "- reviewer evidence: ") in out
    assert "chars: --full)" in out
    assert AUTHOR_TAIL not in out and REVIEWER_TAIL not in out


def test_archive_full_prints_the_whole_evidence(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    out = render(cli, capsys, "--project", project, "archive", "--full")
    assert AUTHOR_LONG in out and REVIEWER_LONG in out
    assert "chars: --full)" not in out


def test_archive_agent_view_clips_the_same_fields(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    out = render(cli, capsys, "--project", project, "archive", "--agent", "developer-1")
    assert AUTHOR_TAIL not in out and REVIEWER_TAIL not in out
    assert archive_clipped_line(root, "- author evidence: ") in out
    assert archive_clipped_line(root, "- reviewer evidence: ") in out
    out = render(cli, capsys, "--project", project, "archive", "--agent", "developer-1", "--full")
    assert AUTHOR_TAIL in out and REVIEWER_TAIL in out


# --------------------------------------------------------------------------- #
# the records keep what the view dropped
# --------------------------------------------------------------------------- #


def test_clipped_views_never_rewrite_the_stored_records(cli, project: Path, capsys) -> None:
    """Reading a clipped view is read-only: every record file is byte-identical."""
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)

    files = [
        root / "Reviews.md",
        root / "Ledger.jsonl",
        root / "Roles" / "Developer" / "TaskQueue.md",
        engine.archive_path(root),
    ]
    before = {p: p.read_bytes() for p in files}

    assert cli("--project", project, "review", "--queue") == 0
    assert cli("--project", project, "trace", "T-0001") == 0
    assert cli("--project", project, "archive") == 0

    for p in files:
        assert p.read_bytes() == before[p], f"{p.name} changed while only a view was rendered"

    reviews = (root / "Reviews.md").read_text(encoding="utf-8")
    assert REVIEWER_LONG in reviews, "the verdict note lost text the queue clipped"
    archive = engine.archive_path(root).read_text(encoding="utf-8")
    assert AUTHOR_LONG in archive and REVIEWER_LONG in archive
    ledger = (root / "Ledger.jsonl").read_text(encoding="utf-8")
    # the ledger has its own (pre-existing, pre-clipping) detail cap, so assert the
    # review event is still there with its own recorded summary and an intact chain
    assert "review.pass" in ledger
    assert REVIEWER_LONG[:60] in ledger
    assert cli("--project", project, "ledger", "verify") == 0


# --------------------------------------------------------------------------- #
# the archive merge sha
# --------------------------------------------------------------------------- #


def merge_pr(cli, project: Path, capsys) -> str:
    """Merge the approved PR of T-0001 and return the merge revision."""
    pr_id = engine.parse_reviews(root_reviews(project))[0]["id"]
    return merge_pr_by_id(cli, project, capsys, pr_id)


def merge_pr_by_id(cli, project: Path, capsys, pr_id: str) -> str:
    """Merge one approved PR and return the merge revision."""
    assert cli("--project", project, "pr", "merge", "--pr", pr_id, "--by", "reviewer-2") == 0
    out = capsys.readouterr().out
    merge_line = next(line for line in out.splitlines() if line.startswith("# merged "))
    return merge_line.split(" at ")[1].split(" by ")[0].strip()


def committed_archive(project: Path, rev: str = "HEAD") -> str:
    """The archive blob as the base branch actually stores it."""
    return engine.run_git(project, "show", f"{rev}:docs/Team/Archive.md").stdout


def root_reviews(project: Path) -> Path:
    return team_root(project) / "Reviews.md"


def archive_branch_merge_lines(root: Path) -> list:
    lines = engine.archive_path(root).read_text(encoding="utf-8").split("\n")
    return [line for line in lines if line.startswith("- branch / merge: ")]


def test_merged_branch_records_the_real_merge_sha_in_archive(cli, project: Path, capsys) -> None:
    """A merged branch's archive entry stops claiming ``pending``, exactly once."""
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)

    before = engine.archive_path(root).read_text(encoding="utf-8")
    assert "- branch / merge: pending" not in before
    assert " / pending" in before, "the review pass should still write pending"

    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]
    sha = merge_pr(cli, project, capsys)

    after = engine.archive_path(root).read_text(encoding="utf-8")
    assert archive_branch_merge_lines(root) == [f"- branch / merge: {branch} / {sha}"], (
        "exactly one entry, updated in place"
    )
    assert "pending" not in "\n".join(archive_branch_merge_lines(root))
    # only that field moved: every other archive line is untouched
    others_before = [ln for ln in before.split("\n") if not ln.startswith("- branch / merge: ")]
    others_after = [ln for ln in after.split("\n") if not ln.startswith("- branch / merge: ")]
    assert others_before == others_after
    task = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]
    assert task["merge_commit"] == sha
    # the fix is in the branch's history, not only in the work tree: the base
    # branch HEAD carries the real sha, and the work tree is left clean
    committed = committed_archive(project)
    assert f"- branch / merge: {branch} / {sha}" in committed
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""
    assert engine.run_git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"


def add_and_ship_second_task(cli, project: Path, capsys) -> tuple:
    """A second, independent deliverable: T-0002 shipped, passed and merged."""
    root = team_root(project)
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "ship the second helper",
            "--priority",
            "P1",
        )
        == 0
    )
    assert cli("--project", project, "task", "next", "developer-1") == 0
    ship_task(cli, project, "T-0002", "ship the second helper", "second.txt")
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0002",
            "--by",
            "reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest @HEAD -> 1 passed",
        )
        == 0
    )
    pr_id = [p["id"] for p in engine.parse_reviews(root_reviews(project)) if p["task"] == "T-0002"][
        0
    ]
    return root, merge_pr_by_id(cli, project, capsys, pr_id)


def test_two_consecutive_merges_both_succeed_in_one_work_repo(cli, project: Path, capsys) -> None:
    """The rewrite is committed, so the next merge does not die on a dirty tree.

    Regression for the P-0022 blocker: the merge used to leave
    ``docs/Team/Archive.md`` modified-but-uncommitted, and the next
    ``pr merge`` failed with "Your local changes ... would be overwritten by
    checkout: docs/Team/Archive.md".
    """
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    first_branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]
    first_sha = merge_pr(cli, project, capsys)

    # the second merge must not be blocked by leftover changes from the first
    _, second_sha = add_and_ship_second_task(cli, project, capsys)

    committed = committed_archive(project)
    assert f"- branch / merge: {first_branch} / {first_sha}" in committed
    assert " / pending" not in committed
    second_branch = next(
        t["branch"]
        for t in engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")
        if t["id"] == "T-0002"
    )
    assert f"- branch / merge: {second_branch} / {second_sha}" in committed
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""
    assert cli("--project", project, "archive") == 0


def test_archive_rewrite_is_a_commit_by_the_reviewer(cli, project: Path, capsys) -> None:
    """The sha lands as its own Reviewer record commit, not as stray work tree state."""
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]
    sha = merge_pr(cli, project, capsys)

    body = engine.run_git(project, "log", "-1", "--format=%B").stdout
    subject = engine.run_git(project, "log", "-1", "--format=%s").stdout
    changed = engine.run_git(project, "show", "--name-only", "--format=", "HEAD").stdout.split()
    assert "Acting role: Reviewer" in body
    assert changed == ["docs/Team/Archive.md"], "the record commit touches only the archive"
    assert "record the merge revision" in subject, "the rewrite is its own recorded commit"
    assert branch in body and sha in body
    assert engine.run_git(project, "log", "-1", "--format=%an").stdout.strip() == "Reviewer"
    # the rewrite is itself a ledger record, so the sha is traceable
    records = [r for r in engine.ledger_read(root) if r["action"] == "pr.merge.archive"]
    assert len(records) == 1
    assert records[0]["actor"] == "Reviewer-2"
    assert sha in records[0]["detail"] and records[0]["rev"]


def test_archive_merge_sha_rewrite_is_idempotent(cli, project: Path, capsys) -> None:
    """Re-running the close-out commits nothing and prints the no-change line."""
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]
    sha = merge_pr(cli, project, capsys)
    pr = engine.parse_reviews(root_reviews(project))[0]

    head_before = engine.run_git(project, "rev-parse", "HEAD").stdout.strip()
    before = engine.archive_path(root).read_bytes()
    message = engine.commit_archive_merge_sha(root, project, branch, sha, pr, "reviewer-2")
    assert "already records the merge" in message
    assert engine.archive_path(root).read_bytes() == before
    assert engine.run_git(project, "rev-parse", "HEAD").stdout.strip() == head_before
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""
    assert archive_branch_merge_lines(root)[0].endswith(f"/ {sha}")


def test_archive_merge_sha_without_a_matching_entry_reports_it(cli, project: Path, capsys) -> None:
    """No entry names the branch: say so, and leave the file exactly as it was."""
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    merge_pr(cli, project, capsys)
    pr = engine.parse_reviews(root_reviews(project))[0]

    head_before = engine.run_git(project, "rev-parse", "HEAD").stdout.strip()
    before = engine.archive_path(root).read_bytes()
    message = engine.commit_archive_merge_sha(
        root, project, "developer-9/t-0042-never-archived", "0" * 40, pr, "reviewer-2"
    )
    assert "no entry names branch developer-9/t-0042-never-archived" in message
    assert engine.archive_path(root).read_bytes() == before
    assert "0000000000000000000000000000000000000000" not in engine.archive_path(root).read_text(
        encoding="utf-8"
    )
    assert engine.run_git(project, "rev-parse", "HEAD").stdout.strip() == head_before
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""
    assert cli("--project", project, "archive") == 0


def test_find_pr_ignores_the_record_of_a_different_branch() -> None:
    """A reworked task keeps its old PR; the branch says which record is live."""
    old = engine.new_pr(
        "ship the clip helper", task="T-0001", branch="developer-1/t-0001-old", status="merged"
    )
    new = engine.new_pr(
        "ship the clip helper", task="T-0001", branch="developer-1/t-0001-new", status="approved"
    )
    prs = [old, new]

    assert engine.find_pr(prs, "T-0001") == 0, "without a branch the first record still wins"
    assert engine.find_pr(prs, "T-0001", "developer-1/t-0001-new") == 1
    assert engine.find_pr_exact(prs, "T-0001", "developer-1/t-0001-new") == 1
    assert engine.find_pr_exact(prs, "T-0001", "developer-1/t-0001-gone") is None


def test_merge_lookup_resolves_a_reworked_task_to_its_live_pr(cli, project: Path) -> None:
    """``pr merge --pr T-0001`` must not land on the PR that is already merged.

    The task id alone matches the first PR record naming the task, and after a
    rework that record is the one whose branch already sits in the base: the
    merge would report "already merged" and leave the live branch unmerged.
    """
    root = init_workspace(cli, project, git=True)
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
        )
        == 0
    )
    tpath = root / "Roles" / "Developer" / "TaskQueue.md"
    tasks = engine.parse_tasks(tpath)
    live_branch = engine.branch_name("developer-1", tasks[0]["id"], tasks[0]["title"])
    tasks[0]["branch"] = live_branch
    tasks[0]["claimed_by"] = "developer-1"
    tasks[0]["status"] = "review"
    engine.write_tasks(tpath, tasks, "developer")

    reviews = root_reviews(project)
    engine.write_reviews(
        reviews,
        [
            engine.new_pr(
                "ship the clip helper",
                task=tasks[0]["id"],
                branch=live_branch + "-previous",
                status="merged",
            ),
            engine.new_pr(
                "ship the clip helper",
                task=tasks[0]["id"],
                branch=live_branch,
                status="approved",
            ),
        ],
    )

    idx = engine._merge_pr_index(engine.parse_reviews(reviews), tasks[0]["id"], live_branch)
    assert idx is not None
    assert engine.parse_reviews(reviews)[idx]["branch"] == live_branch
    assert engine.parse_reviews(reviews)[idx]["status"] == "approved"


def test_rewrite_leaves_an_earlier_merge_of_the_same_branch_intact(
    cli, project: Path, capsys
) -> None:
    """A reworked task reuses its branch name; the earlier merge must survive.

    The second review appends a fresh entry with ``pending``, and both entries
    then name the same branch. Rewriting every match would overwrite the first
    merge revision with the second and silently destroy the record of the first
    merge, so only the newest pending entry may move.
    """
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]
    first_sha = merge_pr(cli, project, capsys)
    pr = engine.parse_reviews(root_reviews(project))[0]

    # a second review round appends the same branch again, awaiting its merge
    path = engine.archive_path(root)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text + f"\n## T-0001 · rework  (developer)\n- branch / merge: {branch} / pending\n",
        encoding="utf-8",
    )
    second_sha = "beef123"

    message = engine.commit_archive_merge_sha(root, project, branch, second_sha, pr, "reviewer-2")
    assert "now records the merge at beef123" in message
    lines = archive_branch_merge_lines(root)
    assert lines == [
        f"- branch / merge: {branch} / {first_sha}",
        f"- branch / merge: {branch} / {second_sha}",
    ], "the earlier merge revision is still recorded"
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


def test_rewrite_reports_when_the_branch_has_no_pending_entry(cli, project: Path, capsys) -> None:
    """Every entry for the branch is already resolved: say so, change nothing."""
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]
    sha = merge_pr(cli, project, capsys)
    pr = engine.parse_reviews(root_reviews(project))[0]

    head_before = engine.run_git(project, "rev-parse", "HEAD").stdout.strip()
    message = engine.commit_archive_merge_sha(root, project, branch, "cafe456", pr, "reviewer-2")
    assert "has no entry awaiting its merge revision" in message
    assert archive_branch_merge_lines(root) == [f"- branch / merge: {branch} / {sha}"]
    assert engine.run_git(project, "rev-parse", "HEAD").stdout.strip() == head_before
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


def test_reworked_task_records_each_merge_revision_of_its_reused_branch(
    cli, project: Path, capsys
) -> None:
    """Both rounds of a reworked task end up in the archive, each with its own sha.

    A rework reuses the deterministic branch name, so the archive holds two
    entries for one branch. The second entry must start at ``pending`` (the
    task still carries the first round's ``merge_commit``, and stamping that in
    would claim the new work merged at the old revision), and the second merge
    must repoint exactly that entry.
    """
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    branch = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]["branch"]
    first_sha = merge_pr(cli, project, capsys)

    # the Reviewer sends the merged task back, and the same owner takes it again
    assert (
        cli(
            "--project",
            project,
            "task",
            "reclaim",
            "developer",
            "T-0001",
            "--as",
            "developer-1",
            "--reason",
            "the reviewer asked for a follow-up",
        )
        == 0
    )
    assert cli("--project", project, "task", "set", "developer", "T-0001", "--status", "doing") == 0
    ship_task(cli, project, "T-0001", "first deliverable", "second_pass.txt")
    pass_review(cli, project, capsys)

    pending_lines = [ln for ln in archive_branch_merge_lines(root) if ln.endswith("/ pending")]
    assert pending_lines == [f"- branch / merge: {branch} / pending"], (
        "the rework's entry awaits its own merge revision"
    )

    second_sha = merge_pr(cli, project, capsys)
    assert second_sha != first_sha
    assert archive_branch_merge_lines(root) == [
        f"- branch / merge: {branch} / {first_sha}",
        f"- branch / merge: {branch} / {second_sha}",
    ], "each round keeps its own merge revision"
    committed = committed_archive(project)
    assert f"- branch / merge: {branch} / {first_sha}" in committed
    assert f"- branch / merge: {branch} / {second_sha}" in committed
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


# --------------------------------------------------------------------------- #
# loop and archive: the two views read on every iteration
# --------------------------------------------------------------------------- #


def test_loop_collapses_passing_records_and_clips_long_lines(cli, project: Path, capsys) -> None:
    """A stop check needs the failures, not the successes, and not 600 chars each."""
    root = init_workspace(cli, project, git=False)
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            "unit",
            "--area",
            "core",
            "--command",
            "pytest -q",
        )
        == 0
    )
    record = engine.parse_tests(engine.tests_path(root))[0]
    record["status"] = "passing"
    record["evidence"] = AUTHOR_LONG
    engine.write_tests(engine.tests_path(root), [record])

    out = render_any(cli, capsys, "--project", project, "loop")
    assert AUTHOR_TAIL not in out, "a passing record's evidence is not needed to decide"
    assert "passing record(s)" in out, "the collapsed count must be stated, not hidden"
    assert "`loop --full`" in out

    full = render_any(cli, capsys, "--project", project, "loop", "--full")
    assert AUTHOR_LONG in full, "--full must print the record whole"
    assert "passing record(s)" not in full


def test_loop_clips_a_long_failing_line_and_names_the_flag(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=False)
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            "unit",
            "--area",
            "core",
            "--command",
            "pytest -q",
        )
        == 0
    )
    record = engine.parse_tests(engine.tests_path(root))[0]
    record["status"] = "failing"
    record["evidence"] = REVIEWER_LONG
    engine.write_tests(engine.tests_path(root), [record])

    out = render_any(cli, capsys, "--project", project, "loop")
    assert "line(s) clipped" in out
    assert REVIEWER_TAIL not in out
    assert REVIEWER_HEAD in out, "a clipped line keeps its head: it must still be triageable"
    assert REVIEWER_LONG in render_any(cli, capsys, "--project", project, "loop", "--full")


def test_archive_listing_shows_the_most_recent_entries(cli, project: Path, capsys) -> None:
    """The evidence ledger grows forever; a listing shows the tail by default."""
    init_workspace(cli, project, git=False)
    target = project / "docs" / "Team" / "Archive.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    body = [engine.ARCHIVE_HEADER.rstrip(), ""]
    for i in range(1, 13):
        body += [
            f"## T-{i:04d} · entry {i}  (developer)",
            "- date: 2026-10-19",
            f"- author evidence: entry-{i}-evidence",
            f"- branch / merge: b{i} / sha{i}",
            "",
        ]
    target.write_text("\n".join(body), encoding="utf-8")

    out = render(cli, capsys, "--project", project, "archive")
    assert "of 12 entries" in out and "`archive --all`" in out
    assert "entry-12-evidence" in out, "the newest entry must always be listed"
    assert "entry-1-evidence" not in out, "the oldest entry is what the default drops"

    everything = render(cli, capsys, "--project", project, "archive", "--all")
    assert "of 12 entries" not in everything
    assert "entry-1-evidence" in everything and "entry-12-evidence" in everything

    limited = render(cli, capsys, "--project", project, "archive", "--limit", "2")
    assert "of 12 entries" in limited
    assert "entry-11-evidence" in limited and "entry-10-evidence" not in limited


# --------------------------------------------------------------------------- #
# quoted evidence is not authored markdown
# --------------------------------------------------------------------------- #


def test_archive_quoted_evidence_is_not_link_checked(tmp_path: Path) -> None:
    """A quoted finding must not fail the link check of the tree that quotes it.

    ``archive_append`` copies another agent's verdict verbatim, so the entry can
    carry a link whose target lived in the author's revision (``compare/v1.0.2...HEAD``
    in a quoted changelog) or a bare URL inside quoted prose. That text is evidence,
    not a link the team maintains: T-0032 and T-0035 each hand-backticked instances
    and the next accepted result re-broke the check.
    """
    docs = tmp_path / "docs" / "Team"
    docs.mkdir(parents=True)
    (docs / "Archive.md").write_text(
        engine.ARCHIVE_HEADER + "\n## T-0001 · shipped  (developer)\n"
        "- date: 2026-10-19\n"
        "- findings history: FAIL @abc123. CHANGELOG.md:12 links "
        "[Unreleased](compare/v1.0.2...HEAD) and see https://github.com/Nidvue/Teamwork\n"
        "- reviewer evidence: PASS. Quoted [changelog](compare/v1.0.2...v1.1.0) too.\n"
        "\n## Authored section\n"
        "[real](missing.md)\n",
        encoding="utf-8",
    )

    report = engine.link_report(tmp_path, tmp_path)
    assert report["bare"] == [], "a URL inside quoted evidence is not an authored bare URL"
    broken_targets = [target for _, _, target, _ in report["broken"]]
    assert broken_targets == ["missing.md"], "authored links must still be checked"


def test_archive_masks_a_credential_shape_quoted_as_evidence(tmp_path: Path) -> None:
    """A verdict may quote a FAKE token to prove a rule fires; the archive must not keep it.

    ``archive_append`` quotes another agent's words verbatim, and the shipped
    privacy gate keeps its credential rules armed inside a quotation by design, so
    committing a probe value turns the gate red on a later revision - and the only
    "fix" left then is widening the allowlist, the one thing the gate prevents.
    The claim stays readable; the shape is rewritten.
    """
    token = "sk-" + "live-" + "0123456789abcdef0123456789abcdef"
    password = "PASS" + 'WORD="' + "hunter2 passphrase" + '"'
    t = {
        "id": "T-0001",
        "title": "probe",
        "priority": "P0",
        "branch": "dev/t-0001",
        "self_note": "re-read the scanner",
        "evidence": f"a token on the exempted line is still reported: {token} -> api-token",
        "review_evidence": f"reproduced with {password} on the line",
        "findings": "-",
        "merge_commit": "",
    }
    engine.archive_append(tmp_path, "developer", t, repo=tmp_path)
    text = (tmp_path / "docs" / "Team" / "Archive.md").read_text(encoding="utf-8")

    assert token not in text, "the raw token must never reach the archive"
    assert "hunter2 passphrase" not in text
    assert "<redacted-api-token>" in text and "<redacted-env-secret>" in text
    # The claim the evidence makes survives, so the record is still worth reading.
    assert "still reported" in text and "-> api-token" in text


def test_the_archive_mask_covers_every_credential_rule_the_gate_arms(tmp_path: Path) -> None:
    """The mask borrows the scanner's rule table, so it cannot cover only some rules.

    A hand-written mask covered 2 of the gate's 5 credential rules, so a verdict
    quoting a private-key header, a JSON secret or a bare high-entropy value was
    archived raw and the shipped gate then failed on the archive itself.
    """
    pem = "-----" + "BEGIN RSA PRIVATE KEY" + "-----"
    high = "A1b2C3d4" + "E5f6G7h8" + "I9j0K1l2" + "M3n4O5p6"
    shapes = {
        "api-token": "sk-" + "live-" + "0123456789abcdef0123456789abcdef",
        "private-key": pem,
        "env-secret": "PASS" + 'WORD="' + "hunter2 passphrase" + '"',
        "json-secret": '{"api' + 'Key": "' + high + '"}',
        "high-entropy-secret": high,
    }
    for rule, value in shapes.items():
        t = {
            "id": "T-0001",
            "title": "probe",
            "priority": "P0",
            "branch": "dev/t-0001",
            "self_note": "re-read the scanner",
            "evidence": f"the {rule} rule fires on {value}",
            "review_evidence": "-",
            "findings": "-",
            "merge_commit": "",
        }
        engine.archive_append(tmp_path, "developer", t, repo=tmp_path)
    text = (tmp_path / "docs" / "Team" / "Archive.md").read_text(encoding="utf-8")

    for rule, value in shapes.items():
        assert value not in text, f"the raw {rule} value must never reach the archive"
        assert f"<redacted-{rule}>" in text, f"the {rule} value must be named, not merely cut"


def test_the_archive_mask_covers_the_entry_header(tmp_path: Path) -> None:
    """The title is agent-written text in the same record, so it is masked too."""
    token = "sk-" + "live-" + "0123456789abcdef0123456789abcdef"
    t = {
        "id": "T-0003",
        "title": f"leak {token} in the title",
        "priority": "P1",
        "branch": "dev/t-0002",
        "self_note": "-",
        "evidence": "-",
        "review_evidence": "-",
        "findings": "-",
        "merge_commit": "",
    }
    engine.archive_append(tmp_path, "developer", t, repo=tmp_path)
    text = (tmp_path / "docs" / "Team" / "Archive.md").read_text(encoding="utf-8")

    assert token not in text
    assert "<redacted-api-token>" in text


def test_the_archive_mask_leaves_ordinary_prose_alone(tmp_path: Path) -> None:
    """Masking is the gate's own finding set: naming a rule must not edit prose.

    The mask used to fire at 12 characters after ``sk-`` while the gate requires
    16, so a helper or task named ``sk-...`` was rewritten in the immutable record
    for a value the gate never reported.
    """
    t = {
        "id": "T-0002",
        "title": "prose",
        "priority": "P1",
        "branch": "dev/t-0002",
        "self_note": "re-read the gate",
        "evidence": "the api-token rule fires on a token; PASSWORD must be at least 8 chars",
        "review_evidence": "short=1 stays, and a bare word sk-live is not a token",
        "findings": "-",
        "merge_commit": "",
    }
    engine.archive_append(tmp_path, "developer", t, repo=tmp_path)
    text = (tmp_path / "docs" / "Team" / "Archive.md").read_text(encoding="utf-8")

    assert "the api-token rule fires on a token" in text
    assert "PASSWORD must be at least 8 chars" in text
    assert "sk-live is not a token" in text


def test_the_archive_mask_does_not_rewrite_a_helper_name_or_a_sha(tmp_path: Path) -> None:
    """A shape the gate would not report must pass through byte-identical."""
    sha = "a" * 40
    prose = (
        "we ran sk-learn-pipeline tests, the sk-timeout-wrapper helper, "
        f"GITHUB_TOKEN=abcdefgh and commit {sha} unchanged"
    )
    t = {
        "id": "T-0004",
        "title": "prose",
        "priority": "P2",
        "branch": "dev/t-0003",
        "self_note": prose,
        "evidence": "-",
        "review_evidence": "-",
        "findings": "-",
        "merge_commit": "",
    }
    engine.archive_append(tmp_path, "developer", t, repo=tmp_path)
    text = (tmp_path / "docs" / "Team" / "Archive.md").read_text(encoding="utf-8")

    assert prose in text, "a value the gate does not report must not be masked"


def test_the_archive_mask_follows_the_gate_for_json_config_shapes(tmp_path: Path) -> None:
    """The JSON arm must use the gate's filters, not the bare regex.

    The mask took ``_RE_JSON_SECRET`` matches directly, so a placeholder or a code
    reference the gate deliberately accepts (``${API_KEY}``, ``replace_me``,
    ``process.env.KEY``) was rewritten in the immutable record - the mask
    over-firing on text the author never wrote. The gate's own ``scan_lines`` is
    the only source now, in both directions.
    """
    accepted = [
        '{"api_key": "your-key-here"}',
        '{"apiKey": "replace_me"}',
        '{"token": "changeme"}',
        '{"api_key": "process.env.KEY"}',
        '{"api_key": "${API_KEY}"}',
        '{"api_key": "<your-key>"}',
        '{"password": "example"}',
        '{"secret": "none"}',
    ]
    for line in accepted:
        assert (
            list(engine._privacy_scan().scan_lines(line, "", "a", engine._privacy_scan().RULES, ()))
            == []
        )
        assert engine.mask_secret_shapes(line) == line, (
            f"the gate accepts this, so it must survive: {line}"
        )

    # Built at runtime and not named like a credential: the gate would (rightly)
    # report either a literal high-entropy value or a secret-named assignment.
    blob = "A1b2C3d4" + "E5f6G7h8" + "I9j0K1l2" + "M3n4O5p6"
    line = '{"apiKey": "' + blob + '"}'
    assert engine.mask_secret_shapes(line) == '{"apiKey": "<redacted-json-secret>"}'


def test_the_archive_mask_and_the_gate_agree_on_every_probe(tmp_path: Path) -> None:
    """One table, both directions: masked iff the gate reports it."""
    scanner = engine._privacy_scan()
    sha = "a" * 40
    probes = [
        '{"api_key": "${API_KEY}"}',
        "sk-learn-pipeline",
        "the sk-timeout-wrapper helper",
        "GITHUB_TOKEN=abcdefgh",
        sha,
        "ordinary prose sentence.",
        "https://example.com/x",
        "docs/Team/Archive.md:6467",
    ]
    for line in probes:
        reported = list(scanner.scan_lines(line, "", "a", scanner.RULES, ()))
        assert not reported, f"probe must be invisible to the gate: {line}"
        assert engine.mask_secret_shapes(line) == line, (
            f"the gate is silent, so the mask must be too: {line}"
        )
