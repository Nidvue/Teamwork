"""Unit: a verification claim carries the context that produced it.

Layer ``unit``, area ``evidence-staleness``, owner Developer (T-0001, D-20261120-CEO-5).

The engine binds evidence to one revision. That half of the rule is worthless
inside one long lane: the tree never moved, but the model that ran the command
no longer holds its output - a context compaction replaced it with a summary.
So a record also carries the context epoch of the run that wrote it, and a
citation from an earlier epoch of the same session is refused.

Owner: developer. Related: references/Evidence.md
"""

from __future__ import annotations

import json

from teamwork import ctxepoch
from teamwork.records import new_test_record, parse_tests, render_tests


def _session(tmp_path, compactions: int) -> str:
    path = tmp_path / "session.jsonl"
    lines = [
        json.dumps({"type": "user", "id": "a1", "message": "run the gate"}),
        json.dumps({"type": "assistant", "id": "a2", "message": "2794 passed"}),
    ]
    for n in range(compactions):
        lines.append(
            json.dumps(
                {
                    "type": "compaction",
                    "id": f"c{n}",
                    "summary": "## Goal",
                    "firstKeptEntryId": "a2",
                    "tokensBefore": 120000 + n,
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def test_the_epoch_names_the_session_and_its_compaction_count(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PI_SESSION_ID", "sess-1")
    monkeypatch.setenv("PI_SESSION_FILE", _session(tmp_path, 2))
    assert ctxepoch.epoch() == "sess-1@2"


def test_a_missing_session_leaves_the_epoch_empty(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("PI_SESSION_ID", raising=False)
    monkeypatch.delenv("PI_SESSION_FILE", raising=False)
    assert ctxepoch.epoch() == ""


def test_a_named_session_without_a_file_reads_as_unknown(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PI_SESSION_ID", "sess-2")
    monkeypatch.setenv("PI_SESSION_FILE", str(tmp_path / "absent.jsonl"))
    assert ctxepoch.epoch() == "sess-2@?"


def test_only_the_same_session_can_be_found_stale() -> None:
    assert ctxepoch.stale("sess-1@1", "sess-1@2")
    assert not ctxepoch.stale("sess-1@2", "sess-1@2")
    assert not ctxepoch.stale("sess-1@1", "sess-2@3")
    assert not ctxepoch.stale("", "sess-1@2")
    assert not ctxepoch.stale("sess-1@?", "sess-1@2")


def test_a_test_record_carries_the_epoch_of_the_run_that_wrote_it(tmp_path) -> None:
    record = new_test_record("unit", "evidence-staleness", command="pytest @x -> 1 passed")
    record["epoch"] = "sess-1@0"
    text = render_tests([record])
    assert "- epoch: sess-1@0" in text
    round_tripped = next(
        r for r in parse_tests(_write(tmp_path, text)) if r["area"] == "evidence-staleness"
    )
    assert round_tripped["epoch"] == "sess-1@0"


def _write(tmp_path, text: str):
    path = tmp_path / "Tests.md"
    path.write_text(text, encoding="utf-8")
    return path
