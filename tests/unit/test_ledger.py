"""Unit tests for the hash-chained audit ledger: digest and verification."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from teamwork import engine

ZERO = "0" * 64
FROZEN_DIGEST = "fc6cee09194dd2578bd7664604fcb72a539066fd34544cea0009c43eb6cdc289"


def _seed(root: Path) -> Path:
    """Append three records so the chain has a middle worth tampering with."""
    root.mkdir(parents=True, exist_ok=True)
    engine.ledger_append(root, "task.add", "developer", "T-0001", "first")
    engine.ledger_append(root, "task.claim", "developer", "T-0001", "second")
    engine.ledger_append(root, "tests.run", "developer", "TS-0001", "third")
    return root


def test_digest_is_deterministic() -> None:
    assert engine._digest(ZERO, {"a": 1}) == engine._digest(ZERO, {"a": 1})


def test_digest_frozen_known_value() -> None:
    assert engine._digest(ZERO, {"a": 1}) == FROZEN_DIGEST


def test_digest_depends_on_record_body() -> None:
    assert engine._digest(ZERO, {"a": 1}) != engine._digest(ZERO, {"a": 2})


def test_digest_depends_on_previous_hash() -> None:
    assert engine._digest(ZERO, {"a": 1}) != engine._digest("1" * 64, {"a": 1})


def test_digest_ignores_the_hash_field() -> None:
    left = engine._digest(ZERO, {"a": 1, "hash": "aaa"})
    right = engine._digest(ZERO, {"a": 1, "hash": "bbb"})
    assert left == right


def test_canon_is_order_independent_sorted_json() -> None:
    left = engine._canon({"b": 1, "a": 2})
    right = engine._canon({"a": 2, "b": 1})
    assert left == right == '{"a":2,"b":1}'


def test_verify_good_chain_is_empty(tmp_path: Path) -> None:
    root = _seed(tmp_path / "team")
    assert engine.ledger_verify(root) == []


def test_ledger_read_returns_all_records(tmp_path: Path) -> None:
    root = _seed(tmp_path / "team")
    records = engine.ledger_read(root)
    assert [r["action"] for r in records] == ["task.add", "task.claim", "tests.run"]
    assert [r["n"] for r in records] == [1, 2, 3]


def test_verify_missing_ledger_is_empty(tmp_path: Path) -> None:
    assert engine.ledger_verify(tmp_path / "nothing") == []
    assert engine.ledger_read(tmp_path / "nothing") == []


def test_ledger_append_links_prev_and_writes_head(tmp_path: Path) -> None:
    root = _seed(tmp_path / "team")
    records = engine.ledger_read(root)
    assert records[1]["prev"] == records[0]["hash"]
    assert records[2]["prev"] == records[1]["hash"]
    head = json.loads(engine.ledger_head_path(root).read_text(encoding="utf-8"))
    assert head == {"n": 3, "hash": records[-1]["hash"]}


def test_verify_detects_altered_detail(tmp_path: Path) -> None:
    root = _seed(tmp_path / "team")
    path = engine.ledger_path(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[1])
    record["detail"] = "tampered"
    lines[1] = json.dumps(record, sort_keys=True, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    problems = engine.ledger_verify(root)
    assert any("digest mismatch" in p for p in problems)


def test_verify_detects_broken_prev_link(tmp_path: Path) -> None:
    root = _seed(tmp_path / "team")
    path = engine.ledger_path(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[1])
    record["prev"] = "f" * 64
    lines[1] = json.dumps(record, sort_keys=True, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    problems = engine.ledger_verify(root)
    assert any("prev hash mismatch" in p for p in problems)


def test_verify_detects_truncated_tail(tmp_path: Path) -> None:
    root = _seed(tmp_path / "team")
    path = engine.ledger_path(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    problems = engine.ledger_verify(root)
    assert any("records were removed" in p or "truncated" in p for p in problems)


def test_verify_detects_unreadable_line(tmp_path: Path) -> None:
    root = _seed(tmp_path / "team")
    path = engine.ledger_path(root)
    with path.open("a", encoding="utf-8") as fh:
        fh.write("{ not json\n")

    problems = engine.ledger_verify(root)
    assert any("unreadable line" in p for p in problems)


def test_verify_reconciles_a_cache_that_is_behind(tmp_path: Path) -> None:
    root = _seed(tmp_path / "team")
    path = engine.ledger_head_path(root)
    records = engine.ledger_read(root)
    path.write_text(json.dumps({"n": 1, "hash": records[0]["hash"]}) + "\n", encoding="utf-8")

    assert engine.ledger_cache_behind(root) is True
    problems = engine.ledger_verify(root)
    assert any("behind" in p for p in problems)

    assert engine.ledger_verify(root, reconcile=True) == []
    assert engine.ledger_cache_behind(root) is False


def test_manifest_anchor_is_scoped_to_the_workspace_id(tmp_path: Path) -> None:
    project = tmp_path / "project"
    root = project / ".pi" / "Teamwork" / "Teams" / "T"
    root.mkdir(parents=True)
    (root / "Settings.json").write_text('{"TeamId": "team-a"}\n', encoding="utf-8")
    engine.ledger_append(root, "a", "ceo", "x", "one")
    docs = project / "docs" / "Team"
    docs.mkdir(parents=True)
    manifest = docs / "AuditManifest.json"
    manifest.write_text('{"team_id": "team-a", "ledger": {"records": 99}}\n', encoding="utf-8")
    assert any("truncated after export" in p for p in engine.ledger_verify(root))

    manifest.write_text('{"team_id": "team-b", "ledger": {"records": 99}}\n', encoding="utf-8")
    assert not any("truncated after export" in p for p in engine.ledger_verify(root))


def test_audit_trail_ignores_a_foreign_workspace_manifest(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    root = project / ".pi" / "Teamwork" / "Teams" / "T"
    root.mkdir(parents=True)
    (root / "Settings.json").write_text('{"TeamId": "team-a"}\n', encoding="utf-8")
    engine.ledger_append(root, "a", "ceo", "x", "one")
    docs = project / "docs" / "Team"
    docs.mkdir(parents=True)
    (docs / "AuditManifest.json").write_text(
        '{"team_id": "team-b", "ledger": {"records": 99}}\n', encoding="utf-8"
    )
    hits = engine._audit_audit_trail_append_only_hash_chained(root, ["ceo"], None)
    assert hits == 0
    assert "FEWER records" not in capsys.readouterr().out


def test_the_manifest_checkpoint_survives_later_ledger_work(tmp_path: Path, capsys) -> None:
    """The manifest pins the export record, so work after the export still verifies.

    Pinning the live head made the published recipe impossible to follow: the very
    act of merging the manifest appends ledger records, so "compare the recomputed
    head with ledger.head above" could never hold on a shipped tree.
    """
    project = tmp_path / "project"
    root = project / ".pi" / "Teamwork" / "Teams" / "T"
    root.mkdir(parents=True)
    (root / "Settings.json").write_text('{"TeamId": "team-a"}\n', encoding="utf-8")
    _seed(root)
    docs = project / "docs" / "Team"
    docs.mkdir(parents=True)
    args = SimpleNamespace(dry_run=False, by="")
    assert engine.ledger_export(root, args) == 0
    manifest = json.loads((docs / engine.F_MANIFEST).read_text(encoding="utf-8"))

    checkpoint = manifest["ledger"]["checkpoint_n"]
    records = engine.ledger_read(root)
    assert records[checkpoint - 1]["action"] == "ledger.export"
    assert manifest["ledger"]["head"] == records[checkpoint - 1]["hash"]

    engine.ledger_append(root, "task.add", "ceo", "T-0009", "work after the export")
    later = engine.ledger_read(root)
    assert later[-1]["hash"] != manifest["ledger"]["head"]
    assert later[manifest["ledger"]["checkpoint_n"] - 1]["hash"] == manifest["ledger"]["head"]
    assert engine.ledger_verify(root) == []
    assert "checkpoint_n" in manifest["ledger"]
    report = (docs / engine.F_AUDITREPORT).read_text(encoding="utf-8")
    assert f"checkpoint: record #{checkpoint}" in report


def test_a_corrupt_middle_line_does_not_fake_a_lagging_head_cache(tmp_path: Path) -> None:
    """The cache counts *valid* records; a torn middle line is not a lag.

    ``ledger_read`` inserts a ``<corrupt>`` placeholder for an unreadable line, so
    comparing the cache with its length made "the head cache is behind" permanent:
    ``--reconcile`` wrote the inflated number and the next append the valid one, so
    every later verify reported it again (T-0020/A8).
    """
    root = _seed(tmp_path / "team")
    path = engine.ledger_path(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    lines.insert(1, "{ not json")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    problems = engine.ledger_verify(root)
    assert problems == ["record 2: unreadable line in the ledger"], problems
    assert engine.ledger_verify(root, reconcile=True) == ["record 2: unreadable line in the ledger"]
    head = json.loads(engine.ledger_head_path(root).read_text(encoding="utf-8"))
    assert head["n"] == 3
    engine.ledger_append(root, "task.add", "ceo", "T-0004", "after the corrupt line")
    assert engine.ledger_verify(root) == ["record 2: unreadable line in the ledger"]


def test_loop_does_not_write_runtime_state(cli, project: Path, capsys) -> None:
    """``loop`` is a read: a lagging head cache is reported, never repaired there.

    The stop gate called ``ledger_verify(reconcile=True)``, so asking "may we
    stop?" rewrote ``Runtime/LedgerHead.json`` from a status command and parsed the
    ledger three times per call (T-0020/A14).
    """
    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    slug = engine.team_slug(project)
    root = (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()
    engine.ledger_append(root, "task.add", "ceo", "T-0001", "one")
    head = engine.ledger_head_path(root)
    current = json.loads(head.read_text(encoding="utf-8"))
    stale = json.dumps({"n": current["n"] - 1, "hash": current["hash"]}) + "\n"
    head.write_text(stale, encoding="utf-8")
    before = head.stat().st_mtime_ns

    capsys.readouterr()
    cli("--project", project, "loop")
    out = capsys.readouterr().out

    assert head.stat().st_mtime_ns == before, "a read-only status command rewrote the head cache"
    assert head.read_text(encoding="utf-8") == stale
    assert "teamwork.py ledger verify --reconcile" in out, out
    assert "head cache is behind" not in out, out


def test_an_unreadable_manifest_is_reported_by_ledger_verify(tmp_path: Path) -> None:
    project = tmp_path / "project"
    root = project / ".pi" / "Teamwork" / "Teams" / "T"
    root.mkdir(parents=True)
    (root / "Settings.json").write_text('{"TeamId": "team-a"}\n', encoding="utf-8")
    engine.ledger_append(root, "a", "ceo", "x", "one")
    docs = project / "docs" / "Team"
    docs.mkdir(parents=True)
    manifest = docs / "AuditManifest.json"
    manifest.write_text("{not json", encoding="utf-8")
    assert any("unreadable" in p and "manifest" in p for p in engine.ledger_verify(root))
    manifest.write_text('{"team_id": "team-a", "ledger": []}\n', encoding="utf-8")
    assert any("unreadable" in p and "manifest" in p for p in engine.ledger_verify(root))


def test_audit_trail_reports_an_unreadable_manifest(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    root = project / ".pi" / "Teamwork" / "Teams" / "T"
    root.mkdir(parents=True)
    (root / "Settings.json").write_text('{"TeamId": "team-a"}\n', encoding="utf-8")
    engine.ledger_append(root, "a", "ceo", "x", "one")
    docs = project / "docs" / "Team"
    docs.mkdir(parents=True)
    (docs / "AuditManifest.json").write_text("{not json", encoding="utf-8")
    hits = engine._audit_audit_trail_append_only_hash_chained(root, ["ceo"], None)
    out = capsys.readouterr().out
    assert hits >= 1
    assert "unreadable" in out


def test_an_absent_manifest_is_not_a_finding(tmp_path: Path) -> None:
    project = tmp_path / "project"
    root = project / ".pi" / "Teamwork" / "Teams" / "T"
    root.mkdir(parents=True)
    (root / "Settings.json").write_text('{"TeamId": "team-a"}\n', encoding="utf-8")
    engine.ledger_append(root, "a", "ceo", "x", "one")
    (project / "docs" / "Team").mkdir(parents=True)
    assert engine.ledger_verify(root) == []


APPEND_WORKER = """
import pathlib, sys, time
sys.path.insert(0, {src!r})
from teamwork import engine

root = pathlib.Path({root!r})
while not pathlib.Path({start!r}).exists():
    time.sleep(0.001)
record = engine.ledger_append(
    root, "task.add", "developer", "T-" + sys.argv[1], "concurrent writer"
)
print(record["n"])
"""


def test_concurrent_appends_from_separate_processes_leave_a_verifiable_chain(
    tmp_path: Path,
) -> None:
    """Eight writers appending at once leave one chain, one cache, no verify problem.

    The lock serialises read-tail -> append -> head-write, and the append re-checks
    under that lock that the tail it read is the tail it extends. A fork was
    possible before (M19 S-1: two writers inside the section, record 106 hashed
    against an empty ``prev`` while the file already held 105 records), and only
    ``ledger verify`` noticed, long after the records were written (T-0028).
    """
    root = tmp_path / "team"
    root.mkdir()
    start = tmp_path / "start"
    script = APPEND_WORKER.format(
        src=str(Path(engine.__file__).resolve().parents[1]),
        root=str(root),
        start=str(start),
    )
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(index)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(8)
    ]
    start.touch()
    written = []
    for worker in workers:
        out, err = worker.communicate(timeout=180)
        assert worker.returncode == 0, err
        written.append(int(out.strip().splitlines()[-1]))

    records = engine.ledger_read(root)
    assert sorted(written) == list(range(1, 9))
    assert [record["n"] for record in records] == list(range(1, 9))
    assert [record["prev"] for record in records] == [""] + [r["hash"] for r in records[:-1]]
    assert engine.ledger_verify(root) == []
    head = json.loads(engine.ledger_head_path(root).read_text(encoding="utf-8"))
    assert head == {"n": 8, "hash": records[-1]["hash"]}


LOCK_PROBE = """
import pathlib, sys
sys.path.insert(0, {src!r})
from teamwork import engine

try:
    with engine.lock(pathlib.Path({lock!r}), timeout=0.2):
        print("free")
except SystemExit:
    print("held")
"""


def test_ledger_verify_reads_the_file_and_the_head_inside_one_lock(
    tmp_path: Path, monkeypatch
) -> None:
    """The cache comparison happens under the ledger lock, not beside it.

    ``ledger_append`` writes the record line and then the head cache in one
    critical section, so the cache can never lead the file on its own. A verifier
    that read the file first and the cache second saw the writer's two halves as
    a truncation: Reviewer-2 measured "head cache knows 5442 records but the
    ledger has 5441" on an intact trail while other lanes appended (T-0122).
    """
    root = _seed(tmp_path / "team")
    lock_path = root / engine.DIR_RUNTIME / engine.DIR_LOCKS / "ledger.lock"
    probe = LOCK_PROBE.format(
        src=str(Path(engine.__file__).resolve().parents[1]), lock=str(lock_path)
    )
    real_read = engine.ledger_read
    seen: list[str] = []

    def spy(r):
        if not seen:
            run = subprocess.run(
                [sys.executable, "-c", probe], capture_output=True, text=True, timeout=120
            )
            seen.append(run.stdout.strip())
        return real_read(r)

    monkeypatch.setattr(engine, "ledger_read", spy)
    assert engine.ledger_verify(root) == []
    assert seen == ["held"], "ledger_verify read the ledger without the ledger lock"


LOOP_WORKER = """
import pathlib, sys, time
sys.path.insert(0, {src!r})
from teamwork import engine

root = pathlib.Path({root!r})
while not pathlib.Path({start!r}).exists():
    time.sleep(0.001)
for index in range({count}):
    engine.ledger_append(
        root, "task.add", "developer", sys.argv[1] + "-" + str(index), "loop writer"
    )
"""


def test_verify_stays_clean_while_two_lanes_append(tmp_path: Path) -> None:
    """Two appenders over 20 iterations each: no verify problem, cache == file.

    The read side is what T-0122 fixed: with the file and the cache read outside
    the lock, a verify interleaved with a concurrent append reported the trail as
    truncated while it was intact.
    """
    root = tmp_path / "team"
    root.mkdir()
    start = tmp_path / "start"
    script = LOOP_WORKER.format(
        src=str(Path(engine.__file__).resolve().parents[1]),
        root=str(root),
        start=str(start),
        count=20,
    )
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", script, name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for name in ("a", "b")
    ]
    start.touch()
    problems: list[str] = []
    while any(worker.poll() is None for worker in workers):
        problems += engine.ledger_verify(root)
    for worker in workers:
        _out, err = worker.communicate(timeout=180)
        assert worker.returncode == 0, err

    records = engine.ledger_read(root)
    head = json.loads(engine.ledger_head_path(root).read_text(encoding="utf-8"))
    assert problems == []
    assert [record["n"] for record in records] == list(range(1, 41))
    assert head == {"n": len(records), "hash": records[-1]["hash"]}
    assert engine.ledger_verify(root) == []


@pytest.mark.parametrize(
    "cache",
    [
        json.dumps({"n": 105, "hash": "a" * 64}),
        json.dumps({"n": 3, "hash": "b" * 64}),
        "{ not json",
    ],
    ids=["cache-ahead-of-the-file", "tail-hash-the-file-never-wrote", "unreadable"],
)
def test_a_desynchronised_head_cache_is_refused_instead_of_appended(
    cache: str, tmp_path: Path, capsys
) -> None:
    """Record 106's precondition: the cache and the file are not the same chain.

    Two writers inside ``ledger_append``'s critical section read a tail that was
    not the tail, so a record was chained to an empty ``prev`` while the file held
    105 records; ``ledger verify`` reported it afterwards. The append now refuses
    and writes nothing, which is what keeps the class out of the trail (T-0028).
    """
    root = _seed(tmp_path / "team")
    head = engine.ledger_head_path(root)
    head.write_text(cache + "\n", encoding="utf-8")
    ledger = engine.ledger_path(root)
    before, cached = ledger.read_text(encoding="utf-8"), head.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as refused:
        engine.ledger_append(root, "task.add", "developer", "T-0002", "must not land")

    assert refused.value.code == 1
    assert ledger.read_text(encoding="utf-8") == before
    assert head.read_text(encoding="utf-8") == cached
    assert "refusing to append a ledger record" in capsys.readouterr().err


def test_a_forked_tail_is_refused_rather_than_extended(tmp_path: Path, capsys) -> None:
    """Record 106 on disk: the last record links to ``prev=""`` but hashes itself.

    The cache agrees with the file the moment such a record lands, so the head
    check alone is blind to it. Extending the tail would bury the fork under every
    later record, so the append refuses on the chain check (T-0028).
    """
    root = _seed(tmp_path / "team")
    ledger = engine.ledger_path(root)
    forked = {
        "ts": "2026-10-29T00:00:00",
        "n": 4,
        "actor": "developer",
        "role": "developer",
        "action": "task.add",
        "target": "T-0002",
        "detail": "hashed against an empty prev",
        "rev": "",
        "prev": "",
    }
    forked["hash"] = engine._digest("", forked)
    with ledger.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(forked, sort_keys=True) + "\n")
    engine.ledger_head_path(root).write_text(
        json.dumps({"n": 4, "hash": forked["hash"]}) + "\n", encoding="utf-8"
    )
    before = ledger.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as refused:
        engine.ledger_append(root, "task.add", "developer", "T-0003", "extension")

    assert refused.value.code == 1
    assert ledger.read_text(encoding="utf-8") == before
    assert "the chain is broken at the tail" in capsys.readouterr().err


def test_a_tail_whose_digest_no_longer_matches_is_refused(tmp_path: Path, capsys) -> None:
    """An altered last record cannot be built on: the break would become permanent."""
    root = _seed(tmp_path / "team")
    ledger = engine.ledger_path(root)
    lines = ledger.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[-1])
    record["detail"] = "altered tail"
    lines[-1] = json.dumps(record, sort_keys=True)
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
    before = ledger.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as refused:
        engine.ledger_append(root, "task.add", "developer", "T-0004", "extension")

    assert refused.value.code == 1
    assert ledger.read_text(encoding="utf-8") == before
    assert "does not match its own digest" in capsys.readouterr().err


def test_a_lagging_head_cache_is_reconciled_before_the_append(tmp_path: Path, capsys) -> None:
    """A crash between the record and the head write must not block the trail.

    A cache naming record 1 of a three-record chain is exactly that artefact: the
    record reached the disk and the head write did not. The append names it and
    carries on, so the guard cannot turn a recoverable crash into a dead team.
    """
    root = _seed(tmp_path / "team")
    records = engine.ledger_read(root)
    engine.ledger_head_path(root).write_text(
        json.dumps({"n": 1, "hash": records[0]["hash"]}) + "\n", encoding="utf-8"
    )

    engine.ledger_append(root, "task.add", "developer", "T-0005", "after the crash")

    assert engine.ledger_verify(root) == []
    assert "reconciled before appending" in capsys.readouterr().err
    assert engine.ledger_read(root)[-1]["prev"] == records[-1]["hash"]


def test_a_transient_short_read_is_resolved_by_one_reread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reader that catches the file between two appends must not cry tampering.

    Measured on CI run 43344749792 (ubuntu 3.12): the head cache named 2 records
    while the file read named 1, and the trail was intact. One bounded re-read
    resolves it; a genuine truncation survives it (the next test).
    """
    root = _seed(tmp_path / "team")
    real = engine.ledger_read
    calls = {"n": 0}

    def short_then_full(path: Path) -> list:
        calls["n"] += 1
        records = real(path)
        return records[:-1] if calls["n"] == 1 else records

    monkeypatch.setattr(engine, "ledger_read", short_then_full)
    assert engine.ledger_verify(root) == []
    assert calls["n"] >= 2, "the cache-ahead branch must re-read the file"


def test_an_empty_reread_does_not_hide_a_truncation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The re-read must not overwrite the evidence with an empty list.

    The first fix assigned the second read unconditionally, so a truncation that
    landed between the two reads left ``valid == []`` and skipped every branch:
    `ledger verify` printed no problem on a trail the pre-change code refused.
    """
    root = _seed(tmp_path / "team")
    real = engine.ledger_read
    calls = {"n": 0}

    def short_then_empty(path: Path) -> list:
        calls["n"] += 1
        return real(path)[:-1] if calls["n"] == 1 else []

    monkeypatch.setattr(engine, "ledger_read", short_then_empty)
    problems = engine.ledger_verify(root)
    assert any("truncated" in problem for problem in problems), problems
