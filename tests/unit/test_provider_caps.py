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

# every page that states the provider cap to a reader
CAP_PAGES = (
    "AGENTS.md",
    "templates/AGENTS.md",
    "references/Concurrency.md",
    "templates/TeamMap.md",
    "roles/ceo.md",
    "SKILL.md",
    "README.md",
)

# any stated cap must be the enforced one, in either word order
RETIRED = re.compile(r"(?:ollama-cloud[^\n]{0,20}\b10\b|\b10\b[^\n]{0,20}Ollama Cloud)")


def test_the_default_caps_are_the_measured_ones() -> None:
    assert config.DEFAULT_PROVIDER_LIMITS["ollama-cloud"] == 64
    assert config.DEFAULT_PROVIDER_LIMITS["default"] == 32
    assert config.DEFAULT_PROVIDER_LIMITS["deepseek"] == 2500
    assert config.DEFAULT_PROVIDER_LIMITS["openai"] == 64
    assert config.DEFAULT_PROVIDER_LIMITS["anthropic"] == 64


def test_every_page_that_states_the_cap_states_the_enforced_number(repo_root: Path) -> None:
    cap = config.DEFAULT_PROVIDER_LIMITS["ollama-cloud"]
    for rel in CAP_PAGES:
        text = (repo_root / rel).read_text(encoding="utf-8")
        assert re.search(r"ollama-cloud|Ollama Cloud", text, re.I), (
            f"{rel} no longer states the provider cap"
        )
        # the old bound was written as "~10" or "~10 concurrent agents"
        assert not re.search(r"Ollama Cloud[^\n]{0,40}~10\b", text), (
            f"{rel} still states the retired ~10 bound"
        )
        assert not RETIRED.search(text), f"{rel} still states the retired 10-lane cap"
        states_cap = re.search(
            rf"(?:ollama-cloud|Ollama Cloud)[^\n]{{0,40}}\b{cap}\b", text, re.I
        ) or re.search(rf"\b{cap}\b[^\n]{{0,40}}(?:ollama-cloud|Ollama Cloud)", text, re.I)
        assert states_cap, f"{rel} does not state the enforced cap {cap}"


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
