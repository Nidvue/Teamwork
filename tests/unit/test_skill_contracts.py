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


# --------------------------------------------------------------------------- #
# host-agnostic execution: any agent software
# --------------------------------------------------------------------------- #

AGENT_HOSTS = ("Pi", "Claude Code", "opencode", "Codex", "Cursor", "Generic")
HOST_OPERATIONS = (
    "Spawn a teammate",
    "Delegate one-shot work",
    "Message an agent",
    "Inspect teammate state",
    "Re-wake on a schedule",
    "Close the team",
)


def test_agent_host_adapters_cover_every_operation_and_host(root):
    text = read(root, "references", "Adapters.md")
    for host in AGENT_HOSTS:
        assert host in text, f"adapter reference is missing host: {host}"
    for operation in HOST_OPERATIONS:
        assert operation in text, f"adapter reference is missing operation: {operation}"
    assert "## Degraded modes" in text


def test_the_skill_states_that_it_is_host_agnostic(root):
    text = flat(read(root, "SKILL.md"))
    assert "agent-agnostic and remote-agnostic" in text
    assert "references/Adapters.md" in text
    assert "### 5d. Any agent host, any git host" in text


def test_no_normative_step_requires_a_pi_only_tool(root):
    """The protocol must not depend on one host's tool names.

    ``teams``/``subagent``/``schedule_prompt`` may appear only as an adapter
    example, never as the definition of an operation.
    """
    text = read(root, "SKILL.md")
    assert "Only six\n  operations need a host mechanism" in text or "six\n  operations" in text
    adapters = read(root, "references", "Adapters.md")
    for tool in ("teams(", "subagent(", "schedule_prompt("):
        assert tool in adapters, tool  # documented as Pi's mechanism
    assert "Never hard-code a host tool" in flat(adapters)


# --------------------------------------------------------------------------- #
# repository and CI integrity on any git host
# --------------------------------------------------------------------------- #

REMOTE_HOSTS = ("GitHub", "GitLab", "Bitbucket", "Gitea", "Azure DevOps")
INTEGRITY_RULES = (
    "no force-push",
    "required status checks",
    "required review",
    "squash",
    "protected tag",
)


def test_remote_integrity_reference_covers_hosts_and_rules(root):
    text = read(root, "references", "Remotes.md")
    for host in REMOTE_HOSTS:
        assert host in text, f"remote reference is missing host: {host}"
    for rule in INTEGRITY_RULES:
        assert rule in text.lower(), f"remote reference is missing rule: {rule}"
    assert "## Minimum viable protection" in text
    assert "Drift check" in text


def test_release_engineer_owns_repo_and_ci_integrity(root):
    text = flat(read(root, "roles", "release-engineer.md"))
    assert "Repository and CI integrity" in text
    assert "no force-push" in text
    assert "required check" in text.lower()
    assert "squash" in text.lower()
    assert "protected tag pattern" in text
    # charters use the {references} placeholder, substituted at init
    assert "Remotes.md" in text


def test_skill_assigns_integrity_to_the_release_engineer(root):
    text = flat(read(root, "SKILL.md"))
    assert "protects" in text.lower() or "protected default branch" in text
    assert "squash-only merges" in text
    assert "protected `v*`" in text or "protected v*" in text


def test_required_checks_are_always_reported_on_pull_requests(root):
    """A path-filtered pull request would wait forever on an unreportable check.

    The path filter is a cost optimisation and belongs on `push`; the required
    workflows must run unconditionally on every pull request.
    """
    ci = read(root, ".github", "workflows", "ci.yml")
    pr_block = ci.split("pull_request:", 1)[1].split("workflow_dispatch", 1)[0]
    assert "paths-ignore" not in pr_block, "ci.yml must not path-filter pull requests"
    docs = read(root, ".github", "workflows", "docs.yml")
    docs_pr = docs.split("pull_request:", 1)[1].split("workflow_dispatch", 1)[0]
    assert "paths:" not in docs_pr, "docs.yml must not path-filter pull requests"
    # and the push side keeps the filter (the cost optimisation)
    assert "paths-ignore" in ci.split("pull_request:", 1)[0]
    assert "paths:" in docs.split("pull_request:", 1)[0]


def test_remote_reference_documents_the_unreported_check_trap(root):
    text = flat(read(root, "references", "Remotes.md"))
    assert "a required check must always be reported" in text.lower()
    assert "deadlock" in text.lower()


# --------------------------------------------------------------------------- #
# automated code standards
# --------------------------------------------------------------------------- #

TOOLCHAIN_LANGUAGES = (
    "Python",
    "JavaScript / TypeScript",
    "Go",
    "Rust",
    "Java / Kotlin",
    "C / C++",
    "Shell",
    "YAML",
    "Markdown",
    "Terraform",
    "Dockerfile",
)


def test_engineering_reference_defines_a_toolchain_per_language(root):
    text = flat(read(root, "references", "Engineering.md"))
    assert "## Linting, formatting and type checking" in text
    for language in TOOLCHAIN_LANGUAGES:
        assert language in text, f"missing toolchain row: {language}"
    for tool in (
        "ruff format",
        "ruff check",
        "mypy",
        "prettier",
        "eslint",
        "gofmt",
        "cargo fmt",
        "clippy",
        "clang-format",
        "shellcheck",
        "yamllint",
        "markdownlint",
        "terraform fmt",
        "hadolint",
    ):
        assert tool in text, f"missing tool: {tool}"
    assert "never weaken the gate to pass" in text.lower() or "Never weaken the gate" in text


def test_agents_template_requires_lint_and_format(root):
    text = (root / "templates" / "AGENTS.md").read_text(encoding="utf-8")
    assert "**LINT AND FORMAT**" in text
    assert "ruff format" in text and "ruff check" in text


def test_every_role_charter_requires_the_canonical_toolchain(root):
    for path in sorted((root / "roles").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "### Code standards (all roles)" in text, path.name
        assert "canonical formatter and linter" in text, path.name
        assert "Never hand-format" in text, path.name


def test_skill_contract_requires_automated_style(root):
    text = flat(read(root, "SKILL.md"))
    assert "Style is automated" in text
    assert "ruff format" in text and "ruff check" in text and "mypy" in text


def test_this_repository_actually_configures_the_toolchain(root):
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.ruff]" in pyproject
    assert "[tool.ruff.format]" in pyproject
    assert "[tool.mypy]" in pyproject
    ci = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "ruff format --check" in ci and "ruff check" in ci and "mypy" in ci


def test_scanner_allows_the_github_service_mailbox():
    """Dependabot signs off with support@github.com; that is not personal data."""
    import sys

    scripts = Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import privacy_scan as ps

    assert ps._email_allowed("support@github.com")
    assert ps._email_allowed("noreply@github.com")


# --------------------------------------------------------------------------- #
# naming and commit hygiene
# --------------------------------------------------------------------------- #


def test_engineering_reference_defines_the_naming_policy(root):
    text = flat(read(root, "references", "Engineering.md"))
    assert "## Naming - PascalCase, camelCase, and the ecosystem's rule" in text
    for row in (
        "Team directory",
        "Docs page",
        "Python module / package",
        "JS / TS component",
        "Test file",
        "Tool-mandated file",
    ):
        assert row in text, row
    assert "PascalCase" in text and "camelCase" in text
    assert "lower_snake_case" in text
    assert "the ecosystem's rule wins" in text


def test_engineering_reference_defines_commit_hygiene(root):
    text = flat(read(root, "references", "Engineering.md"))
    assert "## Commit hygiene - rebase and squash before review" in text
    assert "git rebase -i" in text
    assert "one commit per task" in text.lower()
    assert "Never rebase or force-push a shared branch" in text


def test_agents_template_documents_naming_and_commit_hygiene(root):
    text = (root / "templates" / "AGENTS.md").read_text(encoding="utf-8")
    assert "**NAMING**" in text
    assert "**COMMIT HYGIENE**" in text
    assert "PascalCase" in text and "lower_snake_case" in text


def test_every_charter_documents_naming_and_commit_hygiene(root):
    for path in sorted((root / "roles").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "**Naming:**" in text, path.name
        assert "**Commit hygiene:**" in text, path.name
        assert "one commit per task" in text.lower(), path.name


def test_skill_contract_requires_naming_and_history_hygiene(root):
    text = flat(read(root, "SKILL.md"))
    assert "Names are deliberate" in text
    assert "History is minimal and modular" in text
    assert "Team directories are PascalCase" in text


def test_repository_names_follow_the_policy_it_documents(root):
    """The policy must describe this repository, not an aspiration."""
    # PascalCase team docs and skill directories
    assert (root / "docs" / "Team" / "Architecture.md").is_file()
    assert (root / "references" / "Engineering.md").is_file()
    # Python modules are import paths: lower_snake_case
    for module in (root / "src" / "teamwork").glob("*.py"):
        assert module.stem == module.stem.lower(), module
    # tool-mandated names are untouched
    for tool_file in ("pyproject.toml", "Makefile", "AGENTS.md", "SKILL.md", "LICENSE"):
        assert (root / tool_file).is_file(), tool_file


def test_remote_reference_is_honest_about_single_owner_repositories(root):
    text = flat(read(root, "references", "Remotes.md"))
    assert "## Single-owner repositories" in text
    assert "cannot be satisfied by the author" in text
    assert "enforce_admins = false" in text
    assert "Do not set the approval count to zero" in text


# --------------------------------------------------------------------------- #
# several Reviewers in parallel
# --------------------------------------------------------------------------- #


def test_reviewer_charter_documents_parallel_reviews(root):
    text = flat(read(root, "roles", "reviewer.md"))
    assert "## Working in parallel with other Reviewers" in text
    assert "several Reviewers at the same time" in text
    assert "The queue is shared" in text
    assert "One claim per deliverable" in text
    assert "Double review is explicit" in text
    assert "the merger is always a different reviewer" in text.lower()
    assert "Conflict of interest" in text
    assert "Findings union" in text


def test_skill_allows_multiple_parallel_reviewers(root):
    text = flat(read(root, "SKILL.md"))
    assert "several may run **in parallel**" in text
    assert "Review is a parallel lane" in text
    assert "one claim per deliverable" in text.lower()


def test_there_is_no_single_reviewer_bottleneck_claim(root):
    """The old 'one Reviewer instance' exception must not read as the norm."""
    text = flat(read(root, "SKILL.md"))
    assert "reviewer-1..N" in text
    assert "Reviewer is not optional" in text


# --------------------------------------------------------------------------- #
# warnings are errors
# --------------------------------------------------------------------------- #


def test_engineering_reference_defines_the_warnings_policy(root):
    text = flat(read(root, "references", "Engineering.md"))
    assert "## Warnings are errors" in text
    assert "Make the tool fail on warnings" in text
    assert "filterwarnings" in text and "-W error" in text
    assert "CI annotations count" in text
    assert "Suppress narrowly" in text


def test_agents_template_and_charters_require_warning_free(root):
    assert "**WARNINGS ARE ERRORS**" in read(root, "templates", "AGENTS.md")
    for path in sorted((root / "roles").glob("*.md")):
        assert "**Warnings are errors:**" in path.read_text(encoding="utf-8"), path.name


def test_this_repository_fails_on_warnings(root):
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'filterwarnings = ["error"]' in pyproject
    # TOML spelling here, CLI spelling in the reference
    assert "warn_unused_ignores = true" in pyproject
    assert "warn_redundant_casts = true" in pyproject


def test_ci_actions_are_not_on_node_deprecated_majors(root):
    """The CI log warned that checkout/setup-python/upload-artifact ran on Node 20.

    A deprecation notice about a runner is a warning: the action is bumped, not
    ignored.
    """
    import re

    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((root / ".github" / "workflows").glob("*.yml"))
    )
    floors = {
        "actions/checkout": 7,
        "actions/setup-python": 7,
        "actions/upload-artifact": 7,
        "actions/download-artifact": 8,
        "actions/upload-pages-artifact": 5,
        "actions/deploy-pages": 5,
        "actions/configure-pages": 6,
        "actions/attest-build-provenance": 4,
        "softprops/action-gh-release": 3,
    }
    found = dict(re.findall(r"([\w.-]+/[\w.-]+)@v(\d+)", text))
    for action, floor in floors.items():
        assert action in found, f"{action} not pinned in a workflow"
        assert int(found[action]) >= floor, f"{action}@{found[action]} < v{floor}"


def test_skill_contract_requires_warning_free_output(root):
    text = flat(read(root, "SKILL.md"))
    assert "Warnings are errors" in text
    assert "CI annotations" in text
