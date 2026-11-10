"""The guard that turns an absent external tool into a skip, not a failure.

Regression for ``T-0003``: measured at ``7db810a`` on a host without GNU make,
``pytest -q tests/unit/test_makefile_contracts.py`` ended in
``FileNotFoundError [WinError 2] 'make'`` while CI - which has make - stayed
green. A contributor saw a broken suite, and the report told them nothing about
what was missing or why the test wanted it.

What is pinned here:

1. :func:`tests.tooling.require_tool` **skips** when ``shutil.which`` finds
   nothing, and the skip text names the tool *and* states why the test needs it;
2. it does **not** skip when the tool is present, so the guard cannot be used to
   hide a test that should run;
3. the three make-driven modules really are behind it - proved by calling them
   with ``shutil.which`` patched to ``None``, which is the exact defect above;
4. no test in the tree executes a guarded tool without the guard, so the next
   test that shells out cannot silently reintroduce the failure.

The last test records the deliberate *other* half of the audit: ``git`` and the
interpreter are not guarded, because the product cannot run without them.
"""

from __future__ import annotations

import ast
import importlib
import shutil
import sys
from pathlib import Path

import pytest
from tests.tooling import (
    GENERIC_REASON,
    GUARDED_TOOLS,
    TOOL_REASONS,
    missing_tool,
    require_tool,
    skip_message,
)

TESTS = Path(__file__).resolve().parents[1]
UNIT = TESTS / "unit"
INTEGRATION = TESTS / "integration"

#: The ``subprocess`` entry points a test uses to execute a program.
PROCESS_CALLS = frozenset({"run", "call", "check_call", "check_output", "Popen"})

#: The two spellings of the guard: the direct call and the shared message builder
#: (used where the tool's own resolution, not ``shutil.which``, is the authority).
GUARD_CALLS = ("require_tool(", "skip_message(")


def absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every ``shutil.which`` lookup miss, as on a host without the tool."""
    monkeypatch.setattr(shutil, "which", lambda _name: None)


def present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every ``shutil.which`` lookup hit, as on a host with the tool."""
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")


# --------------------------------------------------------------------------- #
# the guard's own contract
# --------------------------------------------------------------------------- #


def test_the_guard_skips_and_names_the_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    absent(monkeypatch)

    with pytest.raises(pytest.skip.Exception) as skipped:
        require_tool("make")

    message = str(skipped.value)
    assert "make" in message, f"the skip does not name the tool: {message}"
    assert "not installed" in message, message


def test_the_guard_states_why_the_test_needs_the_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """A skip without a reason is a disabled test with extra steps."""
    absent(monkeypatch)
    assert TOOL_REASONS["make"], "make has no stated reason"

    with pytest.raises(pytest.skip.Exception) as skipped:
        require_tool("make")

    assert TOOL_REASONS["make"] in str(skipped.value)


def test_a_tool_with_no_listed_reason_still_states_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tool added later cannot skip with no reason at all."""
    absent(monkeypatch)

    with pytest.raises(pytest.skip.Exception) as skipped:
        require_tool("zz-no-such-tool")

    message = str(skipped.value)
    assert "zz-no-such-tool" in message, message
    assert GENERIC_REASON in message, message


def test_the_reason_for_a_missing_tool_is_one_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Detail is appended, not substituted, so the reason is never lost."""
    absent(monkeypatch)

    with pytest.raises(pytest.skip.Exception) as skipped:
        require_tool("bash", "which bash -> None")

    message = str(skipped.value)
    assert TOOL_REASONS["bash"] in message
    assert "which bash -> None" in message
    assert skip_message("bash", "which bash -> None") == message


def test_the_guard_does_not_skip_when_the_tool_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    present(monkeypatch)

    assert not missing_tool("make")
    require_tool("make")  # no ``pytest.raises``: falling through is the assertion


# --------------------------------------------------------------------------- #
# the defect itself: the make-driven modules skip instead of failing
# --------------------------------------------------------------------------- #


def guarded_test_module(directory: Path, name: str):
    """A sibling test module, imported by file name the way pytest imports it.

    The import is dynamic and by module: a plain ``from module import test_x``
    would put that test in this namespace, where pytest would collect it a second
    time (and skip it here) instead of measuring one contract once.
    """
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    return importlib.import_module(name)


def test_the_makefile_help_contract_skips_instead_of_failing_without_make(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The measured defect, reproduced: no make -> a skip that names make.

    The real test is called, not a copy of it, so the assertion below cannot
    drift from the contract it guards.
    """
    absent(monkeypatch)
    contract = guarded_test_module(UNIT, "test_makefile_contracts")

    with pytest.raises(pytest.skip.Exception) as skipped:
        contract.test_make_help_lists_every_documented_target()

    assert "make" in str(skipped.value)


def test_the_integration_makefile_flow_skips_instead_of_failing_without_make(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The file's autouse fixture routes through the same guard."""
    absent(monkeypatch)
    flow = guarded_test_module(INTEGRATION, "test_makefile_flow")

    with pytest.raises(pytest.skip.Exception) as skipped:
        flow.make_required()

    assert "make" in str(skipped.value)


# --------------------------------------------------------------------------- #
# anti-vacuity: the guard cannot be dropped from an existing or a new test
# --------------------------------------------------------------------------- #


def guarded_tool_runs() -> list[tuple[Path, str]]:
    """Every ``(module, tool)`` where a test executes a tool the suite guards."""
    runs: list[tuple[Path, str]] = []
    for path in sorted(TESTS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr not in PROCESS_CALLS:
                continue
            argv = node.args[0]
            if not isinstance(argv, (ast.List, ast.Tuple)) or not argv.elts:
                continue
            head = argv.elts[0]
            if isinstance(head, ast.Constant) and head.value in GUARDED_TOOLS:
                runs.append((path, str(head.value)))
    return runs


def test_no_test_executes_a_guarded_tool_without_the_guard() -> None:
    """A new test that shells out to make must carry the guard, not rediscover it."""
    runs = guarded_tool_runs()
    assert runs, "the scan found no guarded-tool invocation, so this check is vacuous"

    unguarded: list[str] = []
    for path in {path for path, _tool in runs}:
        source = path.read_text(encoding="utf-8")
        if not any(call in source for call in GUARD_CALLS):
            tools = sorted({tool for run_path, tool in runs if run_path == path})
            unguarded.append(f"{path.name} executes {tools} with no guard")

    assert unguarded == [], unguarded


def test_git_and_the_interpreter_are_deliberately_not_guarded() -> None:
    """Skipping these would report a green build for a host that cannot run the product.

    ``teamwork`` commits, branches and audits through git, so a host without it
    cannot run the thing under test; the loud failure is the honest signal. This
    assertion is the decision, recorded where the temptation to "fix" it lives.
    """
    assert GUARDED_TOOLS == frozenset({"make", "sh", "bash"})
    assert "git" not in GUARDED_TOOLS
