"""Unit: the read-only ctx:// context tree (Architecture.md 16).

Layer ``unit``, area ``context``. The view is computed from files that already
exist, so every assertion is made on a real fixture tree the command reads and on
the command's own stdout. The load-bearing parts are the URI resolver (unsafe and
unknown segments exit 2), the three computed levels, the deterministic scorer
(including "never read L2") and digest's read-only promise.

Owner: developer. Layer: unit. Area: context.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from teamwork import config, engine

AGENTS = "ceo,developer-1,release-engineer,tester-1"

DOC_PROJECT = """# Project

The project builds the context tree and it is read-only.

## Goals

A node resolves to a file that already exists.
"""

DOC_CLI = """# CLI

Commands are documented after they work.

## Context

`context read` prints one computed level.
"""

DOC_ARCH = """# Architecture

Frozen interfaces live here.

## Context tree

The view has no sidecars.
"""

SKILL_CONTEXT = """---
name: tw-context
description: "Distil a context node into a stable L0 line"
kind: workflow
---

# tw-context

Use it when a lane needs navigation without loading full files.

## Steps

1. Read L1 before L2.

## Checks

- The tree writes nothing.
"""

SKILL_PLAIN = """---
name: plain-skill
description: "A skill without the team prefix"
kind: workflow
---

# plain-skill

## Notes

Listed so a prefix finding stays visible.
"""


def team_root(project: Path) -> Path:
    return project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)


def task_file(project: Path, role: str = "developer") -> Path:
    return engine.role_dir(team_root(project), role) / config.F_TASKS


def task(title: str, **fields) -> dict:
    item = engine.new_task(title, priority=fields.pop("priority", "P2"))
    item["area"] = "context"
    item.update(fields)
    return item


@pytest.fixture
def ws(cli, project: Path, capsys) -> Path:
    """A workspace with every store populated and two skills, one unprefixed."""
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    capsys.readouterr()
    root = team_root(project)

    knowledge = [
        engine.new_knowledge(
            "Context tree",
            "The tree is a read-only view over the stores.",
            "pytest @abc -> 1 passed",
            "Developer-1",
            "developer",
            kind="experience",
            tags="context,tree",
            importance=4,
            task="T-0001",
        ),
        engine.new_knowledge(
            "Old context rule",
            "A sidecar used to hold the summary.",
            "pytest @old -> 1 passed",
            "Developer-1",
            "developer",
            kind="fact",
            tags="context",
        ),
    ]
    knowledge[0]["id"] = "K-0001"
    knowledge[1]["id"] = "K-0002"
    knowledge[1]["status"] = "superseded"
    engine.write_knowledge(engine.knowledge_path(root), knowledge)

    lesson = engine.new_lesson(
        "developer",
        "Ship the parser before the CLI",
        "The command was never wired",
        "Run the command once before committing",
        "pytest @abc -> failed",
        "Developer-1",
        task="T-0001",
    )
    lesson["id"] = "L-0001"
    engine.write_lessons(engine.lessons_path(root, "developer"), [lesson])

    engine.write_tasks(
        task_file(project),
        [
            task(
                "Digest a failed task",
                id="T-0001",
                status="doing",
                review_status="failed",
                review_fails=2,
                findings="detects: no-fail | the CLI was not wired",
                review_fail_rev="abc1234",
                branch="developer/t-0001",
            ),
            task(
                "Context find stays deterministic",
                id="T-0002",
                status="done",
                branch="developer/t-0002",
                merge_commit="def5678",
            ),
            task("Still open", id="T-0003"),
        ],
        "developer",
    )

    short = engine.new_entry(
        "Read L1 before L2.", key="context", importance=3, by="Developer-1", src="T-0001"
    )
    engine.write_memory(
        engine.role_dir(root, "developer") / config.F_SHORT,
        [short],
        config.F_SHORT,
        "developer",
    )
    global_entry = engine.new_entry(
        "The context view is read-only.", key="global", importance=2, by="CEO"
    )
    engine.write_memory(
        engine.global_dir(root) / config.F_GLOBAL,
        [global_entry],
        config.F_GLOBAL,
        "ceo",
    )

    docs = {
        "Team/Project.md": DOC_PROJECT,
        "Team/Architecture.md": DOC_ARCH,
        "guide/cli.md": DOC_CLI,
    }
    for rel, text in docs.items():
        path = project / "docs" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    skills = {"tw-context": SKILL_CONTEXT, "plain-skill": SKILL_PLAIN}
    for name, text in skills.items():
        path = project / ".agents" / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return project


def run(cli, project: Path, *argv) -> int:
    return cli("--project", project, "context", *argv)


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).replace("\\", "/").encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


URIS = [
    "ctx://",
    "ctx://project",
    "ctx://project/knowledge",
    "ctx://project/knowledge/K-0001",
    "ctx://project/skills",
    "ctx://project/skills/tw-context",
    "ctx://project/docs",
    "ctx://project/docs/Team/Project.md",
    "ctx://project/docs/guide/cli.md",
    "ctx://role",
    "ctx://role/developer",
    "ctx://role/developer/lessons",
    "ctx://role/developer/lessons/L-0001",
    "ctx://role/developer/tasks",
    "ctx://role/developer/tasks/T-0001",
    "ctx://role/developer/memory",
    "ctx://role/developer/memory/short",
    "ctx://role/developer/memory/short/M-0001",
    "ctx://role/developer/memory/long",
    "ctx://role/developer/memory/archive",
    "ctx://global",
    "ctx://global/memory",
    "ctx://global/memory/M-0001",
]


def test_every_uri_resolves(cli, ws: Path, capsys) -> None:
    for uri in URIS:
        assert run(cli, ws, "read", uri, "--level", "0") == 0, uri
        assert capsys.readouterr().out.strip(), uri


def test_missing_store_is_empty_not_an_error(cli, ws: Path, capsys) -> None:
    root = team_root(ws)
    (engine.role_dir(root, "developer") / config.F_LESSONS).unlink()
    engine.knowledge_path(root).unlink()
    (engine.global_dir(root) / config.F_GLOBAL).unlink()

    assert run(cli, ws, "ls", "ctx://role/developer/lessons") == 0
    assert capsys.readouterr().out == ""
    assert run(cli, ws, "read", "ctx://role/developer/lessons", "--level", "1") == 0
    assert capsys.readouterr().out.strip() == "# 0 lessons"
    assert run(cli, ws, "ls", "ctx://project/knowledge") == 0
    assert capsys.readouterr().out == ""
    assert run(cli, ws, "stats") == 0
    out = capsys.readouterr().out
    assert "- knowledge: 0 active, 0 superseded" in out
    assert "- memory: 1 entry (roles 1, global 0)" in out


@pytest.mark.parametrize(
    "uri",
    [
        "ctx://../Knowledge.md",
        "ctx://project/../global",
        "ctx://project\\knowledge",
        "ctx://C:/Windows",
        "ctx:///etc/passwd",
        "ctx://project//knowledge",
        "ctx://project/knowledge/..",
    ],
)
def test_unsafe_uri_exits_2(cli, ws: Path, uri: str) -> None:
    assert run(cli, ws, "read", uri) == 2


@pytest.mark.parametrize(
    "uri",
    [
        "ctx://project/nope",
        "ctx://role/developer/nope",
        "ctx://role/nope",
        "ctx://project/docs/Team",
        "ctx://project/knowledge/K-9999",
    ],
)
def test_unknown_uri_exits_2(cli, ws: Path, uri: str) -> None:
    assert run(cli, ws, "read", uri) == 2


def test_unknown_level_exits_2(cli, ws: Path) -> None:
    assert run(cli, ws, "read", "ctx://project/knowledge/K-0001", "--level", "3") == 2


def test_knowledge_levels(cli, ws: Path, capsys) -> None:
    assert run(cli, ws, "read", "ctx://project/knowledge/K-0001", "--level", "0") == 0
    assert (
        capsys.readouterr().out.strip()
        == "[experience] Context tree: The tree is a read-only view over the stores."
    )
    assert run(cli, ws, "read", "ctx://project/knowledge/K-0001") == 0
    out = capsys.readouterr().out
    assert "- kind: experience" in out
    assert "- statement: The tree is a read-only view over the stores." in out
    assert "- tags: context,tree" in out
    assert run(cli, ws, "read", "ctx://project/knowledge/K-0001", "--level", "2") == 0
    out = capsys.readouterr().out
    assert out.startswith("## K-0001 - Context tree")
    assert "- task: T-0001" in out
    assert "- status: active" in out


def test_lesson_levels(cli, ws: Path, capsys) -> None:
    assert run(cli, ws, "read", "ctx://role/developer/lessons/L-0001", "--level", "0") == 0
    assert capsys.readouterr().out.strip() == "[open] Ship the parser before the CLI"
    assert run(cli, ws, "read", "ctx://role/developer/lessons/L-0001") == 0
    out = capsys.readouterr().out
    assert "- status: open" in out
    assert "- rule: Run the command once before committing" in out
    assert run(cli, ws, "read", "ctx://role/developer/lessons/L-0001", "--level", "2") == 0
    assert capsys.readouterr().out.startswith("## L-0001 - Ship the parser before the CLI")


def test_memory_levels(cli, ws: Path, capsys) -> None:
    uri = "ctx://role/developer/memory/short/M-0001"
    assert run(cli, ws, "read", uri, "--level", "0") == 0
    assert capsys.readouterr().out.strip() == "Read L1 before L2."
    assert run(cli, ws, "read", uri) == 0
    out = capsys.readouterr().out
    assert "- key: context" in out
    assert "- src: T-0001" in out
    assert run(cli, ws, "read", uri, "--level", "2") == 0
    out = capsys.readouterr().out
    assert out.startswith("## M-0001 · context")
    assert "Read L1 before L2." in out


def test_skill_levels(cli, ws: Path, capsys) -> None:
    uri = "ctx://project/skills/tw-context"
    assert run(cli, ws, "read", uri, "--level", "0") == 0
    assert capsys.readouterr().out.strip() == "Distil a context node into a stable L0 line"
    assert run(cli, ws, "read", uri) == 0
    out = capsys.readouterr().out
    assert "- tw-context" in out
    assert "  - Steps" in out
    assert run(cli, ws, "read", uri, "--level", "2") == 0
    assert "name: tw-context" in capsys.readouterr().out


def test_doc_levels(cli, ws: Path, capsys) -> None:
    uri = "ctx://project/docs/Team/Project.md"
    assert run(cli, ws, "read", uri, "--level", "0") == 0
    assert (
        capsys.readouterr().out.strip()
        == "Project: The project builds the context tree and it is read-only."
    )
    assert run(cli, ws, "read", uri) == 0
    out = capsys.readouterr().out
    assert "- Project" in out
    assert "  - Goals" in out
    assert run(cli, ws, "read", uri, "--level", "2") == 0
    assert "A node resolves to a file that already exists." in capsys.readouterr().out


def test_task_levels(cli, ws: Path, capsys) -> None:
    uri = "ctx://role/developer/tasks/T-0001"
    assert run(cli, ws, "read", uri, "--level", "0") == 0
    assert capsys.readouterr().out.strip() == "Digest a failed task"
    assert run(cli, ws, "read", uri) == 0
    out = capsys.readouterr().out
    assert "- title: Digest a failed task" in out
    assert "- status: doing" in out
    assert "- findings: detects: no-fail | the CLI was not wired" in out
    assert run(cli, ws, "read", uri, "--level", "2") == 0
    assert capsys.readouterr().out.startswith("## T-0001 · Digest a failed task")


def test_directory_cap_and_more_marker(cli, ws: Path, capsys) -> None:
    for index in range(25):
        path = ws / "docs" / "bulk" / f"d{index:02d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# Bulk {index}\n\nA bulk document.\n", encoding="utf-8")
    total = len(list((ws / "docs").rglob("*.md")))
    assert total > config.CONTEXT_CHILD_CAP
    assert run(cli, ws, "tree", "ctx://project/docs", "-L", "1") == 0
    out = capsys.readouterr().out
    assert len([line for line in out.splitlines() if line.startswith("  - ")]) == 20
    assert f"... {total - config.CONTEXT_CHILD_CAP} more" in out
    assert run(cli, ws, "read", "ctx://project/docs", "--level", "1") == 0
    assert f"... {total - config.CONTEXT_CHILD_CAP} more" in capsys.readouterr().out
    assert run(cli, ws, "ls", "ctx://project/docs", "--limit", "5") == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 5


def test_ls_and_tree_defaults(cli, ws: Path, capsys) -> None:
    assert run(cli, ws, "ls") == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("- ctx://project [dir] 3 children")
    assert lines[1].startswith("- ctx://role [dir]")
    assert lines[2].startswith("- ctx://global [dir]")

    assert run(cli, ws, "tree") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "- ctx:// 3 namespaces"
    assert any(line == "  - project 3 children" for line in lines)
    assert any(line == "    - knowledge 2 records" for line in lines)
    assert not any(line.startswith("      - K-0001") for line in lines)


def test_read_default_level_is_fields(cli, ws: Path, capsys) -> None:
    assert run(cli, ws, "read", "ctx://project/knowledge/K-0001") == 0
    out = capsys.readouterr().out
    assert "## K-0001" not in out
    assert out.splitlines()[0].startswith("- statement:")


def test_find_ranking_and_uri_tie(cli, ws: Path, capsys) -> None:
    (ws / "docs" / "alpha.md").write_text("# Alpha\n\nzebra crossing rules\n", encoding="utf-8")
    (ws / "docs" / "beta.md").write_text("# Beta\n\nzebra only\n", encoding="utf-8")
    assert run(cli, ws, "find", "zebra crossing", "--scope", "ctx://project/docs") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("- 12 ctx://project/docs/alpha.md [doc]")
    assert any("ctx://project/docs/beta.md" in line for line in lines[1:])

    for rel in ("twin/a.md", "twin/b.md"):
        path = ws / "docs" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Twin\n\nidentical twin phrase\n", encoding="utf-8")
    assert run(cli, ws, "find", "identical twin phrase", "--scope", "ctx://project/docs") == 0
    hits = [
        line for line in capsys.readouterr().out.splitlines() if "ctx://project/docs/twin/" in line
    ]
    assert len(hits) == 2
    assert hits[0].split()[2] == "ctx://project/docs/twin/a.md"
    assert hits[1].split()[2] == "ctx://project/docs/twin/b.md"


def test_find_scope_is_a_hard_prefix(cli, ws: Path, capsys) -> None:
    assert run(cli, ws, "find", "context", "--scope", "ctx://project/knowledge") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines
    assert all("ctx://project/knowledge" in line for line in lines)
    assert any("ctx://project/knowledge/K-0001" in line for line in lines)
    assert all("ctx://role/" not in line for line in lines)
    assert run(cli, ws, "find", "context", "--scope", "ctx://project/nope") == 2


def test_find_never_reads_l2(cli, ws: Path, capsys) -> None:
    uri = "ctx://project/docs/Team/Project.md"
    assert run(cli, ws, "find", "unique_body_token") == 0
    assert capsys.readouterr().out.strip() == '# no context node matched "unique_body_token"'
    before = capsys.readouterr().out
    assert run(cli, ws, "find", "read-only") == 0
    before = capsys.readouterr().out
    path = ws / "docs" / "Team" / "Project.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nunique_body_token\n", encoding="utf-8")
    assert run(cli, ws, "find", "read-only") == 0
    assert capsys.readouterr().out == before
    assert run(cli, ws, "find", "unique_body_token") == 0
    assert capsys.readouterr().out.strip() == '# no context node matched "unique_body_token"'
    assert run(cli, ws, "read", uri, "--level", "2") == 0
    assert "unique_body_token" in capsys.readouterr().out


def test_stats_counts(cli, ws: Path, capsys) -> None:
    assert run(cli, ws, "stats") == 0
    lines = capsys.readouterr().out.splitlines()
    docs = len(list((ws / "docs").rglob("*.md")))
    assert lines == [
        "- memory: 2 entries (roles 1, global 1)",
        "- lessons: 1 (1 open, 0 fixed)",
        "- knowledge: 1 active, 1 superseded",
        "- skills: 2",
        f"- docs: {docs}",
        "- tasks: 3",
    ]


def test_digest_failed_task_is_a_lesson_template(cli, ws: Path, capsys) -> None:
    root = team_root(ws)
    before = tree_hash(root)
    assert run(cli, ws, "digest", "T-0001") == 0
    out = capsys.readouterr().out
    assert "lesson candidate for T-0001" in out
    assert "teamwork.py lesson add --by <you> --role developer" in out
    assert "--mistake 'Digest a failed task'" in out
    assert "--cause 'detects: no-fail | the CLI was not wired'" in out
    assert "--rule '<what rule prevents this>'" in out
    assert "--evidence '" in out
    assert "--task T-0001" in out
    assert "knowledge add" not in out
    assert tree_hash(root) == before


def test_digest_done_task_is_a_knowledge_template(cli, ws: Path, capsys) -> None:
    root = team_root(ws)
    before = tree_hash(root)
    assert run(cli, ws, "digest", "T-0002") == 0
    out = capsys.readouterr().out
    assert "knowledge candidate for T-0002 (done)" in out
    assert "teamwork.py knowledge add --by <you> --kind experience" in out
    assert "--topic 'Context find stays deterministic'" in out
    assert "--evidence 'merge def5678 of developer/t-0002 -> T-0002 done'" in out
    assert "--task T-0002" in out
    assert tree_hash(root) == before


def test_digest_neutral_and_unknown_task(cli, ws: Path, capsys) -> None:
    assert run(cli, ws, "digest", "T-0003") == 0
    assert capsys.readouterr().out.strip() == "# T-0003: nothing to digest"
    assert run(cli, ws, "digest", "T-9999") == 2


def test_context_is_in_help_and_read_only(cli, ws: Path, capsys) -> None:
    parser = engine.build_parser()
    context = parser.parse_args(["context", "stats"])
    assert context.cmd == "context"
    assert context.context_cmd == "stats"
    root = team_root(ws)
    before = tree_hash(root)
    for argv in (
        ("ls",),
        ("tree",),
        ("read", "ctx://project/knowledge/K-0001"),
        ("find", "context"),
        ("stats",),
        ("digest", "T-0001"),
        ("digest", "T-0002"),
    ):
        assert run(cli, ws, *argv) == 0
    capsys.readouterr()
    assert tree_hash(root) == before
    assert not (root / "ctx").exists()
