"""Acceptance: `teamwork.py links` tells the truth about the tree it measured.

``links`` answers one question for the team's committed prose: **does every
document's claim about another document hold?** CI keys on its exit code, so the
promises below are the reader's, not the author's:

1. a clean committed tree passes (exit ``0``, ``# issues: 0``);
2. a broken internal link fails the release gate (exit ``1``, exact issue line);
3. a malformed external URL is caught, and a proper ``https://`` URL is not, so
   the gate cannot pass by rejecting everything;
4. the gate reports the tree under the caller - including a per-instance
   worktree, which lives under ``.pi/`` and was once skipped whole, making the
   check pass vacuously;
5. reciprocity is a separate promise: a ``docs/`` file nothing links back to is
   reported, ``--no-reciprocity`` drops exactly that class, and a broken link
   still fails.

Every test drives the shipped CLI as a subprocess against a throwaway tree, so
nothing here asserts an internal call a user never makes.

Owner: reviewer-1. Task: T-0004. Requirement: M9-K, area ``links``.
"""

from __future__ import annotations

import re
from pathlib import Path

from cli_harness import run_shim
from gate_fixtures import checkout

AREA = "links"
DOCS = Path("docs") / "Team"
AGENTS = Path("AGENTS.md")

#: The line a broken link must produce. CI and a reviewer both read this string,
#: so it is pinned exactly rather than by keyword.
BROKEN_LINE = "- docs/Team/A.md: [gone](Missing.md) - target does not exist"


def write(root: Path, rel: Path | str, text: str) -> Path:
    """Write one markdown file, creating its parents."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def doc(title: str, body: str = "") -> str:
    """A document shaped like the team's own: H1, owner, related links."""
    return f"# {title}\n\nOwner: acceptance fixture.\n\n{body}".rstrip() + "\n"


def reciprocal_pair(root: Path) -> None:
    """``docs/Team/A.md`` <-> ``docs/Team/B.md``: the minimum clean graph."""
    write(root, DOCS / "A.md", doc("A", "Related: [B](B.md)"))
    write(root, DOCS / "B.md", doc("B", "Related: [A](A.md)"))


def issues(result) -> int:
    """The count the gate prints as its verdict line."""
    match = re.search(r"^# issues: (\d+)$", result.stdout, re.M)
    assert match, f"the gate printed no verdict line:\n{result.stdout}"
    return int(match.group(1))


def files_scanned(result) -> int:
    """How many markdown files the gate says it read."""
    match = re.search(r"^# (\d+) markdown file\(s\)", result.stdout, re.M)
    assert match, f"the gate reported no file count:\n{result.stdout}"
    return int(match.group(1))


def run_links(tree: Path, *extra: str):
    """Run the user's command against ``tree`` and return the finished process."""
    return run_shim(["links", "--project", str(tree), "--team", "Acceptance", *extra])


def test_a_clean_committed_tree_passes(tmp_path):
    """ACCEPT: a checkout whose documents agree -> exit 0 and `# issues: 0`.

    The subject is the real committed tree (``checkout`` copies the tracked file
    set, so no ``.git``/``.pi``/caches), with the minimal reciprocal pair added:
    the shape every document in it must already have.
    """
    tree = checkout(tmp_path / "clone")
    assert (tree / AGENTS).is_file(), "the committed tree carries no AGENTS.md"
    reciprocal_pair(tree)

    result = run_links(tree)

    assert result.returncode == 0, (
        "the link check CI blocks on fails for a clean committed tree:\n"
        f"{result.stdout}\n{result.stderr}"
    )
    assert issues(result) == 0, result.stdout
    # A check that reads nothing is not an acceptance. The pair we added must be
    # visible in the count, or the "clean" verdict means "not looked at".
    assert files_scanned(result) >= len(list(tree.rglob("*.md")))


def test_a_broken_link_fails_the_release_gate(tmp_path):
    """ACCEPT: one broken link -> exit 1 and the exact issue line.

    The exit code is the promise: CI keys on it, not on the prose.
    """
    tree = tmp_path / "tree"
    reciprocal_pair(tree)
    write(tree, DOCS / "A.md", doc("A", "Related: [B](B.md) and [gone](Missing.md)"))

    result = run_links(tree)

    assert result.returncode == 1, (
        f"a tree with a broken link was accepted (exit {result.returncode}):\n{result.stdout}"
    )
    assert BROKEN_LINE in result.stdout, (
        f"the broken link was not reported as {BROKEN_LINE!r}:\n{result.stdout}"
    )
    assert issues(result) == 1, result.stdout


def test_a_malformed_external_url_is_caught(tmp_path):
    """ACCEPT: `www.` and a bare domain are rejected; a real URL is accepted.

    The accepted case is in the same tree on purpose: a gate that flagged every
    external target would satisfy the rejections while being useless.
    """
    tree = tmp_path / "tree"
    reciprocal_pair(tree)
    write(
        tree,
        DOCS / "B.md",
        doc(
            "B",
            "Related: [A](A.md)\n\n"
            "[www](www.example.com) [bare](example.org) [ok](https://example.com/guide)",
        ),
    )

    result = run_links(tree)

    assert result.returncode == 1, result.stdout
    assert "- docs/Team/B.md: [www](www.example.com) - use a full https:// URL" in result.stdout
    # A bare domain is not a URL either, but it is caught on the other path: it
    # resolves as a relative file that does not exist, which is the honest reason.
    assert "- docs/Team/B.md: [bare](example.org) - target does not exist" in result.stdout
    assert "https://example.com/guide" not in result.stdout, (
        f"a valid https:// URL was reported as a defect:\n{result.stdout}"
    )


def test_the_gate_is_honest_about_the_tree_it_measured(tmp_path):
    """ACCEPT: inside a worktree under `.pi/`, the gate reads that worktree.

    This is the regression the area exists for. ``iter_markdown`` once tested
    ``SKIP_DIRS`` against the *absolute* path, so every file under
    ``.pi/.../Worktrees/<Instance>`` was skipped and the check passed while
    scanning zero files - the worst possible failure for a release gate.
    """
    tree = checkout(tmp_path / ".pi" / "Teamwork" / "Teams" / "Acceptance" / "Worktrees" / "Dev")
    reciprocal_pair(tree)
    write(tree, DOCS / "A.md", doc("A", "Related: [B](B.md) and [gone](Missing.md)"))
    readable = len(list(tree.rglob("*.md")))

    result = run_links(tree)

    assert str(tree) in result.stdout, (
        f"the gate did not name the tree it measured ({tree}):\n{result.stdout}"
    )
    assert files_scanned(result) == readable, (
        f"the gate read {files_scanned(result)} of {readable} markdown file(s) in "
        f"a worktree: a skipped tree passes vacuously.\n{result.stdout}"
    )
    assert result.returncode == 1, (
        f"a worktree with a broken link passed the gate:\n{result.stdout}"
    )
    assert BROKEN_LINE in result.stdout, result.stdout


def test_reciprocity_is_a_separate_promise(tmp_path):
    """ACCEPT: a one-way docs/ link is reported, and `--no-reciprocity` drops it.

    Both runs are asserted: the opt-out must remove exactly the back-link class,
    not the release gate. A flag that also silenced broken links would let a
    reader hit a dead end on the strength of a green run.
    """
    tree = tmp_path / "tree"
    reciprocal_pair(tree)
    # Orphan links to A; nothing links to Orphan, so A owes Orphan a back-link.
    write(tree, DOCS / "Orphan.md", doc("Orphan", "Related: [A](A.md)"))
    write(tree, DOCS / "A.md", doc("A", "Related: [B](B.md) and [gone](Missing.md)"))

    strict = run_links(tree)

    assert strict.returncode == 1, strict.stdout
    assert "## missing back-links" in strict.stdout, strict.stdout
    assert (
        "- docs/Team/Orphan.md links to docs/Team/A.md but docs/Team/A.md does not link back"
        in strict.stdout
    ), strict.stdout
    assert BROKEN_LINE in strict.stdout, strict.stdout

    relaxed = run_links(tree, "--no-reciprocity")

    assert relaxed.returncode == 1, (
        f"--no-reciprocity also silenced a broken link:\n{relaxed.stdout}"
    )
    assert "## missing back-links" not in relaxed.stdout, (
        f"--no-reciprocity kept the back-link section:\n{relaxed.stdout}"
    )
    assert BROKEN_LINE in relaxed.stdout, relaxed.stdout
    assert issues(strict) == issues(relaxed) + 1, (
        "the opt-out changed more than the one missing back-link:\n"
        f"strict={issues(strict)} relaxed={issues(relaxed)}\n{strict.stdout}"
    )
