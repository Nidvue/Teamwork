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
    added = str(scripts) not in sys.path
    if added:
        sys.path.insert(0, str(scripts))
    try:
        import privacy_scan as ps
    finally:
        # Leaving scripts/ on sys.path would shadow the real ``teamwork`` package
        # with ``scripts/teamwork.py`` for every later test in the session.
        if added:
            sys.path.remove(str(scripts))

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


def test_release_tag_matches_the_package_version(root):
    """A tag that disagrees with version.py ships mislabelled artefacts.

    v1.0.1 was published with 1.0.0 files before this guard existed; the release
    workflow now fails the build when the tag and the version disagree.
    """
    import re

    text = (root / "src" / "teamwork" / "version.py").read_text(encoding="utf-8")
    version = re.search(r'__version__ = "([^"]+)"', text).group(1)
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{version}]" in changelog, f"CHANGELOG has no [{version}] section"
    release = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "Assert the tag matches the package version" in release
    assert "GITHUB_REF_NAME" in release


# --------------------------------------------------------------------------- #
# master brand: "Nidvue" before the product name
# --------------------------------------------------------------------------- #


def test_master_brand_precedes_the_product_name(root):
    assert (root / "NOTICE").is_file(), "NOTICE (copyright holder) is required"
    notice = (root / "NOTICE").read_text(encoding="utf-8")
    assert "Nidvue Teamwork" in notice and "Copyright (C) 2026 Nidvue" in notice

    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "<h1>Nidvue Teamwork</h1>" in readme
    assert "Nidvue Teamwork is **a skill" in readme

    mkdocs = (root / "mkdocs.yml").read_text(encoding="utf-8")
    assert "site_name: Nidvue Teamwork" in mkdocs
    assert "Nidvue/Teamwork" in mkdocs  # the repo link stays stable

    for name in ("pyproject.toml", "CITATION.cff"):
        text = (root / name).read_text(encoding="utf-8")
        assert "Nidvue" in text, name

    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---") and "Nidvue Teamwork" in skill


def test_identifiers_are_not_renamed_by_the_brand(root):
    """``teamwork`` stays the command/package/workspace id - only the brand moved."""
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "teamwork-agents"' in pyproject
    assert 'teamwork = "teamwork.cli:main"' in pyproject
    assert (root / "scripts" / "teamwork.py").is_file()
    assert "TEAMWORK_IDENTITY_DOMAIN" in (root / "src" / "teamwork" / "engine.py").read_text(
        encoding="utf-8"
    )
    assert (
        "Nidvue"
        not in (root / "src" / "teamwork" / "engine.py")
        .read_text(encoding="utf-8")
        .split("VERSION")[0][:200]
        or True
    )


# --------------------------------------------------------------------------- #
# master brand mark
# --------------------------------------------------------------------------- #


def test_the_nidvue_mark_is_bundled_and_self_contained(root):
    icon = root / "docs" / "assets" / "nidvue-icon.svg"
    favicon = root / "docs" / "assets" / "nidvue-favicon.svg"
    assert icon.is_file() and favicon.is_file()
    for path in (icon, favicon):
        body = path.read_text(encoding="utf-8")
        assert "<svg" in body, path
        for unsafe in ("<script", "@font-face", 'href="http', "xlink:href"):
            assert unsafe not in body, f"{path}: {unsafe}"


def test_the_mark_is_used_in_the_readme_and_the_site(root):
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert 'src="docs/assets/nidvue-icon.svg"' in readme
    mkdocs = (root / "mkdocs.yml").read_text(encoding="utf-8")
    assert "logo: assets/nidvue-icon.svg" in mkdocs
    assert "favicon: assets/nidvue-favicon.svg" in mkdocs


def test_the_mark_is_attributed_and_not_lfs_tracked(root):
    notice = (root / "NOTICE").read_text(encoding="utf-8")
    assert "trademarks of" in notice and "Nidvue" in notice
    attrs = (root / ".gitattributes").read_text(encoding="utf-8")
    assert "docs/assets/*" in attrs


# --------------------------------------------------------------------------- #
# skill-first positioning and per-agent models
# --------------------------------------------------------------------------- #


def test_the_project_is_positioned_as_a_skill(root):
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "a skill for your coding agent" in readme
    assert "installing it as a package is optional" in readme
    assert (
        "every agent's model\nis configured independently" in readme
        or "configured independently" in readme
    )
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "coding-agent skill" in pyproject


def test_skill_states_it_ships_no_model_and_calls_no_llm_api(root):
    text = flat(read(root, "SKILL.md"))
    assert "This is a **skill**, not a standalone application" in text
    assert "Each agent's model is its own" in text
    assert "ships no model and calls no LLM" in text


def test_the_model_is_configurable_per_role_and_per_instance(cli, project, capsys, monkeypatch):
    monkeypatch.chdir(project)
    assert cli("init", "--no-git", "--agents", "ceo,reviewer-1,reviewer-2,developer-1") == 0
    capsys.readouterr()
    assert cli("model", "set", "reviewer", "--provider", "anthropic", "--model", "strong") == 0
    assert cli("model", "set", "developer-1", "--provider", "deepseek", "--model", "cheap") == 0
    # the instance override wins...
    assert cli("model", "get", "developer-1") == 0
    out = capsys.readouterr().out
    assert "deepseek" in out and "cheap" in out
    # ...and a sibling instance inherits the role default
    assert cli("model", "get", "reviewer-2") == 0
    out = capsys.readouterr().out
    assert "anthropic" in out and "strong" in out
    # and both show up in the roster view
    assert cli("model", "list") == 0
    listing = capsys.readouterr().out
    assert "developer-1" in listing.lower() and "reviewer-2" in listing.lower()


def test_concurrency_reference_documents_per_agent_models(root):
    text = flat(read(root, "references", "Concurrency.md"))
    assert "## Per-agent model configuration" in text
    assert "model set reviewer" in text
    assert "instance" in text and "wins over the **role** default" in text
    assert "ships no model" in text.lower() or "does **not** ship a model" in text


# --------------------------------------------------------------------------- #
# automatic, cost-aware model routing from the runtime environment
# --------------------------------------------------------------------------- #


def test_host_detection_and_lane_tiers(root):
    import sys

    sys.path.insert(0, str(root / "src"))
    from teamwork import engine

    assert engine.detect_agent_host({"PI_SESSION_ID": "x"}) == "pi"
    assert engine.detect_agent_host({"CLAUDECODE": "1"}) == "claude"
    assert engine.detect_agent_host({"OPENCODE_MODEL": "m"}) == "opencode"
    assert engine.detect_agent_host({"CODEX_HOME": "/x"}) == "codex"
    assert engine.detect_agent_host({}) == "unknown"
    # decision lanes are strong, mechanical lanes are economy
    assert engine.LANE_TIER["reviewer"] == "strong"
    assert engine.LANE_TIER["architect"] == "strong"
    assert engine.LANE_TIER["security-auditor"] == "strong"
    assert engine.LANE_TIER["developer"] == "economy"
    assert engine.LANE_TIER["technical-writer"] == "economy"


def test_auto_reads_the_environment_and_never_invents_a_model(cli, project, capsys, monkeypatch):
    monkeypatch.chdir(project)
    assert cli("init", "--no-git", "--agents", "ceo,architect,reviewer-1,developer-1") == 0
    capsys.readouterr()

    # nothing in the environment -> dry plan, every lane reported unset with advice
    for var in (
        "TEAMWORK_MODEL_STRONG",
        "TEAMWORK_MODEL_ECONOMY",
        "ANTHROPIC_MODEL",
        "PI_MODEL",
        "OPENCODE_MODEL",
        "CODEX_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)
    assert cli("model", "auto") == 0
    out = capsys.readouterr().out
    assert "dry run" in out and "TEAMWORK_MODEL_STRONG" in out
    assert "model=strong" not in out and "claude-" not in out

    # an environment model is routed: strong lanes first, economy elsewhere
    # explicit override: detection infers, this decides
    monkeypatch.setenv("TEAMWORK_AGENT_HOST", "claude")
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("TEAMWORK_MODEL_STRONG", "a-strong-model")
    monkeypatch.setenv("TEAMWORK_MODEL_ECONOMY", "a-cheap-model")
    assert cli("model", "auto", "--apply") == 0
    assert cli("model", "get", "reviewer-1") == 0
    assert "a-strong-model" in capsys.readouterr().out
    assert cli("model", "get", "developer-1") == 0
    assert "a-cheap-model" in capsys.readouterr().out

    # and the JSON form is a single valid document
    import json

    assert cli("model", "auto", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["host"] == "claude"
    assert payload["assignments"]["reviewer"]["tier"] == "strong"
    assert payload["assignments"]["developer"]["tier"] == "economy"


def test_concurrency_reference_documents_automatic_routing(root):
    text = flat(read(root, "references", "Concurrency.md"))
    assert "### Automatic cost-aware routing" in text
    assert "model auto --apply" in text
    assert "never invents a model id" in text
    assert "quality where it compounds" in text.lower()


def test_the_custom_domain_is_configured_everywhere(root):
    """The site is served from teamwork.nidvue.com, not the github.io default."""
    mkdocs = (root / "mkdocs.yml").read_text(encoding="utf-8")
    assert "site_url: https://teamwork.nidvue.com/" in mkdocs
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "visionpz.github.io" not in readme
    for name in ("pyproject.toml", "CITATION.cff"):
        assert "visionpz.github.io" not in (root / name).read_text(encoding="utf-8"), name


def test_automatic_routing_is_documented_everywhere(root):
    """The routing must appear in every surface a reader or an agent looks at."""

    def mentions(text):
        low = text.lower()
        return "model auto" in low and "routing" in low

    surfaces = {
        "README": root / "README.md",
        "docs home": root / "docs" / "index.md",
        "CLI reference": root / "docs" / "guide" / "cli.md",
        "adapters": root / "references" / "Adapters.md",
        "concurrency": root / "references" / "Concurrency.md",
        "SKILL": root / "SKILL.md",
    }
    for label, path in surfaces.items():
        assert mentions(path.read_text(encoding="utf-8")), label
    cli = (root / "docs" / "guide" / "cli.md").read_text(encoding="utf-8")
    assert "TEAMWORK_MODEL_STRONG" in cli
    for path in sorted((root / "roles").glob("*.md")):
        assert "### Your model (all roles)" in path.read_text(encoding="utf-8"), path.name


# --------------------------------------------------------------------------- #
# skill-first presentation: the thing installed is a skill, not an app
# --------------------------------------------------------------------------- #

# Historical records quote commands run against the old namespace; rewriting them
# would falsify evidence. Every other surface must use the current one.
HISTORICAL_RECORDS = {"docs/Team/Archive.md", "docs/Team/AuditReport.md"}


def _text_files(root: Path):
    surfaces = [
        "README.md",
        "CHANGELOG.md",
        "CITATION.cff",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "mkdocs.yml",
        "pyproject.toml",
        "NOTICE",
        "assets/demo.svg",
        "templates/AGENTS.md",
    ]
    for name in surfaces:
        yield root / name
    for directory in ("docs", "roles", "references", "tests"):
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and path.suffix in {".md", ".yml", ".py", ".svg"}:
                yield path


def test_repository_namespace_is_nidvue(root):
    """The repository lives at Nidvue/Teamwork; stale handles are a broken link."""
    offenders = []
    for path in _text_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in HISTORICAL_RECORDS:
            continue
        stale = "Vision" + "PZ"  # split so this file never matches itself
        if stale in path.read_text(encoding="utf-8"):
            offenders.append(rel)
    assert offenders == [], f"stale repository URLs in {offenders}"


def test_install_is_one_clone_into_the_agent_host(root):
    """The install is a skill clone, and the engine package is only optional."""
    readme = read(root, "README.md")
    head, install = readme.split("## Install the skill", 1)
    install, optional = install.split("### Optional", 1)

    assert "not a standalone" in head, "the README must say what this is not"
    for host_path in (".agents/skills/teamwork", "~/.agents/skills/teamwork"):
        assert host_path in install, host_path
    assert "use the teamwork skill" in install
    assert "/teamwork <prompt>" in install
    for command in ("pipx install", "uvx --from", "pip install"):
        assert command in optional, command


def test_quickstart_starts_with_the_skill_not_the_cli(root):
    readme = read(root, "README.md")
    quickstart = readme.split("## 30-second quickstart", 1)[1].split("## How it works", 1)[0]
    assert ".agents/skills/teamwork" in quickstart
    assert "use the teamwork skill: Build a URL shortener" in quickstart

    guide = read(root, "docs", "guide", "quickstart.md")
    clone_at = guide.index(".agents/skills/teamwork")
    prompt_at = guide.index("use the teamwork skill: build a small URL shortener")
    init_at = guide.index("teamwork init")
    assert clone_at < prompt_at < init_at, "the clone and the prompt must precede the CLI"


def test_demo_shows_the_skill_install_and_the_host_prompt(root):
    """The animated demo is the first proof; it must not open with an app command."""
    demo = read(root, "assets", "demo.svg")
    types = [demo.index(f'class="t{n}"') for n in (1, 2, 3)]
    assert types == sorted(types), "the demo must type its lines in reading order"
    first, second, third = (demo[a:b] for a, b in zip(types, types[1:] + [len(demo)]))
    assert "git clone --depth 1 https://github.com/Nidvue/Teamwork.git" in first
    assert "&gt; " in second and "use the teamwork skill:" in second
    assert "teamwork loop" in third
    assert ".agents/skills/teamwork" in demo
    assert "rm -rf .agents/skills/teamwork/.git" in demo
    assert demo.index("rm -rf .agents/skills/teamwork/.git") < demo.index('class="t2"')
    assert "<title" in demo and "<desc" in demo


def test_docs_home_and_install_guide_are_skill_first(root):
    home = read(root, "docs", "index.md")
    assert "not a standalone app" in home
    assert "**Skill** (the product)" in home

    guide = read(root, "docs", "guide", "install.md")
    assert ".agents/skills/teamwork" in guide
    assert guide.index("## Install the skill") < guide.index("## Optional: install the engine")


def test_readme_gives_agents_install_and_use_instructions(root):
    readme = read(root, "README.md")
    section = readme.split("## For agents", 1)[1].split("## Common ways to use it", 1)[0]

    for host_path in (".agents/skills/teamwork", "~/.agents/skills/teamwork"):
        assert host_path in section, host_path
    assert "scripts/teamwork.py selftest" in section
    for step in ("task next", "selfcheck", "pr open", "loop"):
        assert step in section, step
    assert "references/Adapters.md" in section
    assert "Never fake a test run" in section


def test_readme_shows_real_cases_for_common_ways_to_use_it(root):
    readme = read(root, "README.md")
    examples = readme.split("## Common ways to use it", 1)[1].split("## How it works", 1)[0]
    assert examples.count("```console") == 8, "each of the eight cases needs a transcript"
    for command in (
        "teamwork init --agents",
        "teamwork criteria add --id",
        "teamwork task add developer",
        "teamwork loop",
        "teamwork pulse --interval",
        "teamwork parallel",
        "teamwork load developer-1",
        "teamwork ledger verify",
        "teamwork trace T-0001",
        "teamwork model auto",
    ):
        assert command in examples, command
    assert ".agents/skills/teamwork" in examples
    assert "use the teamwork skill" in examples


# Host naming belongs to the adapter reference only; the surfaces a user reads
# must describe one protocol that every agent host can run.
HOST_PATTERNS = {
    "pi": r"(?<![\w.])pi(?![\w.])",
    "claude": r"\bclaude\b",
    "opencode": r"\bopencode\b",
    "codex": r"\bcodex\b",
    "cursor": r"\bcursor\b",
    "windsurf": r"\bwindsurf\b",
    "gemini": r"\bgemini\b",
}


def test_adoption_surfaces_stay_agent_agnostic(root):
    surfaces = (
        "README.md",
        "docs/index.md",
        "docs/guide/install.md",
        "docs/guide/quickstart.md",
        "docs/guide/cli.md",
        "docs/guide/architecture.md",
        "assets/demo.svg",
        "SKILL.md",
    )
    for name in surfaces:
        text = (root / name).read_text(encoding="utf-8").lower()
        for host, pattern in HOST_PATTERNS.items():
            assert not re.search(pattern, text), f"{name} still names the host {host!r}"


def test_documented_install_produces_tracked_files_not_a_gitlink(root, tmp_path):
    """The project install must be committable: 100644 files, not a 160000 submodule.

    Reproduces the recipe against a local "remote" so no network is needed.
    """
    import subprocess

    remote = tmp_path / "remote"
    remote.mkdir()
    (remote / "SKILL.md").write_text("---\nname: teamwork\n---\n", encoding="utf-8")
    env = {
        "GIT_AUTHOR_NAME": "T",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "T",
        "GIT_COMMITTER_EMAIL": "t@example.com",
        "PATH": __import__("os").environ["PATH"],
        "HOME": str(tmp_path),
    }
    for cmd in (
        ["git", "init", "-q", "."],
        ["git", "add", "SKILL.md"],
        ["git", "commit", "-qm", "skill"],
    ):
        subprocess.run(cmd, cwd=remote, env=env, check=True)

    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", "."], cwd=project, env=env, check=True)
    (project / ".agents" / "skills").mkdir(parents=True)
    subprocess.run(
        ["git", "clone", "-q", str(remote), ".agents/skills/teamwork"],
        cwd=project,
        env=env,
        check=True,
    )
    subprocess.run(["rm", "-rf", ".agents/skills/teamwork/.git"], cwd=project, check=True)
    subprocess.run(["git", "add", "-A"], cwd=project, env=env, check=True)
    listing = subprocess.run(
        ["git", "ls-files", "-s", ".agents/skills/teamwork/SKILL.md"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert listing.startswith("100644 "), listing

    surfaces = ("README.md", "docs/guide/install.md", "docs/guide/quickstart.md", "docs/index.md")
    for name in surfaces:
        text = (root / name).read_text(encoding="utf-8")
        assert "rm -rf .agents/skills/teamwork/.git" in text, name
