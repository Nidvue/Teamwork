"""The always-on cap is a committed rule, so config and the pages must agree.

The enforced cap is ``DEFAULT_ALWAYS_ON_BUDGET_KB`` in ``config.py`` (104 KiB =
106496 B), which ``harness budget`` prints. The constitution, skill and role
pages quoted 122880 B / 120 KiB after the constant was lowered, so a reader
following the prose would size an instance against a cap that is no longer
enforced. This guard discovers every living page that states the cap and
asserts it states the enforced number; a reviewer found that reverting the
constant left the whole suite green until this test existed.
"""

from __future__ import annotations

import re
from pathlib import Path

from teamwork import config

EXPECTED_BYTES = config.DEFAULT_ALWAYS_ON_BUDGET_KB * 1024
EXPECTED_KIB = config.DEFAULT_ALWAYS_ON_BUDGET_KB

CAP_MENTION = re.compile(r"AlwaysOnBudgetKb|\b\d+\s*KiB\s+cap\b", re.IGNORECASE)

STALE_VALUE = re.compile(r"\b122880\b|\b120\s*KiB\b", re.IGNORECASE)

EXPECTED_VALUE = re.compile(rf"\b{EXPECTED_BYTES}\b|\b{EXPECTED_KIB}\s*KiB\b", re.IGNORECASE)

DISCOVERY_FILES = ("README.md", "AGENTS.md", "SKILL.md", "templates/AGENTS.md")

DISCOVERY_DIRS = ("references", "roles")

HISTORICAL_PREFIXES = ("docs/Team/",)


def cap_pages(root: Path) -> list[tuple[str, str]]:
    """``(relative path, text)`` for every living page that states the cap.

    Discovery, not a list: a page is in this contract when it claims a cap -
    it names ``AlwaysOnBudgetKb`` or prints a ``<n> KiB cap`` phrase - so a
    page that only links to the budget command stays out. Team records under
    ``docs/Team/`` are quotations and decisions frozen at their date, never a
    page this contract governs; ``docs/Team/Archive.md`` is one of them.
    """
    paths = [root / name for name in DISCOVERY_FILES]
    for directory in DISCOVERY_DIRS:
        paths.extend(sorted((root / directory).rglob("*.md")))
    found = []
    for path in sorted({path for path in paths if path.is_file()}):
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in HISTORICAL_PREFIXES):
            continue
        text = path.read_text(encoding="utf-8")
        if CAP_MENTION.search(text):
            found.append((rel, text))
    return found


def cap_problems(root: Path) -> list[str]:
    """Every page that states the cap but not the enforced number."""
    problems = []
    for rel, text in cap_pages(root):
        if STALE_VALUE.search(text):
            problems.append(f"{rel}: still states a retired cap value")
        if not EXPECTED_VALUE.search(text):
            problems.append(f"{rel}: states the cap but not the enforced {EXPECTED_BYTES} B")
    return problems


def test_the_enforced_cap_is_the_measured_one() -> None:
    assert config.DEFAULT_ALWAYS_ON_BUDGET_KB == 104
    assert EXPECTED_BYTES == 106496
    assert EXPECTED_KIB == 104


def test_every_page_that_states_the_cap_states_the_enforced_number(repo_root: Path) -> None:
    pages = cap_pages(repo_root)
    assert len(pages) >= 4, (
        "the discovery found almost no page stating the cap, so the guard is "
        f"vacuous: {[rel for rel, _ in pages]}"
    )
    assert cap_problems(repo_root) == []


def test_historical_team_records_are_not_read_into_the_contract(tmp_path: Path) -> None:
    for rel in ("docs/Team/Archive.md", "docs/Team/Decisions.md", "docs/Team/Throughput.md"):
        page = tmp_path / rel
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("The cap is `AlwaysOnBudgetKb` (122880 B default).\n", encoding="utf-8")
    assert cap_pages(tmp_path) == []
    assert cap_problems(tmp_path) == []


def test_a_stale_value_is_flagged_then_cleared_when_the_page_is_restored(tmp_path: Path) -> None:
    page = tmp_path / "references" / "State.md"
    page.parent.mkdir(parents=True)
    page.write_text("The cap is `AlwaysOnBudgetKb` (122880 B default).\n", encoding="utf-8")

    assert [rel for rel, _ in cap_pages(tmp_path)] == ["references/State.md"]
    assert cap_problems(tmp_path)

    page.write_text(
        page.read_text(encoding="utf-8").replace("122880", str(EXPECTED_BYTES)), encoding="utf-8"
    )
    assert cap_problems(tmp_path) == []
