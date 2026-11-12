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
    assert not path.exists()


def test_render_tests_default_path_renders_a_generic_header() -> None:
    """Regression (T-0017): path=None crashed with UnboundLocalError.

    render_tests follows the renderers that do fall back when there is no file to
    link from - render_criteria and render_testplan - so the header is the bare H1
    title and carries no Related line. render_tasks and render go through
    header_for, which deliberately refuses a missing path (records.py:1197-1204);
    that guard is intentional and stays.
    """
    text = engine.render_tests([engine.new_test_record("unit", "names")])
    assert text.startswith("# Tests - one record per test layer and area\n\n")
    assert "Related:" not in text
    assert "## TS-0001 · unit · names" in text


def test_render_tests_with_path_links_the_sibling_documents(tmp_path: Path) -> None:
    """The other arm still links its siblings, so the fix cannot just drop them."""
    text = engine.render_tests([engine.new_test_record("unit", "names")], tmp_path / "Tests.md")
    assert "Related: [test plan](" in text
    assert "[criteria](" in text


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


def test_an_area_is_a_subject_not_a_test_file_path() -> None:
    assert engine.area_looks_like_path("tests/unit/test_ci_contracts.py")
    assert engine.area_looks_like_path("tests\\unit\\test_ci_contracts.py")
    assert engine.area_looks_like_path("test_ci_contracts.py")
    assert engine.area_looks_like_path("tests-unit-test-ci-contr")
    assert engine.area_looks_like_path("tests-unit")
    assert not engine.area_looks_like_path("ci-matrix")
    assert not engine.area_looks_like_path("memory-injection")
    assert not engine.area_looks_like_path("")
    assert not engine.area_looks_like_path("testing")
