"""Integration: the commands and actions the CI workflow runs against the real tree.

`tests/unit/test_ci_contracts.py` asserts the job graph of
`.github/workflows/ci.yml` - the job set, the scope guards, the unconditional
release gate and the matrix clauses. This module crosses the other boundary: the
workflow text against the filesystem and the supply chain. A `run:` step that
names a script nobody ships fails at push time with the whole matrix red, and an
action pinned to a moving tag means the gate a revision passed can change under
it, so both are checked against the shipped tree rather than trusted.

Owner: tester. Task: T-0013.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"

SCRIPT_REF = re.compile(r"scripts/[\w./-]+\.py")
ACTION_REF = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)")
PINNED = re.compile(r"@[0-9a-f]{40}$")


def ci_text() -> str:
    return CI_PATH.read_text(encoding="utf-8")


def non_comment_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if not line.strip().startswith("#")]


def script_refs(text: str) -> list[str]:
    refs: list[str] = []
    for line in non_comment_lines(text):
        refs.extend(SCRIPT_REF.findall(line))
    return refs


def missing_scripts(text: str, root: Path = REPO_ROOT) -> list[str]:
    missing: list[str] = []
    for ref in script_refs(text):
        path = root / ref
        if not path.is_file():
            missing.append(ref)
            continue
        try:
            compile(path.read_text(encoding="utf-8"), ref, "exec")
        except SyntaxError:
            missing.append(ref)
    return missing


def action_refs(text: str) -> list[str]:
    refs: list[str] = []
    for line in non_comment_lines(text):
        match = ACTION_REF.match(line)
        if match:
            refs.append(match.group(1))
    return refs


def unpinned_actions(text: str) -> list[str]:
    return [ref for ref in action_refs(text) if not PINNED.search(ref)]


def test_every_script_the_workflow_runs_is_shipped() -> None:
    text = ci_text()
    assert len(script_refs(text)) >= 5
    assert missing_scripts(text) == []


def test_a_renamed_script_is_reported() -> None:
    text = "\n".join(non_comment_lines(ci_text()))
    ref = script_refs(text)[0]
    mutant = text.replace(ref, "scripts/absent_script.py", 1)
    assert missing_scripts(mutant) == ["scripts/absent_script.py"]


def test_every_action_is_pinned_to_a_commit_sha() -> None:
    text = ci_text()
    assert len(action_refs(text)) >= 5
    assert unpinned_actions(text) == []


def test_a_tag_pinned_action_is_reported() -> None:
    text = ci_text()
    ref = action_refs(text)[0]
    name = ref.split("@", 1)[0]
    mutant = text.replace(ref, f"{name}@v7", 1)
    assert unpinned_actions(mutant) == [f"{name}@v7"]


def test_a_commented_script_reference_does_not_count() -> None:
    text = ci_text() + "\n# python scripts/absent_script.py\n"
    assert missing_scripts(text) == []
    assert script_refs("") == []
    assert unpinned_actions("") == []


def test_the_checks_are_stable_across_calls() -> None:
    text = ci_text()
    assert missing_scripts(text) == missing_scripts(text)
    assert unpinned_actions(text) == unpinned_actions(text)
