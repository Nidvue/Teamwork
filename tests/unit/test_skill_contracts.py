"""Documentation-as-contract tests for the team's own role charters.

The charters are the specification every agent runs against, so the duties that
were added on request - the staged push policy and the local+CI certification -
are asserted here and cannot silently disappear in a refactor.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROLES = (
    "architect",
    "ceo",
    "cfo",
    "coo",
    "cto",
    "data-engineer",
    "designer",
    "developer",
    "product-manager",
    "project-manager",
    "release-engineer",
    "reviewer",
    "security-auditor",
    "technical-writer",
    "tester",
)


@pytest.fixture(scope="module")
def root() -> Path:
    return Path(__file__).resolve().parents[2]


def read(root: Path, *parts: str) -> str:
    return root.joinpath(*parts).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """Collapse whitespace so assertions survive line wrapping and indentation."""
    return re.sub(r"\s+", " ", text)


#: The CEO charter is intentionally different from the line roles.
LINE_ROLES = tuple(role for role in ROLES if role != "ceo")


# --------------------------------------------------------------------------- #
# bundle integrity
# --------------------------------------------------------------------------- #


def test_every_role_charter_exists_and_is_substantial(root):
    roles_dir = root / "roles"
    for role in ROLES:
        path = roles_dir / f"{role}.md"
        assert path.is_file(), f"missing charter: {role}"
        body = path.read_text(encoding="utf-8")
        assert body.startswith("# Role:"), f"{role}: wrong heading"
        assert len(body.splitlines()) > 20, f"{role}: charter looks empty"
    for role in LINE_ROLES:
        assert "## Boundaries" in (roles_dir / f"{role}.md").read_text(encoding="utf-8"), role


# --------------------------------------------------------------------------- #
# push policy: Release Engineer pushes reviewed revisions in stages
# --------------------------------------------------------------------------- #


def test_release_engineer_owns_a_review_gated_staged_push_policy(root):
    text = read(root, "roles", "release-engineer.md")
    assert "## Publishing to the remote (push policy)" in text
    # gated on the Reviewer
    assert "after the Reviewer has confirmed" in text
    assert "no finding is open" in text
    # staged, not batched to the end
    assert "per milestone" in text.lower()
    # pre-push gates and post-push CI watch on the pushed SHA
    assert "privacy_scan.py --tree --history" in text
    assert "on that pushed" in text or "on that SHA" in text
    # red lines
    assert "Never force-push" in text
    assert "Tags and releases are the CEO's call" in text


def test_release_engineer_routes_a_red_run_to_its_owner(root):
    text = read(root, "roles", "release-engineer.md")
    for owner in ("Developer", "Tester", "Architect", "CEO"):
        assert owner in text, f"routing missing owner: {owner}"


def test_engineering_reference_documents_the_push_policy(root):
    text = flat(read(root, "references", "Engineering.md"))
    assert "## Push policy - reviewed and staged, never batched" in text
    assert "force-pushing a shared branch, rewriting published history" in text
    assert "per milestone" in text.lower()
    assert "privacy_scan.py --tree --history" in text


# --------------------------------------------------------------------------- #
# local + CI certification: Tester
# --------------------------------------------------------------------------- #


def test_tester_certifies_both_local_and_ci(root):
    text = flat(read(root, "roles", "tester.md"))
    assert "**locally**" in text and "CI on the pushed revision" in text
    assert "A green local run with a red CI run is a failure" in text
    assert "is your bug" in text
    assert "Never report a suite as passing while the matching CI run is red" in text


def test_tester_routes_failures_to_the_owning_role(root):
    text = flat(read(root, "roles", "tester.md"))
    for owner in (
        "the Developer who owns the component",
        "the Architect",
        "the Release Engineer",
        "the CEO",
    ):
        assert owner in text, f"routing missing: {owner}"


def test_testing_reference_documents_local_and_ci(root):
    text = flat(read(root, "references", "Testing.md"))
    assert "## Local and CI are one certification" in text
    assert "Divergence is a defect" in text
    assert "CI <run-id>" in text


# --------------------------------------------------------------------------- #
# the constitution and the top-level skill carry the same rules
# --------------------------------------------------------------------------- #


def test_agents_template_carries_push_and_ci_rules(root):
    text = flat(read(root, "templates", "AGENTS.md"))
    assert "PUSH POLICY" in text
    assert "LOCAL + CI" in text
    assert "after the Reviewer has passed the revision with no open finding" in text


def test_skill_entry_point_has_the_staged_push_and_ci_step(root):
    text = flat(read(root, "SKILL.md"))
    assert "### 5c. Push in stages, and certify both signals" in text
    assert "push after review, per milestone" in text.lower()
    assert "Tester - certify local *and* CI" in text


def test_architecture_records_who_may_push(root):
    text = read(root, "docs", "Team", "Architecture.md")
    assert "The Release Engineer pushes reviewed revisions" in text
    assert "the Tester certifies" in text


def test_the_superseded_ceo_only_push_rule_is_marked_superseded(root):
    """The old blanket rule must not survive as an 'accepted' decision.

    The previous version of this test grepped for a literal string that only
    existed inside the test itself, so it could never fail. This one checks the
    record that actually governed behaviour.
    """
    text = read(root, "docs", "Team", "Decisions.md")
    for title in (
        "Only the CEO performs external publishing",
        "Neutralise all personal identity before publishing",
    ):
        idx = text.find(title)
        assert idx != -1, f"decision not found: {title}"
        end = text.find("\n## ", idx + 1)
        block = text[idx : end if end != -1 else len(text)]
        assert "status: superseded" in block, f"{title} is not marked superseded"


def test_the_role_mailbox_domain_is_an_owner_decision(root):
    text = read(root, "docs", "Team", "Decisions.md")
    assert "Owner instruction: the role mailbox domain is agents.nidvue.com" in text


# --------------------------------------------------------------------------- #
# CI trigger policy: code in, prose and media out
# --------------------------------------------------------------------------- #

#: Paths that must NOT run the code matrix (prose and media).
PROSE_AND_MEDIA = ('"docs/**"', '"assets/**"', '"README.md"', '"LICENSE"', '"mkdocs.yml"')

#: Paths that must ALWAYS run the code matrix when they change.
SHIPPED = ("src/**", "scripts/**", "tests/**", "roles/**", "references/**", "templates/**")


def test_ci_ignores_prose_and_media_paths(root):
    text = read(root, ".github", "workflows", "ci.yml")
    assert "paths-ignore:" in text, "ci.yml must filter documentation-only changes"
    for marker in PROSE_AND_MEDIA:
        assert marker in text, f"ci.yml paths-ignore is missing {marker}"


def test_ci_does_not_ignore_anything_that_ships(root):
    text = read(root, ".github", "workflows", "ci.yml")
    ignore_block = text.split("paths-ignore:", 1)[1].split("workflow_dispatch", 1)[0]
    for shipped in SHIPPED:
        assert shipped not in ignore_block, f"ci.yml must not ignore shipping path {shipped}"
    assert "pyproject.toml" not in ignore_block
    assert ".github/" not in ignore_block


def test_the_docs_workflow_covers_the_ignored_paths_with_cheap_checks(root):
    text = read(root, ".github", "workflows", "docs.yml")
    assert "paths:" in text
    assert '"docs/**"' in text and '"assets/**"' in text
    # the cheap checks that still matter for prose
    assert "teamwork.py links" in text
    assert "privacy_scan.py --tree --history" in text
    assert "mkdocs build --strict" in text


def test_release_engineer_charter_documents_the_trigger_policy(root):
    text = flat(read(root, "roles", "release-engineer.md"))
    assert "## CI trigger policy - code in, prose and media out" in text
    assert "Never ignore a path that ships" in text
    assert "Keep the two lists in sync" in text


def test_skill_documents_the_trigger_policy(root):
    text = flat(read(root, "SKILL.md"))
    assert "CI triggers are path-filtered: code in, prose and media out" in text


# --------------------------------------------------------------------------- #
# design principles: user first, simple, efficient, usable, great experience
# --------------------------------------------------------------------------- #


def test_designer_charter_is_user_first(root):
    text = flat(read(root, "roles", "designer.md"))
    assert "## Design principles - the user comes first" in text
    for principle in ("**Simple.**", "**Efficient.**", "**Usable.**", "**A great experience.**"):
        assert principle in text, principle
    for topic in ("### Layout and typography", "**Fonts:**", "### Images and media"):
        assert topic in text, topic
    # typography and usability specifics that must not drift
    assert "real text" in text
    assert "16 px" in text
    assert "45-75" in text
    assert "4.5:1" in text
    assert "prefers-reduced-motion" in text
    assert "never let an inline SVG depend on an external font file" in text


def test_design_template_carries_principles_and_typography(root):
    text = read(root, "templates", "Docs", "Design.md")
    assert "## Principles" in text
    assert "## Typography and fonts" in text
    assert "font stack" in text
    assert "text-as-image" in text


def test_repository_svgs_depend_on_no_external_font_or_resource(root):
    import re

    for svg in sorted((root / "assets").glob("*.svg")):
        body = svg.read_text(encoding="utf-8")
        assert "@font-face" not in body, svg
        assert "xlink:href" not in body, svg
        assert 'href="http' not in body, svg
        # An SVG that renders text must declare a font stack with a generic
        # fallback (the terminal demo uses a <style> block); a pure-graphic SVG
        # such as the logo has no text and therefore needs none.
        if "<text" in body or "font-family" in body:
            assert "font-family" in body, svg
            assert re.search(r"(sans-serif|monospace)", body), svg
