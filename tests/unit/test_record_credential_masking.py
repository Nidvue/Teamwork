"""Unit: a credential never reaches a record file, at any write chokepoint (T-0007).

Layer ``unit``, area ``records-mask``. Reviewer-1's security audit S-2 measured
that ``mask_secret_shapes`` was called from ``archive_append`` alone, so a token
passed to ``task add --evidence``, ``decision add``, ``lesson add`` or
``remember`` was written verbatim into ``TaskQueue.md``, ``Lessons.md``, the
memory files, the committed ``docs/Team/Decisions.md`` and the append-only
``Ledger.jsonl`` - three of those are git-ignored (no privacy gate ever reads
them) and the ledger can never be rewritten.

The store is the trust boundary, so the assertions are made on the files the
commands wrote: no file under the workspace may contain the planted value, the
evidence around it must stay readable, and a path, a commit sha and ordinary
prose must come through byte-identical - a mask that eats a path is data
corruption, not privacy. Masking is idempotent, so a second write of the same
record must not change it, and the ledger chain must still verify.

The planted value is assembled at run time: a literal token in a tracked test
file would make the shipped privacy gate red on this very file.

Owner: developer. Layer: unit. Area: records-mask.
"""

from __future__ import annotations

import json

import pytest

from teamwork import engine, records

AGENTS = "ceo,developer-1,reviewer-1"

TOKEN = "ghp" + "_" + "Zq7Rt2Mn9Kp4Vx6" + "Bd8Ws3Jf5Hg1Lc0"
MASKED = "<redacted-api-token>"

SHA = "c8af0e15254aac04ed985b0b34207a8019c93684"
PATH = "docs/Team/Architecture.md"
REPORT_DIR = ".pi/Teamwork/Teams/Teamwork/Agents/Developer/Reports/"
LONG_PATH = REPORT_DIR + "M19" + "-engine-audit.md"
PROSE = "the reviewer re-read the diff and confirmed the boundary case"


def team_root(project) -> object:
    return project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)


def plant(cli, project) -> None:
    """Write the same value through every command the audit named."""
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "probe secret handling",
            "--evidence",
            f"curl -H 'Authorization: Bearer {TOKEN}' @{SHA} -> 200",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "decision",
            "add",
            "--by",
            "developer-1",
            "--decision",
            "the endpoint stays private",
            "--evidence",
            f"env TOKEN={TOKEN} @{SHA} -> 200",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "lesson",
            "add",
            "--by",
            "developer-1",
            "--mistake",
            "a probe wrote the value into a record",
            "--cause",
            "masking ran only in the archive",
            "--rule",
            "mask at the record chokepoint",
            "--evidence",
            f"KEY={TOKEN} @{SHA} -> 200",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "remember",
            "developer",
            f"the key is {TOKEN}",
            "--by",
            "developer-1",
            "--src",
            "T-0001",
            "--rev",
            SHA[:7],
        )
        == 0
    )


def written_files(project) -> list:
    return [path for path in project.rglob("*") if path.is_file()]


def test_a_planted_credential_appears_in_no_written_file(cli, project, capsys) -> None:
    """The finding, measured: five record files used to carry the value."""
    plant(cli, project)
    capsys.readouterr()
    leaks = [
        str(path.relative_to(project))
        for path in written_files(project)
        if TOKEN in path.read_text(encoding="utf-8", errors="replace")
    ]
    assert leaks == [], f"the credential reached {leaks}"

    root = team_root(project)
    stored = {
        "docs/Team/Decisions.md": project / "docs" / "Team" / "Decisions.md",
        "Roles/Developer/Lessons.md": root / "Roles" / "Developer" / "Lessons.md",
        "Roles/Developer/ShortTermMemory.md": root / "Roles" / "Developer" / "ShortTermMemory.md",
        "Roles/Developer/TaskQueue.md": root / "Roles" / "Developer" / "TaskQueue.md",
        "Ledger.jsonl": root / "Ledger.jsonl",
    }
    for name, path in stored.items():
        text = path.read_text(encoding="utf-8")
        assert "<redacted-" in text, f"{name} kept no masked value: the finding was not measured"
        assert TOKEN not in text


def test_the_evidence_and_the_ledger_survive_the_mask(cli, project, capsys) -> None:
    """The record stays readable and the chain still verifies after masking."""
    plant(cli, project)
    capsys.readouterr()
    root = team_root(project)
    task = (root / "Roles" / "Developer" / "TaskQueue.md").read_text(encoding="utf-8")
    assert "curl -H 'Authorization: " in task, "the evidence around the value must survive"
    assert f"@{SHA} -> 200" in task, "the sha in evidence must survive byte-identical"
    assert "<redacted-" in task, "the record no longer says a value was masked there"

    assert cli("--project", project, "ledger", "verify") == 0
    lines = [json.loads(line) for line in (root / "Ledger.jsonl").read_text().splitlines() if line]
    record = next(item for item in lines if item["action"] == "task.add")
    assert "probe secret handling" in record["detail"], "the action must stay readable"
    assert TOKEN not in json.dumps(lines)
    assert any(MASKED in item["detail"] for item in lines), "no ledger record shows a masked value"


def test_a_path_a_sha_and_prose_survive_the_mask(cli, project, capsys) -> None:
    """A value the gate reports is masked; everything else is byte-identical."""
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    evidence = (
        f"python3 -m pytest tests/unit/test_knowledge.py @{SHA} -> 12 passed; "
        f"see {PATH} and {LONG_PATH}; {PROSE}"
    )
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "long evidence boundary",
            "--evidence",
            evidence,
        )
        == 0
    )
    capsys.readouterr()
    root = team_root(project)
    task = (root / "Roles" / "Developer" / "TaskQueue.md").read_text(encoding="utf-8")
    assert evidence in task, [line for line in task.splitlines() if line.startswith("- evidence")]


def test_masking_a_record_twice_writes_the_same_bytes(tmp_path) -> None:
    """Idempotence: the marker is not itself a credential shape."""
    assert engine.mask_secret_shapes(f"the key is {TOKEN}") == f"the key is {MASKED}"
    text = f"the key is {TOKEN} @{SHA}; see {PATH}"
    once = records.masked_text(text)
    assert TOKEN not in once
    assert records.masked_text(once) == once
    assert SHA in once and PATH in once

    tasks = []
    path = tmp_path / "TaskQueue.md"
    records.write_tasks(path, tasks, "developer")
    empty = path.read_text(encoding="utf-8")
    records.write_tasks(path, tasks, "developer")
    assert path.read_text(encoding="utf-8") == empty


def test_write_reviews_masks_a_planted_value(tmp_path) -> None:
    """The review record is a record: a summary and a note go through the mask."""
    prs = [
        {
            "id": "P-0001",
            "task": "T-0001",
            "title": "probe",
            "branch": "developer/t-0001-probe",
            "base": "main",
            "status": "open",
            "opened": "2026-11-07",
            "updated": "2026-11-07",
            "reviewer": "",
            "merge_commit": "",
            "summary": f"ran with TOKEN={TOKEN}",
            "notes": [f"see {PATH} @{SHA}"],
        }
    ]
    path = tmp_path / "Reviews.md"
    records.write_reviews(path, prs)
    text = path.read_text(encoding="utf-8")
    assert TOKEN not in text
    assert "<redacted-" in text
    assert PATH in text and SHA in text


def test_the_record_layer_refuses_to_write_without_the_mask(monkeypatch) -> None:
    """Fail-closed: the engine installs the mask, and no mask means no write."""
    assert records._MASK is engine.mask_secret_shapes
    monkeypatch.setattr(records, "_MASK", None)
    with pytest.raises(RuntimeError, match="no record mask installed"):
        records.masked_text(f"the key is {TOKEN}")


def test_a_ledger_detail_is_masked_before_it_is_clipped(tmp_path) -> None:
    """The clip must not cut a value in half and leave the head in the chain."""
    pad = "x" * (engine.LEDGER_DETAIL_CHARS - 10)
    engine.ledger_append(tmp_path, "probe", "developer-1", "T-0001", f"{pad} {TOKEN} tail")
    text = (tmp_path / engine.F_LEDGER).read_text(encoding="utf-8")
    assert TOKEN not in text
    assert TOKEN[:4] not in text, "a clipped half of a value is still a leak"
    assert len(json.loads(text.strip())["detail"]) <= engine.LEDGER_DETAIL_CHARS


def test_the_mask_keeps_a_credential_that_sits_in_a_path(tmp_path) -> None:
    """The path guard must not become a bypass: a real token stays masked."""
    line = f"cat /tmp/run/{TOKEN}/out -> 200"
    masked = engine.mask_secret_shapes(line)
    assert TOKEN not in masked
    assert "/tmp/run/" in masked and "/out" in masked
    assert PATH in engine.mask_secret_shapes(PATH)
    assert LONG_PATH in engine.mask_secret_shapes(LONG_PATH)
    path_shape = "repos/Nidvue/Teamwork/rulesets/" + "25840176"
    assert path_shape in engine.mask_secret_shapes(f"gh api {path_shape} -> tag")

    random_run = "Ab3xK9mQ2pL7vRt5Ws8Zc4"
    assert random_run not in engine.mask_secret_shapes(f"see docs/{random_run}/notes.md -> ok"), (
        "a random run inside a path is still a credential"
    )


@pytest.mark.parametrize("writer", ["task", "memory", "lessons", "knowledge"])
def test_every_record_writer_masks_its_input(tmp_path, writer) -> None:
    """One helper behind every writer: a later writer cannot forget the mask."""
    path = tmp_path / f"{writer}.md"
    if writer == "task":
        tasks = [
            records.new_task(
                f"probe {TOKEN}", "P0", evidence=f"KEY={TOKEN} @{SHA} -> ok", review="na"
            )
        ]
        records.write_tasks(path, tasks, "developer")
    elif writer == "memory":
        entries = [records.new_entry(f"the key is {TOKEN}", src="T-0001", rev="abc")]
        records.write_memory(path, entries, records.F_SHORT, "developer")
    elif writer == "lessons":
        items = [
            records.new_lesson(
                "developer",
                "m",
                "c",
                f"rule {TOKEN}",
                f"KEY={TOKEN}",
                "Developer-1",
            )
        ]
        records.write_lessons(path, items)
    else:
        items = [
            records.new_knowledge(
                "topic",
                f"the key is {TOKEN}",
                f"KEY={TOKEN} @{SHA} -> ok",
                "Developer-1",
                "developer",
            )
        ]
        records.write_knowledge(path, items)
    text = path.read_text(encoding="utf-8")
    assert TOKEN not in text
    assert "<redacted-" in text
