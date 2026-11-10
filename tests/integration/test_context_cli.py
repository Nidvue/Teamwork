"""Integration: the frozen ``ctx://`` context tree through the shipped CLI.

Layer ``integration``, area ``context``, owner Tester (T-0005). Every case
spawns ``scripts/teamwork.py`` as a subprocess against a throwaway team (never
the live tree, never an in-process engine call), so what is measured is exactly
what a lane runs. The oracle is ``docs/Team/Architecture.md`` section 16:

* 16.1 - every URI resolves to an existing file or record; unsafe segments and
  unknown URIs exit 2; a missing store reads as an empty store;
* 16.2 - L0/L1/L2 are computed at read time with the frozen shapes;
* 16.3 - ``ls``/``tree``/``read``/``find``/``stats``/``digest`` defaults and
  outputs, and every one of them is read-only;
* 16.4 - ``find`` scores exactly, ties break by URI, ``--scope`` is a hard
  prefix and ``find`` never reads L2.

The fixture is built with the real commands (``init``, ``knowledge add``,
``lesson add``, ``remember``, ``global``, ``skill create``, ``task add``) so the
tree is the one those commands leave behind. The only exception is the two task
records that stand for a finished review (``review_status: failed`` with
findings, and ``status: done`` with a merge revision): only the review gate may
write those fields, so the fixture writes the record through the engine's own
task writer instead of pretending ``task add`` produced it. No test asserts on
that writer; ``digest`` is asserted on what the CLI prints.

Owner: tester. Layer: integration. Area: context.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from teamwork import config, engine

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SHIM = REPO_ROOT / "scripts" / "teamwork.py"

ROSTER = "ceo,developer-1,release-engineer,tester-1"

DOC_PROJECT = """# Project

The project builds the context tree and it is read-only.

## Goals

A node resolves to a file that already exists.
"""

SKILL_DESCRIPTION = "Distil a context node into a stable L0 line"
SKILL_BODY = "1. Read L1 before L2."

FIELD_LINE = re.compile(r"^- [a-z_]+: ")
FIND_LINE = re.compile(r"^- -?\d+ ctx://\S+ \[[a-z]+\] ")

FAILED_FINDINGS = "detects: no-fail | the CLI was not wired"


def run(project: Path, *argv: str) -> subprocess.CompletedProcess:
    """Run the shipped CLI against ``project``; never inherit an outer team."""
    env = os.environ.copy()
    env.pop("TEAMWORK_ROOT", None)
    env.pop("TEAMWORK_TEAM", None)
    env["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, str(CLI_SHIM), "--project", str(project), *map(str, argv)],
        cwd=str(project),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        timeout=120,
    )


def ok(project: Path, *argv: str) -> str:
    proc = run(project, *argv)
    assert proc.returncode == 0, (
        f"command {argv!r} exited {proc.returncode}, expected 0\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    return proc.stdout


def refused(project: Path, *argv: str, names: str = "") -> subprocess.CompletedProcess:
    proc = run(project, *argv)
    assert proc.returncode == 2, (
        f"command {argv!r} exited {proc.returncode}, expected 2\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    if names:
        assert names in proc.stderr, (names, proc.stderr)
    return proc


def team_root(project: Path) -> Path:
    return (
        project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def tree_hash(path: Path) -> str:
    """sha256 over every file under ``path``, name and bytes, path-sorted."""
    digest = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(item.relative_to(path).as_posix().encode())
        digest.update(item.read_bytes())
    return digest.hexdigest()


def seed_review_outcomes(project: Path) -> None:
    """Give T-0001 a failed review and T-0002 a merge, as the gates would."""
    queue = engine.role_dir(team_root(project), "developer") / config.F_TASKS
    tasks = engine.parse_tasks(queue)
    by_id = {task["id"]: task for task in tasks}
    by_id["T-0001"].update(
        {
            "status": "doing",
            "review_status": "failed",
            "review_fails": 2,
            "review_fail_rev": "abc1234",
            "findings": FAILED_FINDINGS,
            "branch": "developer/t-0001",
        }
    )
    by_id["T-0002"].update(
        {
            "status": "done",
            "review_status": "passed",
            "branch": "developer/t-0002",
            "merge_commit": "def5678",
        }
    )
    engine.write_tasks(queue, tasks, "developer")


@pytest.fixture(scope="module")
def ws(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One throwaway team with a record in every store section 16 addresses."""
    project = tmp_path_factory.mktemp("ctx") / "SampleProject"
    project.mkdir()
    ok(project, "init", "--agents", ROSTER, "--no-git")

    doc = project / "docs" / "Team" / "Project.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(DOC_PROJECT, encoding="utf-8")

    ok(
        project,
        "knowledge",
        "add",
        "--by",
        "Developer-1",
        "--topic",
        "Context tree",
        "--statement",
        "The tree is a read-only view over the stores.",
        "--evidence",
        "pytest @abc -> 1 passed",
        "--kind",
        "fact",
        "--tags",
        "context,tree",
        "--importance",
        "4",
    )
    ok(
        project,
        "knowledge",
        "add",
        "--by",
        "Developer-1",
        "--kind",
        "experience",
        "--topic",
        "Ranking",
        "--statement",
        "Importance then uses ranks the load rows.",
        "--evidence",
        "pytest zqxranktoken @abc -> 1 passed",
        "--tags",
        "ranking",
    )
    ok(
        project,
        "lesson",
        "add",
        "--by",
        "Developer-1",
        "--role",
        "developer",
        "--mistake",
        "Ship the parser before the CLI",
        "--cause",
        "The command was never wired",
        "--rule",
        "Run the command once before committing",
        "--evidence",
        "pytest @abc -> failed",
    )
    ok(
        project,
        "remember",
        "developer",
        "Read L1 before L2.",
        "--by",
        "Developer-1",
        "--key",
        "context",
        "--importance",
        "3",
        "--src",
        "T-0001",
    )
    ok(
        project,
        "remember",
        "developer",
        "Long-term fact about the tree.",
        "--by",
        "Developer-1",
        "--layer",
        "long",
        "--key",
        "tree",
        "--importance",
        "2",
    )
    ok(project, "global", "The context view is read-only.", "--key", "global", "--by", "CEO")
    ok(
        project,
        "skill",
        "create",
        "--name",
        "tw-context",
        "--for",
        SKILL_DESCRIPTION,
        "--by",
        "Developer-1",
        "--body",
        SKILL_BODY,
    )
    ok(project, "task", "add", "developer", "Digest a failed task", "--priority", "P1")
    ok(project, "task", "add", "developer", "Context find stays deterministic", "--priority", "P1")
    ok(project, "task", "add", "developer", "Still open", "--priority", "P2")
    seed_review_outcomes(project)
    return project


@pytest.fixture
def empty_team(tmp_path: Path) -> Path:
    """A team that never wrote Knowledge.md or Lessons.md."""
    project = tmp_path / "EmptyProject"
    project.mkdir()
    ok(project, "init", "--agents", "ceo,developer-1", "--no-git")
    return project


def test_ls_root_lists_the_three_namespaces(ws: Path) -> None:
    assert ok(ws, "context", "ls").splitlines() == [
        "- ctx://project [dir] 3 children",
        "- ctx://role [dir] 4 roles",
        "- ctx://global [dir] 1 child",
    ]


def test_ls_knowledge_lists_each_record_with_its_l0(ws: Path) -> None:
    assert ok(ws, "context", "ls", "ctx://project/knowledge").splitlines() == [
        "- ctx://project/knowledge/K-0001 [knowledge] [fact] Context tree: "
        "The tree is a read-only view over the stores.",
        "- ctx://project/knowledge/K-0002 [knowledge] [experience] Ranking: "
        "Importance then uses ranks the load rows.",
    ]


def test_ls_level_one_prints_the_child_l1_under_a_bare_header(ws: Path) -> None:
    lines = ok(ws, "context", "ls", "ctx://project/knowledge", "--level", "1").splitlines()
    assert lines[0] == "- ctx://project/knowledge/K-0001 [knowledge]"
    assert lines[1] == "  - statement: The tree is a read-only view over the stores."
    assert "- ctx://project/knowledge/K-0002 [knowledge]" in lines
    assert sum(1 for line in lines if line.startswith("- ctx://")) == 2
    assert all(line.startswith("  - ") for line in lines if not line.startswith("- ctx://"))


def test_ls_limit_zero_means_no_cap_and_positive_caps(ws: Path) -> None:
    assert len(ok(ws, "context", "ls", "ctx://project/knowledge", "--limit", "1").splitlines()) == 1
    assert len(ok(ws, "context", "ls", "ctx://project/knowledge", "--limit", "0").splitlines()) == 2
    refused(ws, "context", "ls", "ctx://project/knowledge", "--limit", "-1")


def test_tree_depth_and_default(ws: Path) -> None:
    default = ok(ws, "context", "tree").splitlines()
    assert default[0] == "- ctx:// 3 namespaces"
    assert "    - knowledge 2 records" in default
    assert "    - developer 3 children" in default
    assert not any(line.startswith("      - K-0001") for line in default)

    assert ok(ws, "context", "tree", "-L", "1").splitlines() == [
        "- ctx:// 3 namespaces",
        "  - project 3 children",
        "  - role 4 roles",
        "  - global 1 child",
    ]
    assert ok(ws, "context", "tree", "-L", "0").splitlines() == ["- ctx:// 3 namespaces"]

    knowledge = ok(ws, "context", "tree", "ctx://project/knowledge").splitlines()
    assert knowledge[0] == "- knowledge 2 records"
    assert knowledge[1].startswith("  - K-0001 [fact] Context tree: ")


READ_CASES = [
    (
        "knowledge-fact",
        "ctx://project/knowledge/K-0001",
        "fields",
        "[fact] Context tree: The tree is a read-only view over the stores.",
        "- statement: The tree is a read-only view over the stores.",
        None,
        "## K-0001 - Context tree",
        ("- statement: The tree is a read-only view over the stores.", "- kind: fact"),
    ),
    (
        "knowledge-experience",
        "ctx://project/knowledge/K-0002",
        "fields",
        "[experience] Ranking: Importance then uses ranks the load rows.",
        "- statement: Importance then uses ranks the load rows.",
        None,
        "## K-0002 - Ranking",
        ("- kind: experience", "- importance: 3"),
    ),
    (
        "lesson",
        "ctx://role/developer/lessons/L-0001",
        "fields",
        "[open] Ship the parser before the CLI",
        "- role: developer",
        None,
        "## L-0001 - Ship the parser before the CLI",
        ("- status: open", "- rule: Run the command once before committing"),
    ),
    (
        "short-memory",
        "ctx://role/developer/memory/short/M-0001",
        "fields",
        "Read L1 before L2.",
        "- key: context",
        None,
        "## M-0001 · context",
        ("- key: context", "- src: T-0001", "Read L1 before L2."),
    ),
    (
        "long-memory",
        "ctx://role/developer/memory/long/M-0001",
        "fields",
        "Long-term fact about the tree.",
        "- key: tree",
        None,
        "## M-0001 · tree",
        ("- key: tree", "Long-term fact about the tree."),
    ),
    (
        "global-memory",
        "ctx://global/memory/M-0001",
        "fields",
        "The context view is read-only.",
        "- key: global",
        None,
        "## M-0001 · global",
        ("- key: global", "The context view is read-only."),
    ),
    (
        "skill",
        "ctx://project/skills/tw-context",
        "headings",
        SKILL_DESCRIPTION,
        "- tw-context",
        "  - Steps",
        "---",
        ("name: tw-context", "1. Read L1 before L2."),
    ),
    (
        "doc",
        "ctx://project/docs/Team/Project.md",
        "headings",
        "Project: The project builds the context tree and it is read-only.",
        "- Project",
        "  - Goals",
        "# Project",
        ("A node resolves to a file that already exists.",),
    ),
    (
        "task",
        "ctx://role/developer/tasks/T-0003",
        "fields",
        "Still open",
        "- title: Still open",
        None,
        "## T-0003 · Still open",
        ("- status: todo",),
    ),
]


@pytest.mark.parametrize(
    ("name", "uri", "shape", "l0", "l1_head", "l1_child", "l2_head", "needles"),
    READ_CASES,
    ids=[case[0] for case in READ_CASES],
)
def test_read_computes_l0_l1_l2(
    ws: Path,
    name: str,
    uri: str,
    shape: str,
    l0: str,
    l1_head: str,
    l1_child: str | None,
    l2_head: str,
    needles: tuple,
) -> None:
    assert ok(ws, "context", "read", uri, "--level", "0").strip() == l0

    lines = ok(ws, "context", "read", uri).splitlines()
    assert lines, f"{name}: L1 is empty"
    assert lines[0] == l1_head, (name, lines[0])
    if l1_child:
        assert l1_child in lines, (name, l1_child)
    if shape == "fields":
        assert all(FIELD_LINE.match(line) for line in lines), (name, lines)
    else:
        assert all(line.startswith("- ") or line.startswith("  - ") for line in lines), (
            name,
            lines,
        )

    level_two = ok(ws, "context", "read", uri, "--level", "2")
    assert level_two.startswith(l2_head), (name, level_two.splitlines()[0])
    for needle in needles:
        assert needle in level_two, (name, needle)

    if shape == "headings":
        if uri.startswith("ctx://project/docs/"):
            path = ws / "docs" / uri[len("ctx://project/docs/") :]
        else:
            path = ws / ".agents" / "skills" / uri.rsplit("/", 1)[1] / "SKILL.md"
        assert level_two.rstrip("\n") == path.read_text(encoding="utf-8").rstrip("\n")


def test_read_directory_levels_and_l2_refusal(ws: Path) -> None:
    assert ok(ws, "context", "read", "ctx://project/knowledge", "--level", "0").strip() == (
        "2 records"
    )
    level_one = ok(ws, "context", "read", "ctx://project/knowledge").splitlines()
    assert level_one[0] == "# 2 records"
    assert level_one[1].startswith("- K-0001 [fact] Context tree: ")
    refused(
        ws,
        "context",
        "read",
        "ctx://project/knowledge",
        "--level",
        "2",
        names="is a directory; L2 is a record or a file",
    )


def test_read_root_level_one_counts_namespaces(ws: Path) -> None:
    lines = ok(ws, "context", "read", "ctx://", "--level", "1").splitlines()
    assert lines[0] == "# 3 namespaces"
    assert lines[1] == "- project 3 children"
    assert lines[2] == "- role 4 roles"
    assert lines[3] == "- global 1 child"


def expected_score(project: Path, uri: str, query: str) -> int:
    """The frozen 16.4 formula, computed from the node's own printed L0/L1."""
    l0 = ok(project, "context", "read", uri, "--level", "0").casefold()
    l1 = ok(project, "context", "read", uri, "--level", "1")
    tags = []
    for line in l1.splitlines():
        if line.startswith("- tags: "):
            tags = [tag.strip().casefold() for tag in line[len("- tags: ") :].split(",")]
    tags = [tag for tag in tags if tag]
    tokens = [token.casefold() for token in query.split()]
    normalised = " ".join(tokens)
    score = 5 if normalised and normalised in l0 else 0
    score += 3 if tokens and all(token in l0 for token in tokens) else 0
    score += 2 * sum(l0.count(token) for token in tokens)
    score += sum(l1.casefold().count(token) for token in tokens)
    score += 1 if any(tag in tokens for tag in tags) else 0
    return score


def test_find_scores_exactly_and_orders_by_score_then_uri(ws: Path) -> None:
    query = "context tree"
    lines = ok(ws, "context", "find", query).splitlines()
    assert lines
    assert all(FIND_LINE.match(line) for line in lines), lines

    hits = []
    for line in lines:
        _dash, score, uri, _rest = line.split(" ", 3)
        hits.append((int(score), uri))
    assert hits == sorted(hits, key=lambda hit: (-hit[0], hit[1])), hits

    knowledge_hit = expected_score(ws, "ctx://project/knowledge/K-0001", query)
    assert hits[0][1] == "ctx://project/knowledge/K-0001"
    assert hits[0][0] == knowledge_hit
    assert all(score == expected_score(ws, uri, query) for score, uri in hits[:5])

    assert ok(ws, "context", "find", query, "--limit", "1").splitlines() == [lines[0]]


def test_find_scope_is_a_hard_prefix(ws: Path) -> None:
    scope = "ctx://project/docs"
    scoped = ok(ws, "context", "find", "read-only", "--scope", scope).splitlines()
    assert scoped
    assert all(
        line.split(" ", 3)[2] == scope or line.split(" ", 3)[2].startswith(scope + "/")
        for line in scoped
    )
    assert not any(
        "[knowledge]" in line or "[skill]" in line or "[lesson]" in line for line in scoped
    )
    assert not any("ctx://role/" in line for line in scoped)

    assert (
        ok(ws, "context", "find", "zqxranktoken", "--scope", "ctx://project/docs").strip()
        == '# no context node matched "zqxranktoken"'
    )
    inside = ok(ws, "context", "find", "zqxranktoken", "--scope", "ctx://project/knowledge")
    assert "ctx://project/knowledge/K-0002" in inside
    assert all(
        line.split(" ", 3)[2].startswith("ctx://project/knowledge") for line in inside.splitlines()
    )


def test_find_never_reads_l2(ws: Path) -> None:
    uri = "ctx://project/docs/Team/Project.md"
    doc = ws / "docs" / "Team" / "Project.md"
    before = ok(ws, "context", "find", "context tree")
    doc.write_text(
        doc.read_text(encoding="utf-8") + "\nsentinelbodytoken\n",
        encoding="utf-8",
    )
    try:
        assert ok(ws, "context", "find", "sentinelbodytoken").strip() == (
            '# no context node matched "sentinelbodytoken"'
        )
        assert ok(ws, "context", "find", "context tree") == before
        assert "sentinelbodytoken" in ok(ws, "context", "read", uri, "--level", "2")
    finally:
        doc.write_text(DOC_PROJECT, encoding="utf-8")


UNSAFE_URIS = [
    "ctx://../Knowledge.md",
    "ctx://project/../global",
    "ctx:///etc/passwd",
    "ctx://C:/Windows",
    "ctx://project\\knowledge",
    "ctx://\\\\server\\share",
]


@pytest.mark.parametrize("uri", UNSAFE_URIS)
def test_unsafe_uris_never_resolve(ws: Path, uri: str) -> None:
    read = refused(ws, "context", "read", uri, "--level", "0", names="unknown context URI")
    assert read.stdout == "", f"{uri} printed content before refusing"
    listed = refused(ws, "context", "ls", uri, names="unknown context URI")
    assert listed.stdout == "", f"{uri} listed content before refusing"


@pytest.mark.parametrize(
    "uri",
    [
        "ctx://project/nope",
        "ctx://project/knowledge/K-9999",
        "ctx://role/nope",
        "ctx://project/docs/Team",
        "ctx://project/skills/tw-missing",
    ],
)
def test_unknown_uris_exit_2_and_name_the_node(ws: Path, uri: str) -> None:
    refused(ws, "context", "read", uri, names=f"unknown context URI '{uri}'")


def test_unknown_level_and_scope_exit_2(ws: Path) -> None:
    level = refused(ws, "context", "read", "ctx://project/knowledge/K-0001", "--level", "3")
    assert re.search(r"argument --level: invalid choice: '?3'? ", level.stderr), level.stderr
    refused(
        ws,
        "context",
        "find",
        "context",
        "--scope",
        "ctx://project/nope",
        names="unknown context URI 'ctx://project/nope'",
    )
    refused(
        ws,
        "context",
        "find",
        "context",
        "--scope",
        "ctx://role/nope",
        names="unknown context URI 'ctx://role/nope'",
    )
    refused(
        ws,
        "context",
        "tree",
        "ctx://project/../global",
        names="unknown context URI 'ctx://project/../global'",
    )


def test_missing_store_reads_as_empty(empty_team: Path) -> None:
    root = team_root(empty_team)
    assert not (root / config.F_KNOWLEDGE).exists()
    assert not (engine.role_dir(root, "developer") / config.F_LESSONS).exists()

    assert ok(empty_team, "context", "ls", "ctx://project/knowledge") == ""
    assert ok(empty_team, "context", "read", "ctx://project/knowledge").strip() == "# 0 records"
    assert ok(empty_team, "context", "ls", "ctx://role/developer/lessons") == ""
    assert (
        ok(empty_team, "context", "read", "ctx://role/developer/lessons").strip() == "# 0 lessons"
    )
    assert ok(empty_team, "context", "find", "zzznomatch").strip() == (
        '# no context node matched "zzznomatch"'
    )
    assert ok(empty_team, "context", "stats").splitlines()[:4] == [
        "- memory: 0 entries (roles 0, global 0)",
        "- lessons: 0 (0 open, 0 fixed)",
        "- knowledge: 0 active, 0 superseded",
        "- skills: 0",
    ]
    refused(
        empty_team,
        "context",
        "read",
        "ctx://project/knowledge/K-0001",
        names="unknown context URI",
    )


def test_digest_failed_task_is_a_lesson_template(ws: Path) -> None:
    out = ok(ws, "context", "digest", "T-0001")
    lines = out.splitlines()
    assert lines[0] == "# lesson candidate for T-0001 (review failed 2x)"
    assert "teamwork.py lesson add --by <you> --role developer" in out
    assert "--mistake 'Digest a failed task'" in out
    assert f"--cause '{FAILED_FINDINGS}'" in out
    assert "--rule '<what rule prevents this>'" in out
    assert "--evidence 'review of T-0001 @abc1234 -> failed'" in out
    assert "--task T-0001" in out
    assert "knowledge add" not in out


def test_digest_done_task_is_an_experience_template(ws: Path) -> None:
    out = ok(ws, "context", "digest", "T-0002")
    lines = out.splitlines()
    assert lines[0] == "# knowledge candidate for T-0002 (done)"
    assert "teamwork.py knowledge add --by <you> --kind experience" in out
    assert "--topic 'Context find stays deterministic'" in out
    assert "--evidence 'merge def5678 of developer/t-0002 -> T-0002 done'" in out
    assert "--task T-0002" in out
    assert "lesson add" not in out


def test_digest_writes_nothing_and_unknown_task_exits_2(ws: Path) -> None:
    before = tree_hash(ws)
    try:
        assert ok(ws, "context", "digest", "T-0003").strip() == "# T-0003: nothing to digest"
        refused(ws, "context", "digest", "T-9999", names="no task 'T-9999' in any role queue")
        ok(ws, "context", "digest", "T-0001")
        ok(ws, "context", "digest", "T-0002")
    finally:
        assert tree_hash(ws) == before


def test_stats_reports_one_line_per_store_with_live_counts(ws: Path) -> None:
    docs = len(list((ws / "docs").rglob("*.md")))
    lines = ok(ws, "context", "stats").splitlines()
    assert lines == [
        "- memory: 3 entries (roles 2, global 1)",
        "- lessons: 1 (1 open, 0 fixed)",
        "- knowledge: 2 active, 0 superseded",
        "- skills: 1",
        f"- docs: {docs}",
        "- tasks: 3",
    ]


def test_stats_echoes_no_stored_content_or_credential(ws: Path) -> None:
    out = ok(ws, "context", "stats")
    assert len(out.splitlines()) == 6
    lowered = out.casefold()
    for marker in ("secret", "credential", "password", "token", "api_key"):
        assert marker not in lowered
    for body in (
        "Read L1 before L2.",
        "Long-term fact about the tree.",
        "The context view is read-only.",
        "The tree is a read-only view over the stores.",
    ):
        assert body not in out
