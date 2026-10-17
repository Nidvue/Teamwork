"""Unit tests for test-layer records: new_test_record, parse_tests, render_tests."""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def test_new_test_record_defaults() -> None:
    record = engine.new_test_record(" Unit ", " API ")
    assert record["layer"] == "unit"
    assert record["area"] == "api"
    assert record["status"] == "pending"
    assert record["id"] == ""
    assert record["evidence"] == ""
    assert record["updated"] == engine.today_iso()


def test_parse_tests_missing_file_is_empty(tmp_path: Path) -> None:
    assert engine.parse_tests(tmp_path / "missing.md") == []


def test_test_record_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "Tests.md"
    record = engine.new_test_record(
        "integration", "ledger", owner="tester-1", command="pytest tests/integration -q"
    )
    engine.write_tests(path, [record])

    out = engine.parse_tests(path)
    assert len(out) == 1
    assert out[0]["id"] == "TS-0001"
    assert out[0]["layer"] == "integration"
    assert out[0]["area"] == "ledger"
    assert out[0]["owner"] == "tester-1"
    assert out[0]["command"] == "pytest tests/integration -q"
    assert out[0]["status"] == "pending"


def test_render_tests_splits_layer_and_area(tmp_path: Path) -> None:
    path = tmp_path / "Tests.md"
    text = engine.render_tests([engine.new_test_record("unit", "names", owner="developer-1")], path)
    assert "## TS-0001 · unit · names" in text
    # Rendering is pure: it must not write the file itself.
    assert not path.exists()


def test_render_tests_orders_by_layer_then_area(tmp_path: Path) -> None:
    path = tmp_path / "Tests.md"
    records = [
        engine.new_test_record("integration", "b"),
        engine.new_test_record("unit", "z"),
        engine.new_test_record("unit", "a"),
    ]
    text = engine.render_tests(records, path)
    assert text.index("unit · a") < text.index("unit · z") < text.index("integration · b")


def test_find_test_by_id_then_area() -> None:
    records = [
        engine.new_test_record("unit", "api"),
        engine.new_test_record("integration", "ledger"),
    ]
    records[0]["id"] = "TS-0001"
    records[1]["id"] = "TS-0002"
    assert engine.find_test(records, "TS-0002") == 1
    assert engine.find_test(records, "ledger") == 1
    assert engine.find_test(records, "missing") is None
