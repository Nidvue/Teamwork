"""The provider caps are a committed rule, so config and the pages must agree.

T-0033: `DEFAULT_PROVIDER_LIMITS` said ten lanes while the teammate harness
offered sixty-four, so dispatch serialised a team it could have run in parallel.
The cap is now raised everywhere, and this test is what keeps the pages and the
constant from drifting apart again - a reviewer found that reverting the
constant left the whole suite green.
"""

from __future__ import annotations

import re
from pathlib import Path

from teamwork import config

CAP_MENTION = re.compile(r"ollama-cloud|Ollama Cloud", re.IGNORECASE)

CAP_CLAIM = re.compile(
    r"(?:ollama-cloud|Ollama Cloud)[^\n]{0,40}\d|\d[^\n]{0,40}(?:ollama-cloud|Ollama Cloud)",
    re.IGNORECASE,
)

DISCOVERY_FILES = ("README.md", "AGENTS.md", "SKILL.md")

DISCOVERY_DIRS = ("docs", "references", "roles", "templates")

HISTORICAL_PREFIXES = ("docs/Team/",)

RETIRED = re.compile(r"(?:ollama-cloud[^\n]{0,20}\b10\b|\b10\b[^\n]{0,20}Ollama Cloud)")


def cap_pages(root: Path) -> list[tuple[str, str]]:
    """``(relative path, text)`` for every page that states a provider cap.

    Discovery, not a list: the README restructure moved the ``parallel``
    transcript and a hardcoded list kept demanding a statement from the page that
    no longer made one. A page is in this contract when it *claims* a cap - the
    provider name next to a number, or a ``cap=`` transcript - so a page that only
    names the provider as a model source stays out. Historical team records under
    ``docs/Team/`` are quotations, never a page this contract governs.
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
        if CAP_MENTION.search(text) and CAP_CLAIM.search(text):
            found.append((rel, text))
    return found


def cap_problems(root: Path) -> list[str]:
    """Every page that states a cap but not the enforced number."""
    cap = config.DEFAULT_PROVIDER_LIMITS["ollama-cloud"]
    problems = []
    for rel, text in cap_pages(root):
        if re.search(r"Ollama Cloud[^\n]{0,40}~10\b", text) or RETIRED.search(text):
            problems.append(f"{rel}: still states the retired 10-lane cap")
        states_cap = re.search(
            rf"(?:ollama-cloud|Ollama Cloud)[^\n]{{0,40}}\b{cap}\b", text, re.IGNORECASE
        ) or re.search(rf"\b{cap}\b[^\n]{{0,40}}(?:ollama-cloud|Ollama Cloud)", text, re.IGNORECASE)
        if not states_cap:
            problems.append(f"{rel}: states the provider cap but not the enforced number {cap}")
    return problems


def test_the_default_caps_are_the_measured_ones() -> None:
    assert config.DEFAULT_PROVIDER_LIMITS["ollama-cloud"] == 64
    assert config.DEFAULT_PROVIDER_LIMITS["default"] == 32
    assert config.DEFAULT_PROVIDER_LIMITS["deepseek"] == 2500
    assert config.DEFAULT_PROVIDER_LIMITS["openai"] == 64
    assert config.DEFAULT_PROVIDER_LIMITS["anthropic"] == 64


def test_every_page_that_states_the_cap_states_the_enforced_number(repo_root: Path) -> None:
    pages = cap_pages(repo_root)
    assert len(pages) >= 5, (
        "the discovery found almost no page stating a provider cap, so the guard is "
        f"vacuous: {[rel for rel, _ in pages]}"
    )
    assert cap_problems(repo_root) == []


def test_a_page_that_prints_a_cap_transcript_is_discovered(repo_root: Path) -> None:
    """The move class: a transcript on a page the old list did not name is judged.

    This is the regression for the README restructure: the ``cap=64`` transcript
    moved to ``docs/guide/usage.md`` while the guard still read the README. The
    guard must discover a page from its content, or a move silently stops being
    checked.
    """
    transcripts = [
        rel
        for rel, text in cap_pages(repo_root)
        if re.search(r"cap=\d+", text) and CAP_MENTION.search(text)
    ]
    assert transcripts, "no discovered page prints a cap transcript; the probe is vacuous"


def test_mutant_a_new_page_stating_a_cap_is_discovered_and_judged(tmp_path: Path) -> None:
    page = tmp_path / "docs" / "guide" / "new-cap-page.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "# New page\n\nThe pool is `ollama-cloud` with cap=10 lanes.\n", encoding="utf-8"
    )

    assert [rel for rel, _ in cap_pages(tmp_path)] == ["docs/guide/new-cap-page.md"]
    problems = cap_problems(tmp_path)
    assert any("new-cap-page.md" in problem for problem in problems), problems


def test_mutant_moving_the_claim_to_a_new_page_is_still_checked(tmp_path: Path) -> None:
    moved = tmp_path / "docs" / "guide" / "moved.md"
    moved.parent.mkdir(parents=True)
    moved.write_text(
        "# Moved transcript\n\n## provider slots\n- ollama-cloud used=0 cap=64 free=64\n",
        encoding="utf-8",
    )
    assert [rel for rel, _ in cap_pages(tmp_path)] == ["docs/guide/moved.md"]
    assert cap_problems(tmp_path) == []

    moved.write_text(moved.read_text(encoding="utf-8").replace("cap=64", "cap=10"), "utf-8")
    problems = cap_problems(tmp_path)
    assert any("moved.md" in problem for problem in problems), problems


def test_historical_team_quotes_are_not_read_into_the_contract(tmp_path: Path) -> None:
    archive = tmp_path / "docs" / "Team" / "Archive.md"
    archive.parent.mkdir(parents=True)
    archive.write_text(
        "- quoted evidence: the pool said Ollama Cloud cap=10 in 2025\n", encoding="utf-8"
    )
    assert cap_pages(tmp_path) == []
    assert cap_problems(tmp_path) == []


def test_the_cap_is_not_left_at_the_retired_bound(repo_root: Path) -> None:
    """Non-vacuity: the old 10/8 pair must not come back unnoticed."""
    text = (repo_root / "src" / "teamwork" / "config.py").read_text(encoding="utf-8")
    block = text[
        text.index("DEFAULT_PROVIDER_LIMITS") : text.index(
            "}", text.index("DEFAULT_PROVIDER_LIMITS")
        )
    ]
    assert '"ollama-cloud": 10' not in block
    assert '"default": 8' not in block


def test_a_settings_only_key_never_becomes_a_provider_cap(tmp_path: Path) -> None:
    """`ReviewLeaseMaxMinutes` is a review setting, not a model provider.

    Settings.json also carries provider caps, and load_providers treats every key
    it does not know as one. A missing entry in SETTINGS_NON_PROVIDER therefore
    turns a documented review setting into a phantom pool and inflates the free
    slot count the CEO scales lanes on.
    """
    from teamwork import engine

    assert "ReviewLeaseMaxMinutes" in config.SETTINGS_NON_PROVIDER
    assert "ReviewLeaseMinutes" in config.SETTINGS_NON_PROVIDER
    root = tmp_path / ".pi" / "Teamwork" / "Teams" / "Probe"
    root.mkdir(parents=True)
    engine.providers_path(root).write_text(
        '{"ReviewLeaseMaxMinutes": 30, "ollama-cloud": 64}', encoding="utf-8"
    )
    caps = engine.load_providers(root)
    assert "ReviewLeaseMaxMinutes" not in caps
    assert caps["ollama-cloud"] == 64
