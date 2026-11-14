"""The intake skill is wired in, and the wiring cannot rot.

A method that lives only in a conversation is lost the first time the
conversation ends. ``.agents/skills/tw-brief-intake/SKILL.md`` is the procedure,
and this module pins the four surfaces that have to name it: Bootstrap step 1,
the project template's ``## Brief`` slot, the CEO and Product Manager charters,
and the skill file's own contract. Every assertion reads a shipped file, so a
rewording that drops a step fails here instead of being discovered by the lane
that then invents its own intake.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".agents/skills/tw-brief-intake/SKILL.md"
BOOTSTRAP = ROOT / "references/Bootstrap.md"
PROJECT_TEMPLATE = ROOT / "templates/Docs/Project.md"
ROOT_SKILL = ROOT / "SKILL.md"
CHARTERS = (ROOT / "roles/ceo.md", ROOT / "roles/product-manager.md")

STEPS = (
    "Record the prompt verbatim",
    "Deep-research its intention",
    "Rewrite the brief",
    "Freeze",
    "Independent read",
)
BRIEF_PARTS = (
    "Objective",
    "User and job",
    "Deliverables",
    "Acceptance criteria",
    "Non-goals",
    "Constraints and invariants",
    "Interfaces to freeze",
    "Lanes",
    "Unknowns and assumptions",
    "Evidence plan",
)


def test_the_skill_file_exists_with_its_front_matter() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "name: tw-brief-intake" in text
    assert "kind: workflow" in text
    assert "description:" in text


def test_the_bootstrap_names_every_step_of_the_flow() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")

    assert "tw-brief-intake" in text, "step 1 does not name the skill that carries the flow"
    missing = [step for step in STEPS if step not in text]
    assert not missing, f"step 1 dropped {missing}"


def test_the_skill_carries_the_ten_part_template() -> None:
    text = SKILL.read_text(encoding="utf-8")

    missing = [part for part in BRIEF_PARTS if part not in text]
    assert not missing, f"the brief template lost {missing}"


def test_the_project_template_has_the_brief_slot() -> None:
    text = PROJECT_TEMPLATE.read_text(encoding="utf-8")

    assert "## Brief" in text
    assert "### Original prompt (verbatim)" in text
    assert "### Rewritten brief" in text
    assert "tw-brief-intake" in text, "the template must point at the procedure that fills it"


def test_the_root_skill_and_the_two_charters_name_the_skill() -> None:
    assert "tw-brief-intake" in ROOT_SKILL.read_text(encoding="utf-8")
    for charter in CHARTERS:
        assert "tw-brief-intake" in charter.read_text(encoding="utf-8"), charter


def test_the_rewrite_rules_and_the_guardrails_are_present() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "## Rewrite rules" in text
    assert "added:" in text, "the rewrite must be able to mark what it widened"
    assert "## Guardrails" in text
    assert "verdict:" in text, "a skill states the contrast it was judged on"
