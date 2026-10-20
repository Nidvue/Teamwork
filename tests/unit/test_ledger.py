"""Unit tests for the hash-chained audit ledger: digest and verification."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from teamwork import engine

ZERO = "0" * 64
# Frozen digest of {"a": 1} with a zero previous hash. Changing the record shape,
# the canonical JSON encoding or the hash function must fail this test.
FROZEN_DIGEST = "fc6cee09194dd2578bd7664604fcb72a539066fd34544cea0009c43eb6cdc289"


def _seed(root: Path) -> Path:
    """Append three records so the chain has a middle worth tampering with."""
    root.mkdir(parents=True, exist_ok=True)
    engine.ledger_append(root, "task.add", "developer", "T-0001", "first")
    engine.ledger_append(root, "task.claim", "developer", "T-0001", "second")
    engine.ledger_append(root, "tests.run", "developer", "TS-0001", "third")
    return root


# --------------------------------------------------------------------------- #
# _digest
# --------------------------------------------------------------------------- #


def test_digest_is_deterministic() -> None:
    assert engine._digest(ZERO, {"a": 1}) == engine._digest(ZERO, {"a": 1})


def test_digest_frozen_known_value() -> None:
    assert engine._digest(ZERO, {"a": 1}) == FROZEN_DIGEST


def test_digest_depends_on_record_body() -> None:
    assert engine._digest(ZERO, {"a": 1}) != engine._digest(ZERO, {"a": 2})


def test_digest_depends_on_previous_hash() -> None:
    assert engine._digest(ZERO, {"a": 1}) != engine._digest("1" * 64, {"a": 1})


def test_digest_ignores_the_hash_field() -> None:
    # ``hash`` is excluded from the canonical body, so a stale/forged hash field
    # does not change the digest.
    left = engine._digest(ZERO, {"a": 1, "hash": "aaa"})
    right = engine._digest(ZERO, {"a": 1, "hash": "bbb"})
    assert left == right


def test_canon_is_order_independent_sorted_json() -> None:
    left = engine._canon({"b": 1, "a": 2})
    right = engine._canon({"a": 2, "b": 1})
    assert left == right == '{"a":2,"b":1}'


# --------------------------------------------------------------------------- #
# good chain
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# tampered chains
# --------------------------------------------------------------------------- #


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

    # ``reconcile=True`` repairs the crash artefact instead of reporting it.
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

    # the checkpoint names the export event, and its hash is that record's hash
    checkpoint = manifest["ledger"]["checkpoint_n"]
    records = engine.ledger_read(root)
    assert records[checkpoint - 1]["action"] == "ledger.export"
    assert manifest["ledger"]["head"] == records[checkpoint - 1]["hash"]

    # later work moves the head; the checkpoint still resolves to the same record
    engine.ledger_append(root, "task.add", "ceo", "T-0009", "work after the export")
    later = engine.ledger_read(root)
    assert later[-1]["hash"] != manifest["ledger"]["head"]
    assert later[manifest["ledger"]["checkpoint_n"] - 1]["hash"] == manifest["ledger"]["head"]
    assert engine.ledger_verify(root) == []
    assert "checkpoint_n" in manifest["ledger"]
    report = (docs / engine.F_AUDITREPORT).read_text(encoding="utf-8")
    assert f"checkpoint: record #{checkpoint}" in report
