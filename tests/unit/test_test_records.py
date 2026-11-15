"""Unit tests for test-layer records: new_test_record, parse_tests, render_tests."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_a_layer_name_is_not_an_area() -> None:
    for layer in engine.TEST_LAYERS:
        assert engine.area_is_layer(layer)
        assert engine.area_is_layer(f" {layer.upper()} ")
        with pytest.raises(SystemExit):
            engine.check_area(layer, 2)
    assert not engine.area_is_layer("merge-identity")
    assert not engine.area_is_layer("")
    assert engine.check_area(" Merge-Identity ") == "merge-identity"


def test_check_area_keeps_the_path_gate() -> None:
    with pytest.raises(SystemExit):
        engine.check_area("tests/unit/test_ci_contracts.py", 2)
    assert engine.check_area("ci-matrix") == "ci-matrix"


def test_check_area_fails_with_a_nonzero_code_by_default() -> None:
    with pytest.raises(SystemExit) as exit_info:
        engine.check_area("unit")
    assert exit_info.value.code == 1


def test_tests_require_refuses_a_layer_as_its_area(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "team"
    root.mkdir()
    argv = [
        "--project",
        str(root),
        "tests",
        "require",
        "--area",
        "unit",
        "--layers",
        "unit,integration",
        "--by",
        "ceo",
        "--reason",
        "probe",
    ]
    with pytest.raises(SystemExit) as exit_info:
        engine.main(argv)
    assert exit_info.value.code == 1
    assert "is a test layer, not an area" in capsys.readouterr().err


def test_tests_require_accepts_a_subject_area(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "team"
    root.mkdir()
    argv = [
        "--project",
        str(root),
        "tests",
        "require",
        "--area",
        "Merge-Identity",
        "--layers",
        "unit,integration",
        "--by",
        "ceo",
        "--reason",
        "probe",
    ]
    with pytest.raises(SystemExit):
        engine.main(argv)
    err = capsys.readouterr().err
    assert "not an area" not in err
    assert "unknown actor 'ceo'" in err


def test_an_area_with_no_test_record_is_flagged_when_it_is_chosen(
    cli, project: Path, capsys
) -> None:
    """The gap trap is named where the area is chosen, not at close (K-0036).

    Measured: a new area on a finished task makes `tests plan` require
    unit/integration/acceptance for it, and three tasks paid a whole extra lane to
    record the layers after the fact.
    """
    assert (
        cli(
            "--project",
            project,
            "init",
            "--agents",
            "ceo,developer-1,tester-1,reviewer-1",
            "--no-git",
        )
        == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "task", "add", "developer", "a new subject") == 0
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--area", "brand-new") == 0
    )
    out = capsys.readouterr().out
    assert "has no test record for" in out, out
    assert "brand-new" in out

    for layer in ("unit", "integration", "acceptance"):
        assert (
            cli("--project", project, "tests", "add", "--layer", layer, "--area", "brand-new") == 0
        )
    capsys.readouterr()
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--area", "brand-new") == 0
    )
    assert "has no test record for" not in capsys.readouterr().out


def test_a_command_already_recorded_in_another_layer_is_refused(cli, project: Path, capsys) -> None:
    """One command, one thing tested: the audit reported the duplicate pairs for months.

    `tests add` printed a note and recorded the twin anyway, so the same suite ran
    under `unit` and `acceptance` and the audit carried two duplicate-command
    findings. It refuses now, and `--force <reason>` is the honest exception.
    """
    assert (
        cli(
            "--project",
            project,
            "init",
            "--agents",
            "ceo,developer-1,tester-1,reviewer-1",
            "--no-git",
        )
        == 0
    )
    command = "pytest -q tests/unit"
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            "unit",
            "--area",
            "dup",
            "--command",
            command,
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            "integration",
            "--area",
            "dup",
            "--command",
            command,
        )
        == 2
    )
    captured = capsys.readouterr()
    assert "one command per thing tested" in captured.out + captured.err
    forced = cli(
        "--project",
        project,
        "tests",
        "add",
        "--layer",
        "integration",
        "--area",
        "dup",
        "--command",
        command,
        "--force",
        "the integration layer needs the same command for this area",
    )
    tail = capsys.readouterr()
    assert forced == 0, tail.out + tail.err
