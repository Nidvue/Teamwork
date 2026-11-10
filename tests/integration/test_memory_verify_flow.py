"""Integration: `memory verify` and the `drifted` dream group on a real team tree.

Layer ``integration``, area ``memory``, owner Tester (T-0008). The unit suite
(`tests/unit/test_memverify.py`) proves the classifier and the writer in
isolation; this file proves the operator-facing contract in
``docs/Team/Memory.md`` 9 on a tree the CLI itself built: `knowledge add`
plants the records, `memory verify` re-resolves them against a real git commit
and a real file in the tree, and `memory dream` reports the same drift with the
four groups it already had.

Asserted here (contract 9):

- one line per record, ``- [<id>] <kind> <verify_status> | <reason> | <pointer>``,
  with the three statuses reachable in one run, and the exact footer counts;
- two runs on the same tree and the same day are byte-identical;
- ``--apply`` adds only ``checked`` and ``verify_status`` to knowledge records -
  statements and evidence strings are untouched and lesson stores stay
  byte-identical - and a second ``--apply`` writes nothing;
- ``memory dream`` gains ``drifted`` (same function) and keeps its four groups.

Not covered here (deliberately): 9.1 ``--focus`` (T-0055 was not merged at
b7aaa44), transcript reach (10), the index header (11), ``--json`` and
``--limit``.

Owner: tester. Layer: integration. Area: memory.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from teamwork import config, engine

AGENTS = "ceo,developer-1,tester-1,reviewer-1"

RECORDED_RE = re.compile(r"^# (K-\d{4}) recorded:", re.MULTILINE)
VERIFY_LINE_RE = re.compile(
    r"^- \[(?P<id>K-\d{4})\] (?P<kind>\w+) (?P<status>\w+) \| (?P<reason>.+) \| (?P<pointer>.+)$",
    re.MULTILINE,
)
FOOTER_RE = re.compile(
    r"^# verify: (?P<records>\d+) record\(s\), (?P<verified>\d+) verified, "
    r"(?P<drifted>\d+) drifted, (?P<unverifiable>\d+) unverifiable \(limit (?P<limit>\S+)\)$",
    re.MULTILINE,
)


def team_root(project: Path) -> Path:
    """The hidden tree ``<project>/.pi/Teamwork/Teams/<Team>/``."""
    return (
        project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def git(project: Path, *args: str) -> str:
    """Run git in the throwaway project without a developer's identity or signing."""
    done = subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test Lane",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def plant(cli, project: Path, topic: str, evidence: str) -> None:
    """Record one knowledge entry through the CLI (the id comes back on stdout)."""
    code = cli(
        "--project",
        project,
        "knowledge",
        "add",
        "--by",
        "Tester",
        "--topic",
        topic,
        "--statement",
        f"{topic}: the pass must classify this record from its evidence alone.",
        "--evidence",
        evidence,
    )
    assert code == 0, f"knowledge add {topic} returned {code}"


@pytest.fixture
def tree(cli, tmp_path: Path, capsys) -> dict:
    """A real no-git team, a real commit, three planted knowledge records."""
    code = cli("--project", tmp_path, "init", "--agents", AGENTS, "--no-git")
    assert code == 0, f"init returned {code}"
    root = team_root(tmp_path)
    assert root.is_dir()
    capsys.readouterr()

    # A real revision the pass can re-resolve, and a real file it can line-count.
    git(tmp_path, "init", "-b", "main")
    (tmp_path / "README.md").write_text("# throwaway\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "base")
    sha = git(tmp_path, "rev-parse", "HEAD")
    (root / "probe.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")

    cases = {
        "revision": f"pytest -q tests/unit/test_memverify.py @{sha} -> 12 passed",
        "path": "probe.txt:99",
        "source": "https://example.com/x",
    }
    ids = {}
    for kind, evidence in cases.items():
        plant(cli, tmp_path, f"{kind} probe for memory verify", evidence)
        out = capsys.readouterr().out
        match = RECORDED_RE.search(out)
        assert match, f"knowledge add printed no id: {out!r}"
        ids[kind] = match.group(1)

    lessons_before = {path: path.read_bytes() for path in sorted(root.glob("Roles/*/Lessons.md"))}
    return {
        "project": tmp_path,
        "root": root,
        "sha": sha,
        "ids": ids,
        "knowledge": root / config.F_KNOWLEDGE,
        "lessons_before": lessons_before,
    }


def verify(cli, project: Path, capsys, *extra: str) -> str:
    code = cli("--project", project, "memory", "verify", "--role", "developer", *extra)
    out = capsys.readouterr().out
    assert code == 0, f"memory verify returned {code}: {out}"
    return out


def test_three_kinds_one_line_each_with_footer_counts(tree, cli, capsys) -> None:
    """One line per record carrying its status and reason, then the footer."""
    out = verify(cli, tree["project"], capsys)
    lines = {row.group("id"): row for row in VERIFY_LINE_RE.finditer(out)}
    assert set(lines) == set(tree["ids"].values()), out

    revision = lines[tree["ids"]["revision"]]
    assert revision.group("kind") == "revision"
    assert revision.group("status") == "verified"
    assert tree["sha"] in revision.group("reason")

    path = lines[tree["ids"]["path"]]
    assert path.group("kind") == "path"
    assert path.group("status") == "drifted"
    assert "has 3 line(s), wanted 99" in path.group("reason")

    source = lines[tree["ids"]["source"]]
    assert source.group("kind") == "source"
    assert source.group("status") == "unverifiable"
    assert "carries no access date" in source.group("reason")

    for row in lines.values():
        assert row.group("pointer").startswith("Knowledge.md#K-"), row.group(0)

    footer = FOOTER_RE.search(out)
    assert footer, out
    assert footer.group("verified") == "1"
    assert footer.group("drifted") == "1"
    assert footer.group("unverifiable") == "1"
    assert footer.group("records") == str(len(lines))
    assert footer.group("limit") == "all"


def test_two_runs_are_byte_identical(tree, cli, capsys) -> None:
    """Same tree, same day: the report is a pure function of the records."""
    first = verify(cli, tree["project"], capsys)
    second = verify(cli, tree["project"], capsys)
    assert first == second


def test_apply_writes_two_fields_and_nothing_else(tree, cli, capsys) -> None:
    """`--apply` stamps checked and verify_status; a second run writes nothing."""
    knowledge = tree["knowledge"]
    before = knowledge.read_text(encoding="utf-8")
    assert "checked:" not in before
    assert "verify_status:" not in before

    out = verify(cli, tree["project"], capsys, "--apply", "--by", "Tester")
    assert "# applied: 3 knowledge record(s) stamped" in out, out

    after = knowledge.read_text(encoding="utf-8")
    added = [
        line for line in after.splitlines() if line not in before.splitlines() and line.strip()
    ]
    assert added, "apply wrote nothing"
    assert all(line.startswith(("- checked: ", "- verify_status: ")) for line in added), added
    assert len(added) == 6, added  # two fields on each of the three records

    # No statement or evidence line was rewritten, and no record was deleted.
    for line in before.splitlines():
        assert line in after.splitlines(), f"apply changed: {line!r}"
    for kind, record_id in tree["ids"].items():
        assert f"## {record_id} - {kind} probe for memory verify" in after

    # Lessons carry no such field: every lesson store stays byte-identical.
    for path, blob in tree["lessons_before"].items():
        assert path.read_bytes() == blob, f"apply touched {path}"

    second = verify(cli, tree["project"], capsys, "--apply", "--by", "Tester")
    assert "# applied: 0 knowledge record(s) stamped, ledger bytes +0" in second, second
    assert knowledge.read_text(encoding="utf-8") == after


def test_dream_reports_drift_and_keeps_its_four_groups(tree, cli, capsys) -> None:
    """`drifted` is one group among five; the original four still print."""
    code = cli("--project", tree["project"], "memory", "dream", "--role", "developer")
    out = capsys.readouterr().out
    assert code == 0, out

    for group in ("duplicate", "contradiction", "stale", "no evidence", "drifted"):
        assert re.search(rf"^# {group}: \d+$", out, re.MULTILINE), (group, out)

    drifted = re.search(r"^# drifted: (\d+)\n((?:^- .*\n)*)", out, re.MULTILINE)
    assert drifted, out
    assert drifted.group(1) == "1", out
    assert tree["ids"]["path"] in drifted.group(2)
    assert "(path)" in drifted.group(2)
    # The two records the verify pass called clean are not drift.
    assert tree["ids"]["revision"] not in drifted.group(2)
    assert tree["ids"]["source"] not in drifted.group(2)
