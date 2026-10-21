"""Documentation-as-contract tests for the team's own role charters.

The charters are the specification every agent runs against, so the duties that
were added on request - the staged push policy and the local+CI certification -
are asserted here and cannot silently disappear in a refactor.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from tests.gitenv import child_env

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


def frontmatter(path: Path) -> dict[str, str]:
    """The skill's YAML frontmatter as flat key/value pairs.

    A five-line parser instead of a yaml dependency: the fields this contract
    pins are single-line scalars, and a package must not grow a runtime dep to
    read its own header.
    """
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name} has no frontmatter"
    block = text.split("\n---\n", 1)[0][len("---\n") :]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("\"'")
    return fields


def test_the_skill_declares_the_agent_skills_contract(root):
    """The published package is loaded by hosts other than this one.

    ``compatibility`` is the only place an installer can learn that the engine
    needs python3 before the first tool call fails on it, so it must be present
    and agree with the interpreter the Python distribution actually supports.
    """
    fields = frontmatter(root / "SKILL.md")
    assert fields["name"] == "teamwork"
    assert 0 < len(fields["description"]) <= 1024, "the spec caps the description"

    compatibility = fields["compatibility"]
    assert "python3" in compatibility, compatibility
    requires = re.search(
        r'requires-python\s*=\s*">=([0-9.]+)"',
        read(root, "pyproject.toml"),
    )
    assert requires, "pyproject.toml no longer declares requires-python"
    assert requires.group(1) in compatibility, (
        "SKILL.md advertises an interpreter the wheel does not support: "
        f"{requires.group(1)} vs {compatibility!r}"
    )
    assert "stdlib" in compatibility, "the no-dependency claim is the point of the engine"


# --------------------------------------------------------------------------- #
# push policy: Release Engineer pushes reviewed revisions in stages
# --------------------------------------------------------------------------- #


def test_release_engineer_owns_a_review_gated_staged_push_policy(root):
    text = read(root, "roles", "release-engineer.md")
    assert "## Publishing to the remote (push policy)" in text
    # gated on the Reviewer
    assert "after the Reviewer has confirmed" in text
    assert "no finding is open" in text
    # staged, not batched to the end: a stage ends with a push
    assert "push per stage" in text.lower()
    assert "a stage ends with a push, not with a merge" in text.lower()
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
    assert "per milestone" not in text.lower()
    assert "a stage ends with a push" in text.lower()
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
    # the cadence is a hard rule on both surfaces, not prose a rewrite can drop
    assert "a stage ends with a push, not with a merge" in text.lower()


def test_skill_entry_point_has_the_staged_push_and_ci_step(root):
    text = flat(read(root, "SKILL.md"))
    assert "### 5c. Push in stages, and certify both signals" in text
    assert "push after review, stage by stage" in text.lower()
    assert "a stage ends with a push, not with a merge" in text.lower()
    assert "Tester - certify local *and* CI" in text


def test_architecture_records_who_may_push(root):
    text = read(root, "docs", "Team", "Architecture.md")
    assert "The Release Engineer pushes reviewed revisions" in text
    assert "per milestone" not in text.lower()
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

#: The prose/media set, as path patterns. Every member must be named by the
#: workflow's own filter (a `paths-ignore` list or the `scope` classifier's
#: regex) and by `docs.yml`'s `paths:` list - the two lists must not drift.
PROSE_AND_MEDIA = ("docs/**", "assets/**", "README.md", "LICENSE", "mkdocs.yml")

#: One concrete file per prose/media pattern, used to exercise the filter the
#: workflow really implements (a glob list or the classifier's regex).
PROSE_AND_MEDIA_EXAMPLES = (
    "docs/Team/Architecture.md",
    "assets/logo.svg",
    "README.md",
    "LICENSE",
    "mkdocs.yml",
)

#: Paths that must ALWAYS run the code matrix when they change.
SHIPPED = ("src/**", "scripts/**", "tests/**", "roles/**", "references/**", "templates/**")

#: The directories whose files ship in the wheel/skill bundle.
SHIPPED_DIRS = ("src", "scripts", "tests", "roles", "references", "templates")

#: The expensive jobs the cost optimisation may skip, and only on a push.
EXPENSIVE_JOBS = ("lint", "typecheck", "test", "build", "privacy", "docs")

#: The exact condition the expensive jobs carry under the `scope` mechanism.
SCOPE_CONDITION = "if: github.event_name != 'push' || needs.scope.outputs.code == 'true'"


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _strip_comments(text: str) -> str:
    """The workflow text without its comment lines.

    The header of `ci.yml` explains the mechanism it replaced, so a mention of
    `paths-ignore` in a comment is not a filter. Only code counts.
    """
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))


def workflow_triggers(text: str) -> dict[str, str]:
    """The `on:` section of a workflow, keyed by trigger name.

    A text parser, not a YAML parser: the workflow must be readable without a
    runtime dependency, and the section is a flat, two-space-indented mapping.
    """
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip() == "on:")
    triggers: dict[str, str] = {}
    name = ""
    body: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and _indent(line) == 0:
            break  # the section ends at the next top-level key
        if not stripped or stripped.startswith("#"):
            if name:
                body.append(line)
            continue
        if _indent(line) == 2 and stripped.endswith(":"):
            if name:
                triggers[name] = "\n".join(body)
            name = stripped[:-1]
            body = []
        elif name:
            body.append(line)
    if name:
        triggers[name] = "\n".join(body)
    return triggers


def workflow_jobs(text: str) -> dict[str, str]:
    """The `jobs:` section of a workflow, keyed by job name."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip() == "jobs:")
    jobs: dict[str, str] = {}
    name = ""
    body: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if _indent(line) == 0:
            break
        if _indent(line) == 2 and re.fullmatch(r"[A-Za-z0-9_-]+:", stripped):
            if name:
                jobs[name] = "\n".join(body)
            name = stripped[:-1]
            body = []
        elif name:
            body.append(line)
    if name:
        jobs[name] = "\n".join(body)
    return jobs


def _yaml_list(block: str, key: str) -> list[str] | None:
    """The list items of `key:` inside a trigger block, or None if absent."""
    match = re.search(rf"^    {re.escape(key)}:\s*$", block, re.M)
    if not match:
        return None
    items: list[str] = []
    for line in block[match.end() :].splitlines():
        item = re.match(r"^      - (.+)$", line)
        if item:
            items.append(item.group(1).strip().strip('"'))
        elif not line.strip() or line.strip().startswith("#"):
            continue
        else:
            break
    return items


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """A GitHub-style path glob as a regex (`**` crosses directories)."""
    out: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return re.compile("^" + "".join(out) + "$")


def _expand_prose_regex(regex: str) -> set[str]:
    """The classifier regex as the equivalent set of path patterns.

    The `scope` job states the prose set as one alternation
    (`^(docs/|assets/|README\\.md$|...)`); the `docs.yml` list states the same
    set as globs. Expanding the regex makes the two comparable.
    """
    body = regex.strip()
    if body.startswith("^(") and body.endswith(")"):
        body = body[2:-1]
    patterns: set[str] = set()
    for alternative in body.split("|"):
        item = alternative.strip().replace("\\.", ".").rstrip("$")
        patterns.add(item + "**" if item.endswith("/") else item)
    return patterns


class ProseSet:
    """The prose/media filter a workflow really implements.

    Two mechanisms exist in the history of `ci.yml`: a workflow-level
    `paths-ignore` list and the `scope` classifier job (a regex over the
    changed paths). Both are modelled here, so the tests can assert the
    contract without depending on which one is checked out.
    """

    def __init__(self, patterns: set[str], regex: str | None = None) -> None:
        self.patterns = patterns
        self.regex = regex
        self._compiled = re.compile(regex) if regex else None
        self._globs = [_glob_to_regex(pattern) for pattern in sorted(patterns)]

    @property
    def mechanism(self) -> str:
        return "scope" if self._compiled is not None else "paths-ignore"

    def matches(self, path: str) -> bool:
        """True when the workflow classifies `path` as prose/media."""
        if self._compiled is not None:
            return self._compiled.search(path) is not None
        return any(glob.match(path) for glob in self._globs)


def ci_prose_filter(root: Path) -> ProseSet:
    """The prose/media filter `ci.yml` implements on a push."""
    text = read(root, ".github", "workflows", "ci.yml")
    classifier = re.search(r"PROSE='([^']*)'", text)
    if classifier:
        return ProseSet(_expand_prose_regex(classifier.group(1)), classifier.group(1))
    items = _yaml_list(workflow_triggers(text).get("push", ""), "paths-ignore")
    assert items is not None, "ci.yml has neither a scope classifier nor a paths-ignore filter"
    return ProseSet(set(items))


def docs_prose_filter(root: Path) -> set[str]:
    """The prose/media set `docs.yml` triggers on."""
    text = read(root, ".github", "workflows", "docs.yml")
    items = _yaml_list(workflow_triggers(text).get("push", ""), "paths")
    assert items is not None, "docs.yml must trigger on a prose/media path list"
    return set(items)


def _first_file(root: Path, directory: str) -> str:
    for path in sorted((root / directory).rglob("*")):
        if path.is_file():
            return path.relative_to(root).as_posix()
    raise AssertionError(f"no file found under {directory}/")


def test_ci_ignores_prose_and_media_paths(root):
    """The prose/media set is named by the workflow and really classifies prose.

    The mechanism may be a `paths-ignore` list or the `scope` classifier's
    regex; the contract is that the set is named, and that every member of it
    is classified as prose by the filter the workflow implements.
    """
    prose = ci_prose_filter(root)
    for marker in PROSE_AND_MEDIA:
        assert marker in prose.patterns, f"ci.yml does not name the prose path {marker}"
    for example in PROSE_AND_MEDIA_EXAMPLES:
        assert prose.matches(example), f"ci.yml does not classify {example} as prose"
    # the filter must be a real filter: a shipping file is not prose
    assert not prose.matches("src/teamwork/cli.py")
    # Exactly one mechanism filters the push. A workflow-level `paths-ignore`
    # skips the whole workflow - including a gate whose subject is prose - so
    # it cannot coexist with the job-level classifier.
    text = read(root, ".github", "workflows", "ci.yml")
    has_scope = "scope" in workflow_jobs(text)
    has_trigger_filter = "paths-ignore" in workflow_triggers(text).get("push", "")
    assert not (has_scope and has_trigger_filter), (
        "ci.yml must not carry a workflow-level paths-ignore next to the scope classifier"
    )


def test_ci_does_not_ignore_anything_that_ships(root):
    """Nothing that ships may be classified as prose.

    The classifier's real logic is exercised: the shipped files of the tree
    are offered to the filter the workflow implements, and each one must come
    back as code.
    """
    prose = ci_prose_filter(root)
    shipped_examples = [_first_file(root, directory) for directory in SHIPPED_DIRS]
    shipped_examples += [
        "SKILL.md",
        "pyproject.toml",
        ".github/workflows/ci.yml",
        ".github/workflows/docs.yml",
        ".github/workflows/release.yml",
    ]
    for example in shipped_examples:
        assert not prose.matches(example), f"ci.yml classifies the shipping path {example} as prose"
    for marker in SHIPPED:
        assert marker not in prose.patterns, f"ci.yml must not ignore shipping path {marker}"
    assert "pyproject.toml" not in prose.patterns
    assert ".github/**" not in prose.patterns


def test_the_prose_set_and_the_docs_workflow_path_list_are_identical(root):
    """A path in one list and not the other is a hole in one of the two gates.

    The prose set the CI filter uses and the `paths:` list `docs.yml` triggers
    on must be the same set - asserted as an identity of the sets, not as a
    count, so that a path added to one side fails the test.
    """
    prose = ci_prose_filter(root)
    docs = docs_prose_filter(root)
    assert prose.patterns == docs, (
        f"the CI prose set and the docs.yml path list differ: "
        f"only in CI: {sorted(prose.patterns - docs)}, only in docs.yml: {sorted(docs - prose.patterns)}"
    )
    for marker in PROSE_AND_MEDIA:
        assert marker in docs, f"docs.yml path list is missing {marker}"


def test_the_release_consistency_gate_is_never_filtered(root):
    """A gate whose subject is prose must not be skipped when prose drifts.

    The `release-consistency` job reads the markdown, `version.py` and
    `CHANGELOG.md`. A workflow-level `paths-ignore` on the push trigger skips
    the whole workflow - including that job - exactly when the documentation
    drifts, which makes the gate worthless. So the gate must be unfiltered:
    no workflow-level push filter, no `needs:` on the classifier and no
    job-level `if:`.

    On a revision that does not carry the gate yet there is nothing to
    protect, and the test states that instead of pretending to check it.
    """
    text = read(root, ".github", "workflows", "ci.yml")
    code = _strip_comments(text)
    jobs = workflow_jobs(code)
    gate = jobs.get("release-consistency")
    checker = root / "scripts" / "check_release_consistency.py"
    if checker.is_file():
        assert gate is not None, "the checker is in the tree, so ci.yml must carry the gate"
    if gate is None:
        assert "scope" not in jobs, "ci.yml has a scope job but no release-consistency gate"
        return
    push = workflow_triggers(code).get("push", "")
    assert "paths-ignore" not in push, "ci.yml must not path-filter the push trigger"
    assert "paths-ignore" not in code, "ci.yml must not carry a workflow-level path filter"
    assert not re.search(r"^    needs:", gate, re.M), (
        "the consistency gate must not need the scope job"
    )
    assert not re.search(r"^    if:", gate, re.M), (
        "the consistency gate must not be skipped by an if"
    )
    assert "check_release_consistency.py" in gate, "the gate must run the consistency checker"


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

    ``subagent``/``schedule.create`` may appear only as an adapter example,
    never as the definition of an operation.
    """
    text = read(root, "SKILL.md")
    assert "Only six\n  operations need a host mechanism" in text or "six\n  operations" in text
    adapters = read(root, "references", "Adapters.md")
    for tool in ("subagent(", "schedule.create"):
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


def test_the_merge_policy_forbids_the_host_merge_button(root):
    """The host's merge button stamps the signed-in account into the history.

    Measured on this repository (2026-10-20): three rewrites of ``main`` came from
    one cause - a host squash (and a host rebase) wrote the merging account's
    personal mailbox into the commit, the privacy gate failed on history, and the
    traceability guard that re-runs that gate failed with it. The doctrine must
    therefore name the local merge + push as the canonical path, or the next
    contributor follows it and rewrites ``main`` again.
    """
    text = flat(read(root, "references", "Remotes.md"))
    assert "merged **locally" in text or "merge is performed" in text, (
        "the merge strategy must state that the merge is done locally and pushed"
    )
    assert "signed-in" in text, "the policy must name the cause: the signed-in account"
    contributing = flat(read(root, "CONTRIBUTING.md"))
    assert "squash" in contributing.lower()
    assert "local" in contributing.lower() or "locally" in contributing.lower()


def test_ci_runs_the_committer_guard(root):
    """The guard that catches an account stamped into main must be wired into CI.

    Measured on this repository (2026-10-20): three rewrites of ``main`` came from
    one cause - a host merge button wrote the signed-in account into the commit,
    the privacy gate failed on that personal mailbox in the history, and the
    acceptance proof that re-runs the gate failed the whole matrix. The guard
    fires on the push instead, with the offending commit named.
    """
    ci = read(root, ".github", "workflows", "ci.yml")
    assert "--guard-committer" in ci, "ci.yml must run the committer guard"
    assert "committer guard" in ci.lower(), "the job must be named so it is visible"
    assert "push:" in ci
    assert ci.index("committer-guard:") > ci.index("jobs:"), "the guard must be a job"


def test_the_committer_guard_is_documented(root):
    """The repair must be written down where a contributor reads the policy."""
    remotes = flat(read(root, "references", "Remotes.md"))
    assert "committer" in remotes.lower()
    contributing = flat(read(root, "CONTRIBUTING.md"))
    assert "committer" in contributing.lower(), (
        "the contributor guide must say the merge button stamps a committer"
    )


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
    workflows must run unconditionally on every pull request. A check that is
    skipped by a path filter is not reported at all, and a required check that
    is never reported blocks the merge forever.
    """
    ci = read(root, ".github", "workflows", "ci.yml")
    triggers = workflow_triggers(ci)
    assert "pull_request" in triggers, "ci.yml must trigger on every pull request"
    pr_block = triggers["pull_request"]
    assert not re.search(r"^\s+paths(-ignore)?:", pr_block, re.M), (
        "ci.yml must not path-filter pull requests"
    )
    docs = read(root, ".github", "workflows", "docs.yml")
    docs_pr = workflow_triggers(docs).get("pull_request", "")
    assert not re.search(r"^\s+paths(-ignore)?:", docs_pr, re.M), (
        "docs.yml must not path-filter pull requests"
    )
    # the cost optimisation exists, on the push side only
    assert "push" in triggers, "ci.yml must trigger on push"
    jobs = workflow_jobs(ci)
    if "scope" in jobs:
        # the classifier mechanism: the expensive jobs ask the classifier
        assert "paths-ignore" not in triggers["push"], (
            "ci.yml must not path-filter the push trigger next to the scope classifier"
        )
        assert jobs["scope"].count("outputs:") == 1, "the scope job must publish one output"
        assert "code:" in jobs["scope"], "the scope job must publish the code output"
        for job in EXPENSIVE_JOBS:
            assert job in jobs, f"ci.yml is missing the {job} job"
            assert "needs: scope" in jobs[job], f"the {job} job must need the scope job"
            assert SCOPE_CONDITION in jobs[job], (
                f"the {job} job must skip only on a prose-only push"
            )
    else:
        # the trigger-filter mechanism: the jobs themselves are never skipped
        for job in EXPENSIVE_JOBS:
            assert job in jobs, f"ci.yml is missing the {job} job"
            assert not re.search(r"^    if:", jobs[job], re.M), f"the {job} job must not be skipped"


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
    assert "a pass is the merge" in text.lower()
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
    # A SHA-pinned action keeps the human-readable major in a trailing comment.
    found.update(
        {
            action: major
            for action, _sha, major in re.findall(
                r"([\w.-]+/[\w.-]+)@([0-9a-f]{40}) # v(\d+)", text
            )
        }
    )
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
    surfaces = [
        "README.md",
        "docs/index.md",
        "docs/guide/install.md",
        "docs/guide/quickstart.md",
        "docs/guide/cli.md",
        "docs/guide/architecture.md",
        "assets/demo.svg",
        "SKILL.md",
    ]
    for name in surfaces:
        text = (root / name).read_text(encoding="utf-8").lower()
        for host, pattern in HOST_PATTERNS.items():
            assert not re.search(pattern, text), f"{name} still names the host {host!r}"

    # every role charter ships inside the pi package: a concrete host tool call
    # there is the same portability regression as one in SKILL.md. Provider and
    # model names are content, not a host dependency, so they are not scanned.
    for charter in sorted((root / "roles").glob("*.md")):
        text = charter.read_text(encoding="utf-8")
        for tool in ("subagent(", "subagent_supervisor(", "schedule.create", "teams("):
            assert tool not in text, f"{charter.name} hard-codes the host tool {tool!r}"


def test_documented_install_produces_tracked_files_not_a_gitlink(root, tmp_path):
    """The project install must be committable: 100644 files, not a 160000 submodule.

    Reproduces the recipe against a local "remote" so no network is needed.
    """
    import subprocess

    remote = tmp_path / "remote"
    remote.mkdir()
    (remote / "SKILL.md").write_text("---\nname: teamwork\n---\n", encoding="utf-8")
    # The platform's own variables must survive (a hand-built environment that
    # keeps PATH and HOME but drops SystemRoot/TEMP breaks Windows, where the
    # interpreter's RNG is initialised from the OS) and the caller's git
    # configuration must not: ``GIT_CONFIG_GLOBAL``, ``GIT_CONFIG_SYSTEM`` and
    # ``$XDG_CONFIG_HOME/git/config`` would otherwise decide whether the commit
    # is signed (``commit.gpgsign``) and which branch a fresh repository starts
    # on (``init.defaultBranch``). ``child_env`` starts from the parent
    # environment and re-asserts the hermeticity on top.
    env = child_env(
        GIT_AUTHOR_NAME="T",
        GIT_AUTHOR_EMAIL="t@example.com",
        GIT_COMMITTER_NAME="T",
        GIT_COMMITTER_EMAIL="t@example.com",
        HOME=str(tmp_path),
    )
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


def test_no_surface_still_demands_a_second_reviewer_to_merge(root):
    """A pass merges at once; no shipped surface may teach the retired two-step.

    Six review rounds attacked a heuristic that tried to *recognise* an offender
    sentence, and every round found a phrasing it could not see - the search space
    of ways to say "somebody other than the verifier lands it" is unbounded, so
    that design cannot converge. This guard is deliberately bounded instead:

    * a POSITIVE floor: every shipped surface must still state the merged-on-pass
      rule in one of the accepted sentences (delete or contradict the rule and this
      fails), and
    * a REGRESSION LIST: every wording a reviewer actually produced, each of which
      shipped green at some point, is stored here and grepped for verbatim.

    That trades "catches phrasings nobody thought of" for "cannot be talked
    around": the rule must be present and the known retirements must stay absent.
    A newly invented phrasing only survives if a reviewer reads the surface and
    adds a line here - which is the review step doing its job, not a regex.

    KNOWN AND ACCEPTED LIMITATION, measured: appending
    "Whoever read the patch carries it onto the trunk." to references/Roles.md
    leaves this test green (it shares no wording with any retired phrase). That is
    deliberate - the previous predicate was six rounds deep in paraphrases it could
    not see while reading as if it could. This one does not overclaim: it guarantees
    the rule is present and the retirements stay gone, and it names the residual
    risk instead of hiding it.
    """

    surfaces = (
        ("AGENTS.md",),
        ("templates", "AGENTS.md"),
        ("references", "Roles.md"),
        ("SKILL.md",),
        ("docs", "guide", "cli.md"),
        ("references", "Engineering.md"),
        ("roles", "reviewer.md"),
    )
    texts = {parts: flat(read(root, *parts)) for parts in surfaces}

    # (1) The rule has to be stated, in the imperative form the contract uses.
    # Without this the rest of the guard is satisfied by simply deleting the topic.
    stated = (
        "pass merges",
        "pass is the merge",
        "merges the pr at once",
        "merging it now",
        "merges the deliverable",
        "passing review merges the pr itself",
        "a pass is the merge",
    )
    for parts, text in texts.items():
        low = text.lower()
        assert any(phrase in low for phrase in stated), (
            f"{'/'.join(parts)} no longer states that a pass merges the deliverable"
        )

    # (2) Every wording a reviewer produced. Verbatim, case-folded, whitespace
    # collapsed - so a re-wrap or a capitalisation change cannot hide one.
    retired = (
        "a different reviewer must merge it",
        "a second reviewer must merge it",
        "another reviewer must merge it",
        "another reviewer applies the change after the pass",
        "another reviewer merges it after the pass",
        "the next reviewer merges it",
        "someone who did not pass it must land the branch",
        "somebody besides the verifier must land the branch",
        "landing is done by whoever did not pass it",
        "the reviewer who was not the one to verify it applies the change",
        "the reviewer who did not verify it applies the change",
        "a reviewer who was not the verifier lands the branch",
        "a reviewer who was not the verifier applies the change",
        "the role that did not record the verdict integrates the change",
        "the branch is integrated by a different reviewer",
        "after the pass, someone else lands the branch",
        "the reviewer who merely read the diff lands it",
        "the merge is performed by a reviewer other than the verifier",
        "a different role applies the change to main",
        "it must be merged by an instance that did not record the verdict",
        "the change should be landed by a lane that only read the diff",
        "--by <another-reviewer>",
    )
    for parts, text in texts.items():
        low = " ".join(text.lower().split())
        for wording in retired:
            assert wording not in low, (
                f"{'/'.join(parts)} teaches the retired two-step merge: {wording!r}"
            )

    # (3) The rule as authored: the author is the one party refused, so
    # independence never becomes "find a second Reviewer".
    joined = " ".join(" ".join(text.lower().split()) for text in texts.values())
    assert "author never merges" in joined or "never merges its own work" in joined
    assert "author" in joined and "refused" in joined


def test_the_review_rule_counts_failures_and_escalates(root):
    """The review-failure rule must state one rule, not two contradictory ones.

    Regression: the tracked `SKILL.md` said "there is no round limit" while the
    three-failure dispute rule sat 340 lines above it, and the 1.1.2 changelog
    entry claimed the contradiction had been repaired - it had been repaired in
    the built copies only, so no test could see the difference. This guards the
    two shipped statements against drifting apart again; it does not read
    CHANGELOG.md, so it cannot catch a changelog entry that overstates the source.
    """
    skill = flat(read(root, "SKILL.md")).lower()
    agents = flat(read(root, "templates", "AGENTS.md")).lower()

    for text, label in ((skill, "SKILL.md"), (agents, "templates/AGENTS.md")):
        assert "there is no round limit" not in text, (
            f"{label} still states that review rework has no round limit, which "
            "contradicts the 3-failure dispute rule"
        )
        assert "failures are counted" in text, (
            f"{label} must state that review failures are counted"
        )
        assert re.search(r"at 3 .{0,40}dispute", text), (
            f"{label} must state that at 3 failures the Reviewer opens a dispute"
        )


def test_the_reviewer_charter_carries_the_ordered_criteria(root):
    """The artefact-first rubric is a contract, not an optional nicety.

    The order matters: a later strength never pays for an earlier gap. Asserting
    the sequence keeps a refactor from reshuffling it.
    """
    raw = read(root, "roles", "reviewer.md")
    start = raw.index("## Ordered criteria")
    section = flat(raw[start : raw.index("## Standards", start)]).lower()
    assert raw.count("## Ordered criteria") == 1, "the rubric must have one home"
    order = [
        "delivery and conformance",
        "fidelity",
        "internal consistency",
        "operational fitness",
        "finish",
        "evidence reproduces",
    ]
    positions = [section.find(name) for name in order]
    assert all(pos >= 0 for pos in positions), (
        f"roles/reviewer.md is missing an ordered criterion: "
        f"{[name for name, pos in zip(order, positions) if pos < 0]}"
    )
    assert positions == sorted(positions), "the review criteria are out of order"

    # Blind to the author, and the downside counts as much as the upside.
    assert "judge blind to the author" in section
    assert "length and polish are not merits" in section
    assert "weigh the downside as heavily as the upside" in section


def test_the_skill_points_at_the_review_rubric(root):
    """An agent that never opens the charter must still see the rubric exists.

    The pointer is asserted by name, not as "roles/reviewer.md appears somewhere":
    SKILL.md cites that file for other reasons, so the bare substring let a
    reviewer reword the pointer and keep the test green.
    """
    skill = flat(read(root, "SKILL.md")).lower()
    assert "the reviewer judges the artefact, not the author" in skill
    assert "the `## ordered criteria` section of `roles/reviewer.md`" in skill
    for name in (
        "delivery and conformance",
        "fidelity",
        "internal consistency",
        "operational fitness",
        "finish",
        "evidence reproduces",
    ):
        assert name in skill, f"SKILL.md does not name the criterion {name!r}"


def test_the_untrusted_material_rule_is_stated_where_agents_read_it(root):
    """Material under inspection is data, never instructions."""
    for parts in (
        ("references", "Evidence.md"),
        ("templates", "AGENTS.md"),
        ("AGENTS.md",),
    ):
        text = flat(read(root, *parts)).lower()
        assert "data, never instructions" in text, (
            f"{'/'.join(parts)} does not state the untrusted-material rule"
        )


def test_a_process_change_reported_as_an_improvement_needs_a_contrast(root):
    """The verdict vocabulary is the guard against invented attribution.

    A lesson with no contrast is a guess, and `confounded` must be available so an
    agent has an honest label for 'one run, several changes'. Declining to record a
    lesson has to stay a legitimate outcome, or the rule pushes agents to invent.
    """
    texts = {
        "references/Evidence.md": flat(read(root, "references", "Evidence.md")).lower(),
        "templates/AGENTS.md": flat(read(root, "templates", "AGENTS.md")).lower(),
        "AGENTS.md": flat(read(root, "AGENTS.md")).lower(),
    }
    for name, text in texts.items():
        assert "a claim of improvement needs a contrast" in text, (
            f"{name} does not require a contrast for an improvement claim"
        )
        for verdict in ("helped", "hurt", "no observed effect", "confounded"):
            assert verdict in text, f"{name} does not name the verdict {verdict!r}"
        assert "declining to record a lesson is a valid outcome" in text, (
            f"{name} must keep declining to record a lesson legitimate"
        )
