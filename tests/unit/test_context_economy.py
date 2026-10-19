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


def ship_and_open_pr(cli, project: Path, root: Path) -> None:
    """Full owner path up to an open PR: branch, commit, self-check, ``pr open``."""
    task_to_review(cli, project, root)
    assert (
        cli(
            "--project",
            project,
            "branch",
            "start",
            "--agent",
            "developer-1",
            "--task",
            "T-0001",
        )
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
            "T-0001",
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
    task_to_review(cli, project, root)
    out = render(cli, capsys, "--project", project, "review", "--queue")
    assert queue_author_line() in out
    assert AUTHOR_TAIL not in out


def test_review_queue_full_prints_the_omitted_text(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=False)
    task_to_review(cli, project, root)
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
    assert cli("--project", project, "pr", "merge", "--pr", pr_id, "--by", "reviewer-2") == 0
    out = capsys.readouterr().out
    merge_line = next(line for line in out.splitlines() if line.startswith("# merged "))
    return merge_line.split(" at ")[1].split(" by ")[0].strip()


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


def test_archive_merge_sha_rewrite_is_idempotent(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    sha = merge_pr(cli, project, capsys)

    before = engine.archive_path(root).read_bytes()
    message = engine.archive_set_merge_sha(root, "developer-1/t-0001-ship-the-clip-helper", sha)
    assert "already records the merge" in message
    assert engine.archive_path(root).read_bytes() == before
    assert archive_branch_merge_lines(root)[0].endswith(f"/ {sha}")


def test_archive_merge_sha_without_a_matching_entry_reports_it(cli, project: Path, capsys) -> None:
    """No entry names the branch: say so, and leave the file exactly as it was."""
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    merge_pr(cli, project, capsys)

    before = engine.archive_path(root).read_bytes()
    message = engine.archive_set_merge_sha(root, "developer-9/t-0042-never-archived", "0" * 40)
    assert "no entry names branch developer-9/t-0042-never-archived" in message
    assert engine.archive_path(root).read_bytes() == before
    assert "0000000000000000000000000000000000000000" not in engine.archive_path(root).read_text(
        encoding="utf-8"
    )
    assert cli("--project", project, "archive") == 0
